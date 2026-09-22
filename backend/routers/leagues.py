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
    get_current_season_id,
    get_league_fixtures,
    get_league_position_history,
    get_league_recent_results,
    get_match_detail,
    get_reconstructed_final_standings,
    get_standings,
    get_teams_in_season,
    get_top_assists,
    get_top_scorers,
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


@router.get("/api/matches/{match_id}")
def match_detail(
    match_id: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> dict[str, object]:
    detail = get_match_detail(con, match_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return record(detail)


@router.get("/api/leagues/{code}/standings")
def standings(
    code: str, season: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> dict[str, object]:
    result = get_standings(con, code, season)
    if result.table is None:
        return {"table": None, "message": result.message}
    return {"table": records(result.table), "message": None}


@router.get("/api/leagues/{code}/reconstructed-standings")
def reconstructed_standings(
    code: str, season: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> list[dict[str, object]]:
    return records(get_reconstructed_final_standings(con, code, season))


@router.get("/api/leagues/{code}/results")
def results(
    code: str, season: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> list[dict[str, object]]:
    return records(get_league_recent_results(con, code, season))


@router.get("/api/leagues/{code}/fixtures")
def fixtures(
    code: str, season: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> list[dict[str, object]]:
    return records(get_league_fixtures(con, code, season))


@router.get("/api/leagues/{code}/scorers")
def scorers(
    code: str, season: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> list[dict[str, object]]:
    return records(get_top_scorers(con, code, season))


@router.get("/api/leagues/{code}/assists")
def assists(
    code: str, season: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> list[dict[str, object]]:
    return records(get_top_assists(con, code, season))


@router.get("/api/leagues/{code}/position-history")
def position_history(
    code: str, season: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> list[dict[str, object]]:
    return records(get_league_position_history(con, code, season))
