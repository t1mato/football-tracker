"""Query layer for the Streamlit app: a cached read-only DuckDB connection
and one function per page's data need.

Read-only, always -- this project's DuckDB allows one writer or many
readers, never both (see CLAUDE.md). This app must never hold a write lock.
"""

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DEFAULT_DB_PATH = Path("football_data.duckdb")

# Mirrors dbt_project.yml's standings_phase_stages var (REGULAR_SEASON,
# GROUP_STAGE, LEAGUE_STAGE) -- the same set mart_standings_over_time.sql
# uses to identify a real league-table phase, applied here against
# fct_standings_snapshot.stage instead of fct_matches.stage.
LEAGUE_TABLE_STAGES = ("REGULAR_SEASON", "GROUP_STAGE", "LEAGUE_STAGE")


@dataclass(frozen=True)
class StandingsResult:
    table: pd.DataFrame | None
    message: str | None


@st.cache_resource
def get_connection(db_path: Path = DEFAULT_DB_PATH) -> duckdb.DuckDBPyConnection:
    """One read-only connection per Streamlit session, not one per rerun."""
    return duckdb.connect(str(db_path), read_only=True)


def get_competitions(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute("""
        select competition_code, competition_name
        from dim_competitions
        order by competition_name
    """).df()


def get_current_season_id(
    con: duckdb.DuckDBPyConnection, competition_code: str
) -> int:
    """The most recent season_id for this competition -- never hardcoded,
    so this never drifts from pipeline.py's CURRENT_SEASON (see the design
    doc for why duplicating that constant here would be a real risk).
    """
    row = con.execute(
        "select max(season_id) from dim_seasons where competition_code = ?",
        [competition_code],
    ).fetchone()
    season_id: int = row[0]
    return season_id


def get_standings(
    con: duckdb.DuckDBPyConnection, competition_code: str, season_id: int
) -> StandingsResult:
    latest = con.execute(
        """
        select max(snapshot_date) from fct_standings_snapshot
        where competition_code = ? and season_id = ?
        """,
        [competition_code, season_id],
    ).fetchone()
    latest_snapshot_date = latest[0] if latest else None

    if latest_snapshot_date is None:
        return StandingsResult(
            table=None, message="No standings available yet for this competition."
        )

    stage_row = con.execute(
        """
        select distinct stage from fct_standings_snapshot
        where competition_code = ? and season_id = ? and snapshot_date = ?
        """,
        [competition_code, season_id, latest_snapshot_date],
    ).fetchone()
    stage = stage_row[0] if stage_row else None

    if stage not in LEAGUE_TABLE_STAGES:
        return StandingsResult(
            table=None,
            message="No table during the knockout stage -- "
            "there's no season-long position to rank.",
        )

    table = con.execute(
        """
        select f.position, t.team_name, f.played_games, f.won, f.draw, f.lost,
               f.goals_for, f.goals_against, f.goal_difference, f.points, f.form
        from fct_standings_snapshot f
        join dim_teams t on f.team_id = t.team_id
        where f.competition_code = ? and f.season_id = ? and f.snapshot_date = ?
        order by f.position
        """,
        [competition_code, season_id, latest_snapshot_date],
    ).df()
    return StandingsResult(table=table, message=None)
