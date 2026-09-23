"""Teams page routes -- one endpoint per warehouse.queries function the
React Teams page needs. No query logic here; every route is routing +
serialization only, same discipline as backend/routers/leagues.py.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.main import get_con
from backend.queries import (
    ConnectionLike,
    get_current_teams,
    get_head_to_head,
    get_head_to_head_matches,
    get_standings,
    get_team_assists,
    get_team_position_history,
    get_team_recent_form,
    get_team_scorers,
    get_team_upcoming,
    get_teams_for_league,
)
from backend.serialization import record, records

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


@router.get("/api/teams/{team_id}/stats")
def team_stats(
    team_id: int, league: str, season: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> dict[str, object]:
    result = get_standings(con, league, season)
    if result.table is None:
        return {"stats": None, "message": result.message}
    row = result.table[result.table["team_id"] == team_id]
    if row.empty:
        return {
            "stats": None,
            "message": "No season stats available for this team in this league yet.",
        }
    return {"stats": record(row.iloc[0]), "message": None}


@router.get("/api/teams/{team_id}/scorers")
def team_scorers(
    team_id: int, league: str, season: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> list[dict[str, object]]:
    return records(get_team_scorers(con, team_id, league, season))


@router.get("/api/teams/{team_id}/assists")
def team_assists(
    team_id: int, league: str, season: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> list[dict[str, object]]:
    return records(get_team_assists(con, team_id, league, season))


@router.get("/api/teams/{team_id}/position-history")
def team_position_history(
    team_id: int, league: str, season: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> list[dict[str, object]]:
    return records(get_team_position_history(con, team_id, league, season))


@router.get("/api/teams/{team_id}/head-to-head/{opponent_id}")
def head_to_head(
    team_id: int, opponent_id: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> dict[str, object] | None:
    result = get_head_to_head(con, team_id, opponent_id)
    if result is None:
        return None
    return record(result)


@router.get("/api/teams/{team_id}/head-to-head/{opponent_id}/matches")
def head_to_head_matches(
    team_id: int, opponent_id: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> list[dict[str, object]]:
    return records(get_head_to_head_matches(con, team_id, opponent_id))
