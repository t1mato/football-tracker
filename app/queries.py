"""Streamlit-facing query layer: applies caching to warehouse.queries'
connector-agnostic functions for the Streamlit app specifically.

All query logic lives in warehouse/queries.py. Nothing in this file
executes SQL directly -- it only adds @st.cache_data/@st.cache_resource
around functions imported from there. See warehouse/queries.py's own
docstring for why caching lives here and not there.
"""

import streamlit as st

from warehouse.queries import (
    DEFAULT_DB_PATH,
    LEAGUE_TABLE_STAGES,
    BigQueryConnection,
    ConnectionLike,
    CursorLike,
    StandingsResult,
)
from warehouse.queries import get_competition_seasons as _get_competition_seasons
from warehouse.queries import get_competitions as _get_competitions
from warehouse.queries import get_connection as _get_connection
from warehouse.queries import get_cross_league_stats as _get_cross_league_stats
from warehouse.queries import get_current_season_id as _get_current_season_id
from warehouse.queries import get_current_teams as _get_current_teams
from warehouse.queries import get_head_to_head as _get_head_to_head
from warehouse.queries import get_head_to_head_matches as _get_head_to_head_matches
from warehouse.queries import get_league_fixtures as _get_league_fixtures
from warehouse.queries import get_league_recent_results as _get_league_recent_results
from warehouse.queries import get_match_detail as _get_match_detail
from warehouse.queries import get_player_bio as _get_player_bio
from warehouse.queries import get_player_scoring_history as _get_player_scoring_history
from warehouse.queries import get_players_directory as _get_players_directory
from warehouse.queries import (
    get_reconstructed_final_standings as _get_reconstructed_final_standings,
)
from warehouse.queries import get_standings as _get_standings
from warehouse.queries import get_streaks as _get_streaks
from warehouse.queries import get_team_competitions as _get_team_competitions
from warehouse.queries import get_team_position_history as _get_team_position_history
from warehouse.queries import get_team_recent_form as _get_team_recent_form
from warehouse.queries import get_team_upcoming as _get_team_upcoming
from warehouse.queries import get_teams_for_league as _get_teams_for_league
from warehouse.queries import get_teams_in_season as _get_teams_in_season
from warehouse.queries import get_top_scorers as _get_top_scorers

__all__ = [
    "BigQueryConnection",
    "ConnectionLike",
    "CursorLike",
    "DEFAULT_DB_PATH",
    "LEAGUE_TABLE_STAGES",
    "StandingsResult",
    "get_connection",
    "get_competition_seasons",
    "get_competitions",
    "get_cross_league_stats",
    "get_current_season_id",
    "get_current_teams",
    "get_head_to_head",
    "get_head_to_head_matches",
    "get_league_fixtures",
    "get_league_recent_results",
    "get_match_detail",
    "get_player_bio",
    "get_player_scoring_history",
    "get_players_directory",
    "get_reconstructed_final_standings",
    "get_standings",
    "get_streaks",
    "get_team_competitions",
    "get_team_position_history",
    "get_team_recent_form",
    "get_team_upcoming",
    "get_teams_for_league",
    "get_teams_in_season",
    "get_top_scorers",
]

get_connection = st.cache_resource(_get_connection)
get_competition_seasons = st.cache_data(ttl=600)(_get_competition_seasons)
get_competitions = st.cache_data(ttl=600)(_get_competitions)
get_cross_league_stats = st.cache_data(ttl=600)(_get_cross_league_stats)
get_current_season_id = st.cache_data(ttl=600)(_get_current_season_id)
get_current_teams = st.cache_data(ttl=600)(_get_current_teams)
get_head_to_head = st.cache_data(ttl=600)(_get_head_to_head)
get_head_to_head_matches = st.cache_data(ttl=600)(_get_head_to_head_matches)
get_league_fixtures = st.cache_data(ttl=600)(_get_league_fixtures)
get_league_recent_results = st.cache_data(ttl=600)(_get_league_recent_results)
get_match_detail = st.cache_data(ttl=600)(_get_match_detail)
get_player_bio = st.cache_data(ttl=600)(_get_player_bio)
get_player_scoring_history = st.cache_data(ttl=600)(_get_player_scoring_history)
get_players_directory = st.cache_data(ttl=600)(_get_players_directory)
get_reconstructed_final_standings = st.cache_data(ttl=600)(_get_reconstructed_final_standings)
get_standings = st.cache_data(ttl=600)(_get_standings)
get_streaks = st.cache_data(ttl=600)(_get_streaks)
get_team_competitions = st.cache_data(ttl=600)(_get_team_competitions)
get_team_position_history = st.cache_data(ttl=600)(_get_team_position_history)
get_team_recent_form = st.cache_data(ttl=600)(_get_team_recent_form)
get_team_upcoming = st.cache_data(ttl=600)(_get_team_upcoming)
get_teams_for_league = st.cache_data(ttl=600)(_get_teams_for_league)
get_teams_in_season = st.cache_data(ttl=600)(_get_teams_in_season)
get_top_scorers = st.cache_data(ttl=600)(_get_top_scorers)
