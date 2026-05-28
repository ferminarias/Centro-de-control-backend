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

# FIFA WC 2026 TLA (3-letter code) → ISO 3166-1 alpha-2 (for flags)
TLA_TO_ISO: dict[str, str] = {
    "MEX": "MX", "RSA": "ZA", "KOR": "KR", "CZE": "CZ",
    "CAN": "CA", "BIH": "BA", "QAT": "QA", "SUI": "CH",
    "BRA": "BR", "MAR": "MA", "HAI": "HT", "SCO": "GB",
    "USA": "US", "PAR": "PY", "AUS": "AU", "TUR": "TR",
    "GER": "DE", "CUW": "CW", "CIV": "CI", "ECU": "EC",
    "NED": "NL", "JPN": "JP", "SWE": "SE", "TUN": "TN",
    "BEL": "BE", "EGY": "EG", "IRN": "IR", "NZL": "NZ",
    "ESP": "ES", "CPV": "CV", "KSA": "SA", "URU": "UY",
    "FRA": "FR", "SEN": "SN", "IRQ": "IQ", "NOR": "NO",
    "ARG": "AR", "ALG": "DZ", "AUT": "AT", "JOR": "JO",
    "POR": "PT", "COD": "CD", "UZB": "UZ", "COL": "CO",
    "ENG": "GB", "CRO": "HR", "GHA": "GH", "PAN": "PA",
}

# TLA → Spanish name (for auto-created teams)
TLA_TO_NOMBRE: dict[str, str] = {
    "MEX": "México", "RSA": "Sudáfrica", "KOR": "Corea del Sur", "CZE": "República Checa",
    "CAN": "Canadá", "BIH": "Bosnia y Herzegovina", "QAT": "Qatar", "SUI": "Suiza",
    "BRA": "Brasil", "MAR": "Marruecos", "HAI": "Haití", "SCO": "Escocia",
    "USA": "Estados Unidos", "PAR": "Paraguay", "AUS": "Australia", "TUR": "Turquía",
    "GER": "Alemania", "CUW": "Curazao", "CIV": "Costa de Marfil", "ECU": "Ecuador",
    "NED": "Países Bajos", "JPN": "Japón", "SWE": "Suecia", "TUN": "Túnez",
    "BEL": "Bélgica", "EGY": "Egipto", "IRN": "Irán", "NZL": "Nueva Zelanda",
    "ESP": "España", "CPV": "Cabo Verde", "KSA": "Arabia Saudita", "URU": "Uruguay",
    "FRA": "Francia", "SEN": "Senegal", "IRQ": "Irak", "NOR": "Noruega",
    "ARG": "Argentina", "ALG": "Argelia", "AUT": "Austria", "JOR": "Jordania",
    "POR": "Portugal", "COD": "Congo DR", "UZB": "Uzbekistán", "COL": "Colombia",
    "ENG": "Inglaterra", "CRO": "Croacia", "GHA": "Ghana", "PAN": "Panamá",
}

# All known API name variants → our stored nombre_api (lowercase)
API_NAME_NORMALIZE: dict[str, str] = {
    "côte d'ivoire": "ivory coast",
    "cote d'ivoire": "ivory coast",
    "turkey": "türkiye",
    "dr congo": "dr congo",
    "congo dr": "dr congo",
    "democratic republic of the congo": "dr congo",
    "democratic republic of congo": "dr congo",
    "south korea": "korea republic",
    "republic of korea": "korea republic",
    "czech republic": "czechia",
    "united states of america": "united states",
    "usa": "united states",
    "curacao": "curaçao",
    "cabo verde": "cape verde",
    "ksa": "saudi arabia",
    "england": "england",
    "scotland": "scotland",
    "iran": "iran",
    "iraq": "iraq",
}

# Server-side live data cache
_live_cache: dict = {"ts": 0.0, "matches": []}
LIVE_CACHE_TTL = 55


def _normalize_api_name(raw: str) -> str:
    clean = raw.strip().lower()
    return API_NAME_NORMALIZE.get(clean, clean)


def calculate_points(pred_local: int, pred_visit: int, real_local: int, real_visit: int) -> int:
    if pred_local == real_local and pred_visit == real_visit:
        return 5
    pred_sign = (pred_local > pred_visit) - (pred_local < pred_visit)
    real_sign = (real_local > real_visit) - (real_local < real_visit)
    return 3 if pred_sign == real_sign else 0


def _resolve_team(
    api_team: dict,
    equipos_by_api_id: dict,
    equipos_by_name: dict,
    db: Session,
    group_letter: Optional[str] = None,
) -> Optional[ProdeEquipo]:
    api_id = api_team.get("id")
    tla = (api_team.get("tla") or "").strip().upper()

    # 1. Fast path: already have this api_id
    if api_id and api_id in equipos_by_api_id:
        return equipos_by_api_id[api_id]

    # 2. Try all name variants
    equipo: Optional[ProdeEquipo] = None
    for raw in [api_team.get("name", ""), api_team.get("shortName", ""), tla]:
        if not raw:
            continue
        normalized = _normalize_api_name(raw)
        equipo = equipos_by_name.get(normalized)
        if equipo:
            break

    # 3. Auto-create team from API data using TLA → ISO/nombre mapping
    if equipo is None and api_id:
        iso = TLA_TO_ISO.get(tla, "UN")
        nombre = TLA_TO_NOMBRE.get(tla) or api_team.get("shortName") or api_team.get("name") or f"Equipo {api_id}"
        nombre_api = api_team.get("name") or nombre
        logger.warning(
            "Team not found in DB: id=%s name='%s' tla='%s' → auto-creating as '%s' (ISO: %s)",
            api_id, api_team.get("name"), tla, nombre, iso,
        )
        equipo = ProdeEquipo(
            nombre=nombre,
            nombre_api=nombre_api,
            codigo_iso=iso,
            grupo=group_letter or "?",
            api_id=api_id,
        )
        db.add(equipo)
        db.flush()
        equipos_by_api_id[api_id] = equipo
        equipos_by_name[nombre_api.lower()] = equipo

    # 4. Persist api_id if matched by name
    if equipo and api_id and not equipo.api_id:
        equipo.api_id = api_id
        equipos_by_api_id[api_id] = equipo

    return equipo


def _parse_match(m: dict, equipos_by_api_id: dict, equipos_by_name: dict, db: Session) -> Optional[dict]:
    api_id = m.get("id")
    raw_date = m.get("utcDate")
    if not api_id or not raw_date:
        return None

    stage_raw = m.get("stage", "GROUP_STAGE")
    fase = STAGE_MAP.get(stage_raw, "grupo")
    group_raw = m.get("group") or ""
    group_letter: Optional[str] = None
    if group_raw.startswith("GROUP_"):
        letter = group_raw[6:]
        if len(letter) == 1 and letter.isalpha():
            group_letter = letter

    home = _resolve_team(m.get("homeTeam", {}), equipos_by_api_id, equipos_by_name, db, group_letter)
    away = _resolve_team(m.get("awayTeam", {}), equipos_by_api_id, equipos_by_name, db, group_letter)

    fecha = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
    api_status = m.get("status", "SCHEDULED")
    estado = STATUS_MAP.get(api_status, "programado")

    score = m.get("score", {}) or {}
    ft = score.get("fullTime", {}) or {}
    goles_local = ft.get("home")
    goles_visitante = ft.get("away")
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
    }


def _upsert_partido(db: Session, parsed: dict, recalc_points: bool = True) -> tuple[str, int]:
    partido = db.query(ProdePartido).filter(ProdePartido.api_id == parsed["api_id"]).first()
    pts_updated = 0

    if partido is None:
        home, away = parsed["home"], parsed["away"]
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
    unmatched_teams: set[str] = set()

    for m in matches:
        parsed = _parse_match(m, equipos_by_api_id, equipos_by_name, db)
        if not parsed:
            continue
        if parsed["home"] is None:
            unmatched_teams.add(m.get("homeTeam", {}).get("name", "?"))
        if parsed["away"] is None:
            unmatched_teams.add(m.get("awayTeam", {}).get("name", "?"))
        action, pts = _upsert_partido(db, parsed)
        if action == "created":
            created += 1
        else:
            updated += 1
        points_updated += pts

    db.commit()

    result: dict = {
        "partidos_creados": created,
        "partidos_actualizados": updated,
        "predicciones_puntuadas": points_updated,
        "total_partidos_api": len(matches),
    }
    if unmatched_teams:
        result["equipos_sin_match"] = list(unmatched_teams)
        logger.warning("Unmatched teams after sync: %s", unmatched_teams)

    return result


def get_live_matches_from_api(api_key: str) -> list[dict]:
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
    pts = 0
    for pred in preds:
        pred.puntos = calculate_points(
            pred.goles_local, pred.goles_visitante, goles_local, goles_visitante
        )
        pts += 1

    db.commit()
    return pts
