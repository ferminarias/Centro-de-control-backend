"""
Sync service for football-data.org API.
Competition: WC (FIFA World Cup), season 2026.
"""
from __future__ import annotations

import logging
import time
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

# Maps all known API name variants → our stored nombre_api (lowercase)
API_NAME_NORMALIZE: dict[str, str] = {
    # Ivory Coast
    "côte d'ivoire": "ivory coast",
    "cote d'ivoire": "ivory coast",
    "côte d'ivoire": "ivory coast",
    # Turkey
    "turkey": "türkiye",
    # DR Congo
    "dr congo": "dr congo",
    "congo dr": "dr congo",
    "democratic republic of the congo": "dr congo",
    "democratic republic of congo": "dr congo",
    "congo, the democratic republic of the": "dr congo",
    # Korea
    "south korea": "korea republic",
    "republic of korea": "korea republic",
    # Czechia
    "czech republic": "czechia",
    # USA
    "united states of america": "united states",
    "usa": "united states",
    # Curacao variants (with/without accent)
    "curacao": "curaçao",
    # Cape Verde
    "cabo verde": "cape verde",
    # Saudi Arabia
    "ksa": "saudi arabia",
    # New Zealand
    "new zealand": "new zealand",
}

# Server-side live data cache (per-process, avoids hammering API rate limits)
_live_cache: dict = {"ts": 0.0, "matches": []}
LIVE_CACHE_TTL = 55  # seconds (under 1-minute rate limit window)


def _normalize_api_name(raw: str) -> str:
    """Normalize an API team name to match our stored nombre_api."""
    clean = raw.strip().lower()
    return API_NAME_NORMALIZE.get(clean, clean)


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

    # 1. Exact API id match (fastest)
    if api_id and api_id in equipos_by_api_id:
        return equipos_by_api_id[api_id]

    # 2. Try all name variants the API provides
    candidates = [
        api_team.get("name", ""),
        api_team.get("shortName", ""),
        api_team.get("tla", ""),
    ]
    equipo: Optional[ProdeEquipo] = None
    for raw in candidates:
        if not raw:
            continue
        normalized = _normalize_api_name(raw)
        equipo = equipos_by_name.get(normalized)
        if equipo:
            break

    # 3. Store api_id for faster future lookups
    if equipo and api_id and not equipo.api_id:
        equipo.api_id = api_id
        equipos_by_api_id[api_id] = equipo

    return equipo


def _parse_match(m: dict, equipos_by_api_id: dict, equipos_by_name: dict, db: Session) -> Optional[dict]:
    """Parse a raw API match dict into a structured dict for DB upsert."""
    api_id = m.get("id")
    raw_date = m.get("utcDate")
    if not api_id or not raw_date:
        return None

    home = _resolve_team(m.get("homeTeam", {}), equipos_by_api_id, equipos_by_name, db)
    away = _resolve_team(m.get("awayTeam", {}), equipos_by_api_id, equipos_by_name, db)

    fecha = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
    fase = STAGE_MAP.get(m.get("stage", "GROUP_STAGE"), "grupo")

    group_raw = m.get("group") or ""
    group_letter: Optional[str] = None
    if group_raw.startswith("GROUP_"):
        letter = group_raw[6:]
        if len(letter) == 1 and letter.isalpha():
            group_letter = letter

    api_status = m.get("status", "SCHEDULED")
    estado = STATUS_MAP.get(api_status, "programado")
    # PAUSED = halftime, keep as en_juego but flag it
    is_ht = api_status == "PAUSED"

    score = m.get("score", {}) or {}
    ft = score.get("fullTime", {}) or {}
    ht = score.get("halfTime", {}) or {}
    goles_local = ft.get("home")
    goles_visitante = ft.get("away")
    # During the game, fullTime scores are null — use regular score object
    if goles_local is None and api_status == "IN_PLAY":
        reg = score.get("regularTime", {}) or {}
        goles_local = reg.get("home")
        goles_visitante = reg.get("away")

    return {
        "api_id": api_id,
        "home": home,
        "away": away,
        "fecha": fecha,
        "estadio": m.get("venue") or None,
        "fase": fase,
        "grupo": group_letter,
        "jornada": m.get("matchday") or None,
        "goles_local": goles_local,
        "goles_visitante": goles_visitante,
        "estado": estado,
        "is_ht": is_ht,
    }


def _upsert_partido(db: Session, parsed: dict, recalc_points: bool = True) -> tuple[str, int]:
    """Insert or update a match. Returns ('created'|'updated', points_recalced)."""
    partido = db.query(ProdePartido).filter(ProdePartido.api_id == parsed["api_id"]).first()
    pts_updated = 0

    if partido is None:
        home = parsed["home"]
        away = parsed["away"]
        partido = ProdePartido(
            api_id=parsed["api_id"],
            equipo_local_id=home.id if home else None,
            equipo_visitante_id=away.id if away else None,
            fecha=parsed["fecha"],
            estadio=parsed["estadio"],
            fase=parsed["fase"],
            grupo=parsed["grupo"],
            jornada=parsed["jornada"],
            goles_local=parsed["goles_local"],
            goles_visitante=parsed["goles_visitante"],
            estado=parsed["estado"],
        )
        db.add(partido)
        db.flush()
        action = "created"
    else:
        home, away = parsed["home"], parsed["away"]
        if home and partido.equipo_local_id is None:
            partido.equipo_local_id = home.id
        if away and partido.equipo_visitante_id is None:
            partido.equipo_visitante_id = away.id
        partido.fecha = parsed["fecha"]
        if parsed["estadio"]:
            partido.estadio = parsed["estadio"]
        partido.goles_local = parsed["goles_local"]
        partido.goles_visitante = parsed["goles_visitante"]
        partido.estado = parsed["estado"]
        action = "updated"

    if (
        recalc_points
        and parsed["estado"] == "finalizado"
        and parsed["goles_local"] is not None
        and parsed["goles_visitante"] is not None
    ):
        preds = db.query(ProdePrediccion).filter(ProdePrediccion.partido_id == partido.id).all()
        for pred in preds:
            new_pts = calculate_points(
                pred.goles_local, pred.goles_visitante,
                parsed["goles_local"], parsed["goles_visitante"],
            )
            if pred.puntos != new_pts:
                pred.puntos = new_pts
                pts_updated += 1

    return action, pts_updated


def sync_wc_fixtures(db: Session, api_key: str) -> dict:
    """Full sync: all WC 2026 matches."""
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{FOOTBALL_DATA_URL}/competitions/WC/matches",
            headers={"X-Auth-Token": api_key},
            params={"season": 2026},
        )
        resp.raise_for_status()

    matches = resp.json().get("matches", [])
    logger.info("Full sync: %d matches from football-data.org", len(matches))

    all_equipos = db.query(ProdeEquipo).all()
    equipos_by_api_id = {e.api_id: e for e in all_equipos if e.api_id}
    equipos_by_name = {e.nombre_api.lower(): e for e in all_equipos}

    created = updated = points_updated = 0

    for m in matches:
        parsed = _parse_match(m, equipos_by_api_id, equipos_by_name, db)
        if not parsed:
            continue
        action, pts = _upsert_partido(db, parsed)
        if action == "created":
            created += 1
        else:
            updated += 1
        points_updated += pts

    db.commit()

    return {
        "partidos_creados": created,
        "partidos_actualizados": updated,
        "predicciones_puntuadas": points_updated,
        "total_partidos_api": len(matches),
    }


def get_live_matches_from_api(api_key: str) -> list[dict]:
    """Fetch IN_PLAY matches with 55-second server cache."""
    now = time.time()
    if now - _live_cache["ts"] < LIVE_CACHE_TTL:
        return _live_cache["matches"]

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{FOOTBALL_DATA_URL}/competitions/WC/matches",
                headers={"X-Auth-Token": api_key},
                params={"season": 2026, "status": "IN_PLAY,PAUSED"},
            )
            resp.raise_for_status()
        data = resp.json().get("matches", [])
    except Exception as exc:
        logger.warning("Live sync API error: %s", exc)
        data = []

    _live_cache["ts"] = now
    _live_cache["matches"] = data
    return data


def sync_live_matches(db: Session, api_key: str) -> dict:
    """Sync only currently live matches (uses server cache)."""
    matches = get_live_matches_from_api(api_key)

    if not matches:
        return {"en_juego": 0, "actualizados": 0}

    all_equipos = db.query(ProdeEquipo).all()
    equipos_by_api_id = {e.api_id: e for e in all_equipos if e.api_id}
    equipos_by_name = {e.nombre_api.lower(): e for e in all_equipos}

    updated = 0
    for m in matches:
        parsed = _parse_match(m, equipos_by_api_id, equipos_by_name, db)
        if not parsed:
            continue
        _upsert_partido(db, parsed, recalc_points=False)
        updated += 1

    db.commit()
    return {"en_juego": len(matches), "actualizados": updated}


def apply_resultado_manual(
    db: Session,
    partido: ProdePartido,
    goles_local: int,
    goles_visitante: int,
) -> int:
    partido.goles_local = goles_local
    partido.goles_visitante = goles_visitante
    partido.estado = "finalizado"

    preds = db.query(ProdePrediccion).filter(ProdePrediccion.partido_id == partido.id).all()
    points_updated = 0
    for pred in preds:
        pred.puntos = calculate_points(
            pred.goles_local, pred.goles_visitante, goles_local, goles_visitante
        )
        points_updated += 1

    db.commit()
    return points_updated
