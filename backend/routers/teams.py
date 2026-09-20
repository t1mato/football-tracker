"""Teams page routes -- one endpoint per warehouse.queries function the
React Teams page needs. No query logic here; every route is routing +
serialization only, same discipline as backend/routers/leagues.py.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.main import get_con
from backend.serialization import records
from warehouse.queries import (
    ConnectionLike,
    get_current_teams,
    get_team_recent_form,
    get_team_upcoming,
    get_teams_for_league,
)

router = APIRouter()


@router.get("/api/teams")
def teams_for_league(
    league: str, season: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> list[dict[str, object]]:
    return records(get_teams_for_league(con, league, season))


@router.get("/api/teams/all")
def all_teams(
    con: Annotated[ConnectionLike, Depends(get_con)],
) -> list[dict[str, object]]:
    return records(get_current_teams(con))


@router.get("/api/teams/{team_id}/form")
def team_form(
    team_id: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> list[dict[str, object]]:
    return records(get_team_recent_form(con, team_id))


@router.get("/api/teams/{team_id}/upcoming")
def team_upcoming(
    team_id: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> list[dict[str, object]]:
    return records(get_team_upcoming(con, team_id))
