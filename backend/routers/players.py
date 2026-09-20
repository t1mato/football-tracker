"""Players page routes -- one endpoint per warehouse.queries function the
React Players page needs. No query logic here; every route is routing +
serialization only, same discipline as backend/routers/leagues.py and
backend/routers/teams.py.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.main import get_con
from backend.serialization import record, records
from warehouse.queries import (
    ConnectionLike,
    get_player_bio,
    get_player_scoring_history,
    get_players_directory,
)

router = APIRouter()


@router.get("/api/players")
def players_directory(
    con: Annotated[ConnectionLike, Depends(get_con)],
) -> list[dict[str, object]]:
    return records(get_players_directory(con))


@router.get("/api/players/{player_id}")
def player_bio(
    player_id: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> dict[str, object]:
    bio = get_player_bio(con, player_id)
    if bio is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return record(bio)


@router.get("/api/players/{player_id}/scoring-history")
def player_scoring_history(
    player_id: int, con: Annotated[ConnectionLike, Depends(get_con)]
) -> list[dict[str, object]]:
    return records(get_player_scoring_history(con, player_id))
