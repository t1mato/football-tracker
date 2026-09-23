"""FastAPI-facing query layer: applies backend/caching.py's TTL cache to
warehouse.queries' connector-agnostic functions for the backend specifically
-- the app/queries.py counterpart backend/main.py's own docstring already
promised ("just with HTTP instead of @st.cache_data") but never delivered
until now.

All query logic lives in warehouse/queries.py. Nothing in this file
executes SQL directly -- it only adds @cached around functions imported
from there. Routers import query functions from here, not from
warehouse.queries directly.

get_connection/ConnectionLike/DEFAULT_DB_PATH are re-exported unwrapped:
unlike Streamlit's per-rerun st.cache_resource, FastAPI already gives the
connection a single process-lifetime instance via backend/main.py's
lifespan handler, so there's no separate resource-caching concern here.
"""

from backend.caching import cached
from warehouse.queries import DEFAULT_DB_PATH, ConnectionLike, StandingsResult
from warehouse.queries import get_competition_seasons as _get_competition_seasons
from warehouse.queries import get_competitions as _get_competitions
from warehouse.queries import get_connection as get_connection
from warehouse.queries import get_current_season_id as _get_current_season_id
from warehouse.queries import get_current_teams as _get_current_teams
from warehouse.queries import get_head_to_head as _get_head_to_head
from warehouse.queries import get_head_to_head_matches as _get_head_to_head_matches
from warehouse.queries import get_league_fixtures as _get_league_fixtures
from warehouse.queries import get_league_position_history as _get_league_position_history
from warehouse.queries import get_league_recent_results as _get_league_recent_results
from warehouse.queries import get_match_detail as _get_match_detail
from warehouse.queries import get_player_bio as _get_player_bio
from warehouse.queries import get_player_scoring_history as _get_player_scoring_history
from warehouse.queries import get_players_directory as _get_players_directory
from warehouse.queries import (
    get_reconstructed_final_standings as _get_reconstructed_final_standings,
)
from warehouse.queries import get_standings as _get_standings
from warehouse.queries import get_team_assists as _get_team_assists
from warehouse.queries import get_team_position_history as _get_team_position_history
from warehouse.queries import get_team_recent_form as _get_team_recent_form
from warehouse.queries import get_team_scorers as _get_team_scorers
from warehouse.queries import get_team_upcoming as _get_team_upcoming
from warehouse.queries import get_teams_for_league as _get_teams_for_league
from warehouse.queries import get_teams_in_season as _get_teams_in_season
from warehouse.queries import get_top_assists as _get_top_assists
from warehouse.queries import get_top_scorers as _get_top_scorers

__all__ = [
    "ConnectionLike",
    "DEFAULT_DB_PATH",
    "StandingsResult",
    "get_connection",
    "get_competition_seasons",
    "get_competitions",
    "get_current_season_id",
    "get_current_teams",
    "get_head_to_head",
    "get_head_to_head_matches",
    "get_league_fixtures",
    "get_league_position_history",
    "get_league_recent_results",
    "get_match_detail",
    "get_player_bio",
    "get_player_scoring_history",
    "get_players_directory",
    "get_reconstructed_final_standings",
    "get_standings",
    "get_team_assists",
    "get_team_position_history",
    "get_team_recent_form",
    "get_team_scorers",
    "get_team_upcoming",
    "get_teams_for_league",
    "get_teams_in_season",
    "get_top_assists",
    "get_top_scorers",
]

get_competition_seasons = cached()(_get_competition_seasons)
get_competitions = cached()(_get_competitions)
get_current_season_id = cached()(_get_current_season_id)
get_current_teams = cached()(_get_current_teams)
get_head_to_head = cached()(_get_head_to_head)
get_head_to_head_matches = cached()(_get_head_to_head_matches)
get_league_fixtures = cached()(_get_league_fixtures)
get_league_position_history = cached()(_get_league_position_history)
get_league_recent_results = cached()(_get_league_recent_results)
get_match_detail = cached()(_get_match_detail)
get_player_bio = cached()(_get_player_bio)
get_player_scoring_history = cached()(_get_player_scoring_history)
get_players_directory = cached()(_get_players_directory)
get_reconstructed_final_standings = cached()(_get_reconstructed_final_standings)
get_standings = cached()(_get_standings)
get_team_assists = cached()(_get_team_assists)
get_team_position_history = cached()(_get_team_position_history)
get_team_recent_form = cached()(_get_team_recent_form)
get_team_scorers = cached()(_get_team_scorers)
get_team_upcoming = cached()(_get_team_upcoming)
get_teams_for_league = cached()(_get_teams_for_league)
get_teams_in_season = cached()(_get_teams_in_season)
get_top_assists = cached()(_get_top_assists)
get_top_scorers = cached()(_get_top_scorers)
