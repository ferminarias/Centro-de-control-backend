"""
Client for footballdata.io Predictions API.
Docs: https://footballdata.io/api/v1
"""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

FOOTBALLDATA_IO_BASE = "https://footballdata.io/api/v1"

TIMEOUT = 5.0  # seconds


@dataclass
class MatchPrediction:
    home_win: float
    draw: float
    away_win: float
    source: str = "footballdata.io"

    def as_pct(self) -> dict[str, str]:
        return {
            "home_win": f"{self.home_win * 100:.0f}%",
            "draw": f"{self.draw * 100:.0f}%",
            "away_win": f"{self.away_win * 100:.0f}%",
        }


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "NodisProde/1.0",
    }


def get_prediction(
    api_key: str,
    home_team: str,
    away_team: str,
    fixture_date: Optional[str] = None,
) -> Optional[MatchPrediction]:
    """
    Try multiple endpoint patterns to get win probabilities for a match.
    Returns None if the API is unavailable or the match is not found.
    """
    if not api_key:
        return None

    headers = _headers(api_key)

    # Strategy 1: direct predictions endpoint with team names
    candidates = [
        f"{FOOTBALLDATA_IO_BASE}/predictions",
        f"{FOOTBALLDATA_IO_BASE}/match-predictions",
        f"{FOOTBALLDATA_IO_BASE}/fixtures/predictions",
    ]

    params_by_name = {
        "home": home_team,
        "away": away_team,
    }
    if fixture_date:
        params_by_name["date"] = fixture_date

    with httpx.Client(verify=False, timeout=TIMEOUT, follow_redirects=True) as client:
        for url in candidates:
            try:
                r = client.get(url, headers=headers, params=params_by_name)
                if r.status_code == 200 and "application/json" in r.headers.get("content-type", ""):
                    data = r.json()
                    pred = _parse_prediction(data)
                    if pred:
                        logger.info("footballdata.io prediction for %s vs %s: %s", home_team, away_team, pred)
                        return pred
            except Exception as exc:
                logger.debug("footballdata.io %s failed: %s", url, exc)

        # Strategy 2: fetch today/upcoming fixtures and find by team name, then get predictions
        try:
            for fixtures_ep in ["/fixtures/today", "/fixtures/upcoming", "/fixtures"]:
                r = client.get(
                    f"{FOOTBALLDATA_IO_BASE}{fixtures_ep}",
                    headers=headers,
                    params={"home": home_team, "away": away_team},
                )
                if r.status_code == 200 and "application/json" in r.headers.get("content-type", ""):
                    fixtures = r.json()
                    fixture_id = _find_fixture_id(fixtures, home_team, away_team)
                    if fixture_id:
                        pred_r = client.get(
                            f"{FOOTBALLDATA_IO_BASE}/fixtures/{fixture_id}/predictions",
                            headers=headers,
                        )
                        if pred_r.status_code == 200:
                            pred = _parse_prediction(pred_r.json())
                            if pred:
                                return pred
        except Exception as exc:
            logger.debug("footballdata.io fixture lookup failed: %s", exc)

    return None


def _parse_prediction(data: dict | list) -> Optional[MatchPrediction]:
    """Extract home_win / draw / away_win from any known response shape."""
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        return None

    # Shape 1: { "home_win": 0.58, "draw": 0.25, "away_win": 0.17 }
    if "home_win" in data and "draw" in data and "away_win" in data:
        return MatchPrediction(
            home_win=float(data["home_win"]),
            draw=float(data["draw"]),
            away_win=float(data["away_win"]),
        )

    # Shape 2: { "predictions": { "home_win": ..., ... } }
    if "predictions" in data:
        return _parse_prediction(data["predictions"])

    # Shape 3: { "probabilities": { "home": ..., "draw": ..., "away": ... } }
    if "probabilities" in data:
        p = data["probabilities"]
        home = p.get("home", p.get("home_win", 0))
        draw = p.get("draw", 0)
        away = p.get("away", p.get("away_win", 0))
        if home or draw or away:
            return MatchPrediction(home_win=float(home), draw=float(draw), away_win=float(away))

    # Shape 4: { "data": { ... } }
    if "data" in data:
        return _parse_prediction(data["data"])

    return None


def _find_fixture_id(fixtures_data: dict | list, home: str, away: str) -> Optional[int]:
    """Walk a fixtures response to find the ID of the matching game."""
    items = fixtures_data if isinstance(fixtures_data, list) else fixtures_data.get("data", fixtures_data.get("fixtures", []))
    home_lower, away_lower = home.lower(), away.lower()
    for f in items:
        if not isinstance(f, dict):
            continue
        h = str(f.get("home_team", f.get("homeTeam", f.get("home", "")))).lower()
        a = str(f.get("away_team", f.get("awayTeam", f.get("away", "")))).lower()
        if home_lower in h and away_lower in a:
            return f.get("id") or f.get("fixture_id")
    return None
