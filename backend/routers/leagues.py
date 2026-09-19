"""Leagues page routes -- one endpoint per warehouse.queries function the
React Leagues page needs. No query logic here; every route is routing +
serialization only, same discipline as backend/main.py's existing
/api/competitions route.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.main import get_con
from backend.serialization import record, records
from warehouse.queries import (
    ConnectionLike,
    get_competition_seasons,
    get_cross_league_stats,
    get_current_season_id,
    get_match_detail,
    get_teams_in_season,
)

router = APIRouter()


@router.get("/api/leagues/{code}/seasons")
def seasons(
    code: str, con: Annotated[ConnectionLike, Depends(get_con)]
) -> list[dict[str, object]]:
    return records(get_competition_seasons(con, code))


@router.get("/api/leagues/{code}/current-season")
def current_season(
    code: str, con: Annotated[ConnectionLike, Depends(get_con)]
) -> dict[str, int]:
    return {"season_id": get_current_season_id(con, code)}


@router.get("/api/leagues/{code}/teams-in-season")
def teams_in_season(
    code: str, season: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> list[dict[str, object]]:
    return records(get_teams_in_season(con, code, season))


@router.get("/api/cross-league-stats")
def cross_league_stats(
    con: Annotated[ConnectionLike, Depends(get_con)],
) -> list[dict[str, object]]:
    return records(get_cross_league_stats(con))


@router.get("/api/matches/{match_id}")
def match_detail(
    match_id: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> dict[str, object]:
    detail = get_match_detail(con, match_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return record(detail)
