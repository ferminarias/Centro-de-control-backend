"""
Sync service for football-data.org API.
Competition: WC (FIFA World Cup), season 2026.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.prode.models import ProdeEquipo, ProdePartido, ProdePrediccion

logger = logging.getLogger(__name__)

FOOTBALL_DATA_URL = "https://api.football-data.org/v4"

STAGE_MAP = {
    "GROUP_STAGE": "grupo",
    "LAST_32": "r32",
    "LAST_16": "r16",
    "QUARTER_FINALS": "cuartos",
    "SEMI_FINALS": "semis",
    "THIRD_PLACE": "tercero",
    "FINAL": "final",
}

STATUS_MAP = {
    "SCHEDULED": "programado",
    "TIMED": "programado",
    "IN_PLAY": "en_juego",
    "PAUSED": "en_juego",
    "FINISHED": "finalizado",
    "POSTPONED": "programado",
    "SUSPENDED": "programado",
    "CANCELLED": "programado",
}


def calculate_points(pred_local: int, pred_visit: int, real_local: int, real_visit: int) -> int:
    if pred_local == real_local and pred_visit == real_visit:
        return 3
    pred_sign = (pred_local > pred_visit) - (pred_local < pred_visit)
    real_sign = (real_local > real_visit) - (real_local < real_visit)
    return 1 if pred_sign == real_sign else 0


def _resolve_team(
    api_team: dict,
    equipos_by_api_id: dict,
    equipos_by_name: dict,
    db: Session,
) -> Optional[ProdeEquipo]:
    api_id = api_team.get("id")
    name = (api_team.get("name") or api_team.get("shortName") or "").strip()

    equipo = equipos_by_api_id.get(api_id) or equipos_by_name.get(name.lower())

    if equipo and api_id and not equipo.api_id:
        equipo.api_id = api_id
        equipos_by_api_id[api_id] = equipo

    return equipo


def sync_wc_fixtures(db: Session, api_key: str) -> dict:
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{FOOTBALL_DATA_URL}/competitions/WC/matches",
            headers={"X-Auth-Token": api_key},
            params={"season": 2026},
        )
        resp.raise_for_status()

    matches = resp.json().get("matches", [])
    logger.info("Fetched %d matches from football-data.org", len(matches))

    all_equipos = db.query(ProdeEquipo).all()
    equipos_by_api_id = {e.api_id: e for e in all_equipos if e.api_id}
    equipos_by_name = {e.nombre_api.lower(): e for e in all_equipos}

    created = updated = points_updated = 0

    for m in matches:
        api_id = m.get("id")
        if not api_id:
            continue

        home = _resolve_team(m.get("homeTeam", {}), equipos_by_api_id, equipos_by_name, db)
        away = _resolve_team(m.get("awayTeam", {}), equipos_by_api_id, equipos_by_name, db)

        raw_date = m.get("utcDate")
        if not raw_date:
            continue
        fecha = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))

        stage_raw = m.get("stage", "GROUP_STAGE")
        fase = STAGE_MAP.get(stage_raw, "grupo")

        group_raw = m.get("group") or ""
        group_letter: str | None = None
        if group_raw.startswith("GROUP_"):
            letter = group_raw[6:]
            if len(letter) == 1 and letter.isalpha():
                group_letter = letter

        estado = STATUS_MAP.get(m.get("status", "SCHEDULED"), "programado")

        score = m.get("score", {})
        ft = score.get("fullTime", {}) or {}
        goles_local = ft.get("home")
        goles_visitante = ft.get("away")

        estadio = m.get("venue") or None
        jornada = m.get("matchday") or None

        partido = db.query(ProdePartido).filter(ProdePartido.api_id == api_id).first()

        if partido is None:
            partido = ProdePartido(
                api_id=api_id,
                equipo_local_id=home.id if home else None,
                equipo_visitante_id=away.id if away else None,
                fecha=fecha,
                estadio=estadio,
                fase=fase,
                grupo=group_letter,
                jornada=jornada,
                goles_local=goles_local,
                goles_visitante=goles_visitante,
                estado=estado,
            )
            db.add(partido)
            db.flush()
            created += 1
        else:
            if home and partido.equipo_local_id is None:
                partido.equipo_local_id = home.id
            if away and partido.equipo_visitante_id is None:
                partido.equipo_visitante_id = away.id
            partido.fecha = fecha
            if estadio:
                partido.estadio = estadio
            partido.goles_local = goles_local
            partido.goles_visitante = goles_visitante
            partido.estado = estado
            updated += 1

        # Recalculate prediction points for finished matches
        if estado == "finalizado" and goles_local is not None and goles_visitante is not None:
            preds = db.query(ProdePrediccion).filter(
                ProdePrediccion.partido_id == partido.id
            ).all()
            for pred in preds:
                new_pts = calculate_points(
                    pred.goles_local, pred.goles_visitante, goles_local, goles_visitante
                )
                if pred.puntos != new_pts:
                    pred.puntos = new_pts
                    points_updated += 1

    db.commit()

    return {
        "partidos_creados": created,
        "partidos_actualizados": updated,
        "predicciones_puntuadas": points_updated,
        "total_partidos_api": len(matches),
    }


def apply_resultado_manual(
    db: Session,
    partido: "ProdePartido",
    goles_local: int,
    goles_visitante: int,
) -> int:
    partido.goles_local = goles_local
    partido.goles_visitante = goles_visitante
    partido.estado = "finalizado"

    preds = db.query(ProdePrediccion).filter(
        ProdePrediccion.partido_id == partido.id
    ).all()
    points_updated = 0
    for pred in preds:
        pred.puntos = calculate_points(
            pred.goles_local, pred.goles_visitante, goles_local, goles_visitante
        )
        points_updated += 1

    db.commit()
    return points_updated
