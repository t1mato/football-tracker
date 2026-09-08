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

_FINISHED_STATUSES = ("FINISHED", "AWARDED")
_UPCOMING_STATUSES = ("SCHEDULED", "TIMED")

_MATCH_COLUMNS = (
    "f.match_id, f.kickoff_utc, f.kickoff_time_confirmed, "
    "ht.team_name as home_team_name, aw.team_name as away_team_name, "
    "f.full_time_home, f.full_time_away"
)


@dataclass(frozen=True)
class StandingsResult:
    table: pd.DataFrame | None
    message: str | None


@st.cache_resource
def get_connection(db_path: Path = DEFAULT_DB_PATH) -> duckdb.DuckDBPyConnection:
    """One read-only connection per Streamlit session, not one per rerun."""
    con = duckdb.connect(str(db_path), read_only=True)
    # Load-bearing, not cosmetic -- same reasoning as transform/profiles.yml's
    # TimeZone: 'UTC' setting. fct_matches.kickoff_utc is TIMESTAMP WITH TIME
    # ZONE; without an explicit session TimeZone, DuckDB converts it to the
    # MACHINE's local timezone whenever it's read out (e.g. via .df()), and
    # nothing downstream would catch that -- app/formatting.py's kickoff
    # formatter would print a wrong wall-clock time with a literal "UTC"
    # suffix, silently. This project is UTC end-to-end (see CLAUDE.md);
    # this is the one connection that hadn't yet been pinned to it.
    con.execute("SET TimeZone='UTC'")
    return con


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
    # MAX(...) aggregate always returns exactly one row (possibly NULL), never zero rows,
    # so fetchone() always succeeds. Unpack directly.
    latest_snapshot_date = latest[0]

    if latest_snapshot_date is None:
        return StandingsResult(
            table=None, message="No standings available yet for this competition."
        )

    stage_row = con.execute(
        """
        select distinct stage from fct_standings_snapshot
        where competition_code = ? and season_id = ? and snapshot_date = ?
        order by stage
        """,
        [competition_code, season_id, latest_snapshot_date],
    ).fetchone()
    # DISTINCT with no ORDER BY has unspecified row order in DuckDB. ORDER BY stage makes
    # the result deterministic (same input always gives same output), though alphabetical
    # ordering does not guarantee "prefer league-table stages" semantics (a knockout stage
    # named "FINAL" would still lose to "GROUP_STAGE" alphabetically). This scenario
    # (multiple stages per snapshot_date) has never been observed in real data.
    # Unlike the aggregate above, SELECT DISTINCT can return zero rows if no snapshots
    # exist for this (competition, season, date), so the None check is needed here.
    stage = stage_row[0] if stage_row else None

    if stage not in LEAGUE_TABLE_STAGES:
        return StandingsResult(
            table=None,
            message="No table during the knockout stage -- "
            "there's no season-long position to rank.",
        )

    table = con.execute(
        """
        select f.position, t.team_id, t.team_name, f.played_games, f.won, f.draw,
               f.lost, f.goals_for, f.goals_against, f.goal_difference, f.points, f.form
        from fct_standings_snapshot f
        join dim_teams t on f.team_id = t.team_id
        where f.competition_code = ? and f.season_id = ? and f.snapshot_date = ?
          and f.stage = ? and f.table_type = 'TOTAL'
        order by f.position
        """,
        [competition_code, season_id, latest_snapshot_date, stage],
    ).df()
    return StandingsResult(table=table, message=None)


def get_recent_matches(
    con: duckdb.DuckDBPyConnection, competition_code: str, season_id: int
) -> pd.DataFrame:
    return con.execute(
        f"""
        select {_MATCH_COLUMNS}
        from fct_matches f
        join dim_teams ht on f.home_team_id = ht.team_id
        join dim_teams aw on f.away_team_id = aw.team_id
        where f.competition_code = ? and f.season_id = ?
          and f.status in ('{"', '".join(_FINISHED_STATUSES)}')
        order by f.kickoff_utc desc
        limit 10
        """,
        [competition_code, season_id],
    ).df()


def get_upcoming_matches(
    con: duckdb.DuckDBPyConnection, competition_code: str, season_id: int
) -> pd.DataFrame:
    return con.execute(
        f"""
        select {_MATCH_COLUMNS}
        from fct_matches f
        join dim_teams ht on f.home_team_id = ht.team_id
        join dim_teams aw on f.away_team_id = aw.team_id
        where f.competition_code = ? and f.season_id = ?
          and f.status in ('{"', '".join(_UPCOMING_STATUSES)}')
        order by f.kickoff_utc asc
        limit 10
        """,
        [competition_code, season_id],
    ).df()


def get_matches_for_picker(
    con: duckdb.DuckDBPyConnection, competition_code: str, season_id: int
) -> pd.DataFrame:
    """Every match in this competition/season, for a match-selection dropdown.

    Unlike get_recent_matches/get_upcoming_matches, no status filter and no
    limit -- the picker needs to find any match, not just the last/next 10.
    """
    return con.execute(
        """
        select f.match_id, f.kickoff_utc,
               ht.team_name as home_team_name, aw.team_name as away_team_name
        from fct_matches f
        join dim_teams ht on f.home_team_id = ht.team_id
        join dim_teams aw on f.away_team_id = aw.team_id
        where f.competition_code = ? and f.season_id = ?
        order by f.kickoff_utc asc
        """,
        [competition_code, season_id],
    ).df()


def get_current_teams(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Every team with at least one match, home or away, in ANY competition's
    current season. UNION (not UNION ALL) dedupes a team appearing in both
    positions across different matches.
    """
    return con.execute("""
        select team_id, team_name from (
            select f.home_team_id as team_id, t.team_name
            from fct_matches f
            join dim_teams t on f.home_team_id = t.team_id
            where f.season_id = (
                select max(season_id) from dim_seasons s2
                where s2.competition_code = f.competition_code
            )
            union
            select f.away_team_id as team_id, t.team_name
            from fct_matches f
            join dim_teams t on f.away_team_id = t.team_id
            where f.season_id = (
                select max(season_id) from dim_seasons s2
                where s2.competition_code = f.competition_code
            )
        ) combined
        order by team_name
    """).df()


def get_team_competitions(con: duckdb.DuckDBPyConnection, team_id: int) -> pd.DataFrame:
    """Every competition this team has a current-season match in.

    DISTINCT is load-bearing here, unlike get_current_teams -- a team can
    have several matches in the same competition/season, and without it
    this would return one row per match, not one per competition.
    """
    return con.execute(
        """
        select distinct f.competition_code, c.competition_name, f.season_id
        from fct_matches f
        join dim_competitions c on f.competition_code = c.competition_code
        where (f.home_team_id = ? or f.away_team_id = ?)
          and f.season_id = (
              select max(season_id) from dim_seasons s2
              where s2.competition_code = f.competition_code
          )
        order by c.competition_name
        """,
        [team_id, team_id],
    ).df()


def get_team_form(
    con: duckdb.DuckDBPyConnection, team_id: int, competition_code: str
) -> pd.Series | None:
    """mart_team_form has no row at all for a team with zero counted
    results this season/competition -- not a null-valued row. None here
    means exactly that, and the page must show a message, not an empty
    form string.
    """
    df = con.execute(
        """
        select last_5_results, wins, draws, losses, goals_for, goals_against
        from mart_team_form
        where team_id = ? and competition_code = ?
        """,
        [team_id, competition_code],
    ).df()
    if df.empty:
        return None
    return df.iloc[0]


def get_team_position_history(
    con: duckdb.DuckDBPyConnection, team_id: int, competition_code: str, season_id: int
) -> pd.DataFrame:
    """May legitimately be empty -- the reconstruction has nothing to chart
    yet (not started, or entirely in a non-league-table stage). The page
    must handle that with a message, not an empty or broken chart.
    """
    return con.execute(
        """
        select matchday, position
        from mart_standings_over_time
        where team_id = ? and competition_code = ? and season_id = ?
        order by matchday asc
        """,
        [team_id, competition_code, season_id],
    ).df()


def get_match_detail(
    con: duckdb.DuckDBPyConnection, match_id: int
) -> pd.Series | None:
    """One match's full detail: teams, venue (nullable -- a needs_review
    venue has no coordinates), weather (nullable -- no row until ingested,
    or kickoff not yet confirmed). None if match_id doesn't exist at all.
    """
    df = con.execute(
        """
        select f.match_id, f.competition_code, f.season_id, f.matchday, f.stage,
               f.kickoff_utc, f.kickoff_time_confirmed, f.status,
               f.full_time_home, f.full_time_away,
               ht.team_name as home_team_name, aw.team_name as away_team_name,
               v.canonical_venue_name, v.display_name as venue_display_name,
               v.capacity, v.latitude, v.longitude, v.needs_review as venue_needs_review,
               w.temperature_2m, w.precipitation, w.wind_speed_10m,
               w.data_type as weather_data_type
        from fct_matches f
        join dim_teams ht on f.home_team_id = ht.team_id
        join dim_teams aw on f.away_team_id = aw.team_id
        left join dim_venues v on f.venue_key = v.venue_key
        left join fct_match_weather w on f.match_id = w.match_id
        where f.match_id = ?
        """,
        [match_id],
    ).df()
    if df.empty:
        return None
    return df.iloc[0]
