"""Query layer for the Streamlit app: a cached read-only DuckDB connection
and one function per page's data need.

Read-only, always -- this project's DuckDB allows one writer or many
readers, never both (see CLAUDE.md). This app must never hold a write lock.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import duckdb
import pandas as pd
import streamlit as st
from google.cloud import bigquery


def _app_destination() -> str:
    return "bigquery" if os.environ.get("APP_DESTINATION") == "bigquery" else "duckdb"


class CursorLike(Protocol):
    def df(self) -> pd.DataFrame: ...
    def fetchone(self) -> tuple[object, ...] | None: ...


class ConnectionLike(Protocol):
    def execute(
        self, sql: str, params: list[object] | None = None
    ) -> CursorLike: ...


class _BigQueryCursor:
    def __init__(self, job: "bigquery.QueryJob") -> None:
        self._job = job

    def df(self) -> pd.DataFrame:
        return self._job.to_dataframe()

    def fetchone(self) -> tuple[object, ...] | None:
        row = next(iter(self._job.result()), None)
        return tuple(row.values()) if row is not None else None


class BigQueryConnection:
    """Adapts google.cloud.bigquery.Client to the narrow slice of DuckDB's
    connection interface app/queries.py actually uses --
    .execute(sql, params) returning something with .df()/.fetchone(). No
    query function or page needs to know which connection type it was
    given.

    Positional `?` placeholders (DuckDB's DB-API style, used throughout
    this file) are translated to BigQuery's named `@pN` parameters here,
    one adapter, rather than rewriting every query's SQL string.
    """

    def __init__(self, client: "bigquery.Client") -> None:
        self._client = client

    def execute(
        self, sql: str, params: list[object] | None = None
    ) -> _BigQueryCursor:
        job_config = None
        if params:
            query_params = []
            for i, value in enumerate(params):
                name = f"p{i}"
                sql = sql.replace("?", f"@{name}", 1)
                type_ = "STRING" if isinstance(value, str) else "INT64"
                query_params.append(
                    bigquery.ScalarQueryParameter(name, type_, value)
                )
            job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        job = self._client.query(sql, job_config=job_config)
        return _BigQueryCursor(job)


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
def get_connection(db_path: Path = DEFAULT_DB_PATH) -> ConnectionLike:
    """One read-only connection per Streamlit session, not one per rerun."""
    if _app_destination() == "bigquery":
        project = os.environ["GCP_PROJECT"]
        client = bigquery.Client(
            project=project,
            default_query_job_config=bigquery.QueryJobConfig(
                default_dataset=f"{project}.main"
            ),
        )
        return BigQueryConnection(client)

    con = duckdb.connect(str(db_path), read_only=True)
    # Load-bearing, not cosmetic -- same reasoning as transform/profiles.yml's
    # TimeZone: 'UTC' setting. fct_matches.kickoff_utc is TIMESTAMP WITH TIME
    # ZONE; without an explicit session TimeZone, DuckDB converts it to the
    # MACHINE's local timezone whenever it's read out (e.g. via .df()), and
    # nothing downstream would catch that -- app/formatting.py's kickoff
    # formatter would print a wrong wall-clock time with a literal "UTC"
    # suffix, silently. This project is UTC end-to-end (see CLAUDE.md);
    # this is the one connection that hadn't yet been pinned to it.
    #
    # BigQuery needs no equivalent pin: google.cloud.bigquery's
    # to_dataframe() already returns timezone-aware UTC timestamps by
    # default (verified live, 2026-09-10, against this project's real
    # production warehouse), so there is nothing to silently drift.
    con.execute("SET TimeZone='UTC'")
    return con


def get_competitions(con: ConnectionLike) -> pd.DataFrame:
    return con.execute("""
        select competition_code, competition_name
        from dim_competitions
        order by competition_name
    """).df()


def get_current_season_id(
    con: ConnectionLike, competition_code: str
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
    con: ConnectionLike, competition_code: str, season_id: int
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
        select f.position, t.team_name, f.played_games, f.won, f.draw,
               f.lost, f.goals_for, f.goals_against, f.goal_difference, f.points, f.form,
               t.team_id
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
    con: ConnectionLike, competition_code: str, season_id: int
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
        """,  # nosec B608 -- only the hardcoded _MATCH_COLUMNS/_FINISHED_STATUSES
        # constants are interpolated; the real user-supplied values
        # (competition_code, season_id) are bound via ? placeholders below.
        [competition_code, season_id],
    ).df()


def get_upcoming_matches(
    con: ConnectionLike, competition_code: str, season_id: int
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
        """,  # nosec B608 -- only the hardcoded _MATCH_COLUMNS/_UPCOMING_STATUSES
        # constants are interpolated; the real user-supplied values
        # (competition_code, season_id) are bound via ? placeholders below.
        [competition_code, season_id],
    ).df()


def get_matches_for_picker(
    con: ConnectionLike, competition_code: str, season_id: int
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


def get_top_scorers(
    con: ConnectionLike, competition_code: str, season_id: int
) -> pd.DataFrame:
    """fct_scorers already carries player_name/team_name denormalized on
    the fact row (the source API embeds scorer names directly, unlike
    matches/standings, which only carry team_id and need dim_teams) -- no
    join needed here.

    rank is computed with rank(), not row_number() and not dense_rank():
    two players tied on every sort key must share a rank, with the next
    distinct row's rank skipping by the count of tied rows ahead of it
    (1, 2, 2, 4) -- dense_rank() would give 1, 2, 2, 3 instead, silently
    compressing the tie away, and row_number() would split ties
    arbitrarily by whatever order the query happens to return rows in.
    Verified empirically against DuckDB, not assumed from the function
    name.

    May legitimately return an empty DataFrame -- a competition whose
    current season has no counted scorer rows yet is a real state, not an
    error.

    assists/penalties coalesce NULL to 0 -- confirmed via a live
    football-data.org API call (not guessed) that the source JSON sends
    an explicit null when a player has no assists/penalties, not an
    omitted field and not an explicit 0. Rendering that as a blank cell
    reads as "unknown"; it means zero. This also removes every null this
    query could see feeding rank()'s ORDER BY (goals and played_matches
    are never null in the real data), so no NULLS LAST/FIRST handling is
    needed here at all -- a prior fix relied on NULLS LAST inside the
    window's own ORDER BY, which BigQuery's documented window-function
    grammar does not appear to support (only top-level ORDER BY does);
    coalescing removes the need for it entirely rather than leaving an
    unverified, possibly-nonportable clause in place unused.

    The outer ORDER BY breaks ties on player_name for a deterministic
    display order -- DuckDB does not guarantee scan order is stable
    across reruns, and two players sharing a rank would otherwise render
    in an arbitrary order (same class of concern get_standings' own
    ORDER BY comment already flags).
    """
    return con.execute(
        """
        select
            rank() over (
                order by goals desc, coalesce(assists, 0) desc, played_matches asc
            ) as rank,
            player_name, team_name, goals,
            coalesce(assists, 0) as assists,
            played_matches,
            coalesce(penalties, 0) as penalties
        from fct_scorers
        where competition_code = ? and season_id = ?
        order by rank, player_name
        """,
        [competition_code, season_id],
    ).df()


def get_current_teams(con: ConnectionLike) -> pd.DataFrame:
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
            union distinct
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


def get_team_competitions(con: ConnectionLike, team_id: int) -> pd.DataFrame:
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
    con: ConnectionLike, team_id: int, competition_code: str, season_id: int
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
        where team_id = ? and competition_code = ? and season_id = ?
        """,
        [team_id, competition_code, season_id],
    ).df()
    if df.empty:
        return None
    return df.iloc[0]


def get_team_position_history(
    con: ConnectionLike, team_id: int, competition_code: str, season_id: int
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


def get_head_to_head(
    con: ConnectionLike, team_1_id: int, team_2_id: int
) -> pd.Series | None:
    """mart_head_to_head stores one row per unordered pair, keyed
    team_a_id = least(...), team_b_id = greatest(...) (CLAUDE.md's
    pairwise-model convention) -- an ordering the caller's two team ids
    have no relationship to. Looks the row up via least/greatest, then
    remaps team_a_*/team_b_* back onto team_1_*/team_2_* in whichever
    order the caller actually passed them in, so the result always
    reflects "team_1's" record regardless of team_1_id's numeric value
    relative to team_2_id.

    None when the pair has no row at all -- two teams that have never
    played each other is a real state, not an error.
    """
    df = con.execute(
        """
        select team_a_id, team_a_wins, team_b_wins, draws,
               matches_played, team_a_goals, team_b_goals
        from mart_head_to_head
        where team_a_id = least(?, ?) and team_b_id = greatest(?, ?)
        """,
        [team_1_id, team_2_id, team_1_id, team_2_id],
    ).df()
    if df.empty:
        return None
    row = df.iloc[0]
    if team_1_id == row["team_a_id"]:
        team_1_wins, team_2_wins = row["team_a_wins"], row["team_b_wins"]
        team_1_goals, team_2_goals = row["team_a_goals"], row["team_b_goals"]
    else:
        team_1_wins, team_2_wins = row["team_b_wins"], row["team_a_wins"]
        team_1_goals, team_2_goals = row["team_b_goals"], row["team_a_goals"]
    return pd.Series(
        {
            "team_1_wins": team_1_wins,
            "team_2_wins": team_2_wins,
            "draws": row["draws"],
            "matches_played": row["matches_played"],
            "team_1_goals": team_1_goals,
            "team_2_goals": team_2_goals,
        }
    )


def get_head_to_head_matches(
    con: ConnectionLike, team_1_id: int, team_2_id: int
) -> pd.DataFrame:
    """Every FINISHED/AWARDED match between the pair, either team home,
    newest first, no cap. Same status filter mart_head_to_head.sql uses,
    so this list and that aggregate always agree on which matches count
    -- a SCHEDULED fixture between the two showing up here (or an
    AWARDED one missing from it) would make the two panels on the page
    disagree with each other.

    May legitimately be empty -- reachable only when get_head_to_head
    also returns None, since both read the same underlying match set.
    """
    return con.execute(
        f"""
        select f.kickoff_utc, f.kickoff_time_confirmed, c.competition_name,
               ht.team_name as home_team_name, aw.team_name as away_team_name,
               f.full_time_home, f.full_time_away
        from fct_matches f
        join dim_teams ht on f.home_team_id = ht.team_id
        join dim_teams aw on f.away_team_id = aw.team_id
        join dim_competitions c on f.competition_code = c.competition_code
        where f.status in ('{"', '".join(_FINISHED_STATUSES)}')
          and ((f.home_team_id = ? and f.away_team_id = ?)
            or (f.home_team_id = ? and f.away_team_id = ?))
        order by f.kickoff_utc desc
        """,  # nosec B608 -- only the hardcoded _FINISHED_STATUSES constant is
        # interpolated; the real user-supplied values (team_1_id, team_2_id)
        # are bound via ? placeholders below.
        [team_1_id, team_2_id, team_2_id, team_1_id],
    ).df()


def get_cross_league_stats(con: ConnectionLike) -> pd.DataFrame:
    """One row per tracked competition (dim_competitions), always -- a
    competition with no decided matches in its current season (e.g. UEFA
    Champions League before its group stage starts) still appears, with
    null decided_matches/avg_goals_per_match/avg_goal_margin/home_win_rate,
    via LEFT JOIN rather than silently vanishing from the comparison.

    This differs from every other "no data" case in this module
    (get_team_form/get_team_position_history return None/empty) --
    here one query covers every competition at once, so absence is
    expressed per-row instead of for the whole result.
    """
    return con.execute(
        """
        select
            c.competition_name,
            m.decided_matches,
            m.avg_goals_per_match,
            m.avg_goal_margin,
            m.home_win_rate
        from dim_competitions c
        left join mart_cross_league_stats m
          on m.competition_code = c.competition_code
         and m.season_id = (
             select max(season_id) from dim_seasons s
             where s.competition_code = c.competition_code
         )
        order by c.competition_name
        """
    ).df()


def get_competition_seasons(
    con: ConnectionLike, competition_code: str
) -> pd.DataFrame:
    """Every backfilled season for one competition, most recent first --
    the season picker's source. The page derives a human-readable
    "2024/25" label from start_date/end_date; season_id itself is an
    opaque API-assigned integer with no calendar meaning to a reader.
    """
    return con.execute(
        """
        select season_id, start_date, end_date
        from dim_seasons
        where competition_code = ?
        order by season_id desc
        """,
        [competition_code],
    ).df()


def get_reconstructed_final_standings(
    con: ConnectionLike, competition_code: str, season_id: int
) -> pd.DataFrame:
    """A past season's final table, reconstructed from match results via
    mart_standings_over_time -- fct_standings_snapshot has zero rows for
    any past season (the standings endpoint only ever returns a
    competition's CURRENT table; there was never a historical backfill
    for it), so this reconstruction is the only source available for a
    completed season. Same caveat CLAUDE.md already documents for this
    mart: can drift from the real final table on tiebreakers it has no
    way to know about (head-to-head record, disciplinary points) and on
    points deductions.

    group_name is nullable and carried through unchanged -- the old
    Champions League group-stage format (2023/24 in this backfill) has
    real distinct groups, so more than one team can legitimately show
    position = 1 (one per group). Every other season/competition in
    today's backfill has group_name null throughout. The correlated
    subquery takes each (competition, season, group)'s own final
    matchday, matching the mart's own position window (already
    partitioned by group_name) -- not a global max across groups, which
    would silently pick one group's last matchday for every group.

    May legitimately be empty -- a season with no mart_standings_over_time
    rows at all (not reachable for any season in today's backfill, but
    not guaranteed to stay that way) gets a message, not a broken table.
    """
    return con.execute(
        """
        select
            m.group_name,
            m.position,
            t.team_name,
            m.cumulative_points as points,
            m.cumulative_goal_difference as goal_difference,
            m.cumulative_goals_for as goals_for
        from mart_standings_over_time m
        join dim_teams t on m.team_id = t.team_id
        where m.competition_code = ? and m.season_id = ?
          and m.matchday = (
              select max(m2.matchday)
              from mart_standings_over_time m2
              where m2.competition_code = m.competition_code
                and m2.season_id = m.season_id
                and m2.group_name is not distinct from m.group_name
          )
        order by m.group_name, m.position
        """,
        [competition_code, season_id],
    ).df()


def get_streaks(con: ConnectionLike, competition_code: str) -> pd.DataFrame:
    """mart_streaks is grained at (team_id, competition_code) with no
    season_id -- deliberately, not an oversight (see the design doc):
    current_win_streak/current_unbeaten_streak must span a season
    boundary (a real streak doesn't reset when the calendar rolls over),
    and longest_win_streak/longest_unbeaten_streak are meant to be
    all-time records across the whole backfilled window, the same
    "all-time, not season-scoped" choice already made for
    mart_head_to_head. All four stat columns pass through unchanged --
    no recomputation, no filtering to only teams currently on a streak.

    May legitimately be empty -- a competition with no decided matches
    in mart_streaks (not reachable for any competition in today's
    backfill) gets a message, not a broken table.
    """
    return con.execute(
        """
        select
            s.team_id,
            t.team_name,
            s.current_win_streak,
            s.current_unbeaten_streak,
            s.longest_win_streak,
            s.longest_unbeaten_streak
        from mart_streaks s
        join dim_teams t on s.team_id = t.team_id
        where s.competition_code = ?
        """,
        [competition_code],
    ).df()


def get_teams_in_season(
    con: ConnectionLike, competition_code: str, season_id: int
) -> pd.DataFrame:
    """Every team with at least one match, home or away, in this specific
    competition/season -- the same home+away UNION get_current_teams
    already uses, scoped to one (competition, season) pair instead of
    "any competition's current season". Built to filter get_streaks'
    "Current Streaks" panel down to teams actually still in the
    competition -- mart_streaks itself has no notion of "still
    competing", so without this filter a team that left the
    competition years ago (relegated, or eliminated from a prior
    Champions League edition) renders indistinguishably from a
    genuinely active team's current streak.
    """
    return con.execute(
        """
        select team_id from (
            select home_team_id as team_id
            from fct_matches
            where competition_code = ? and season_id = ?
            union distinct
            select away_team_id as team_id
            from fct_matches
            where competition_code = ? and season_id = ?
        ) combined
        """,
        [competition_code, season_id, competition_code, season_id],
    ).df()


def get_match_detail(
    con: ConnectionLike, match_id: int
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
