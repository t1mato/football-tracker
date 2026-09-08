"""Tests for app/queries.py's logic-bearing functions.

Most of queries.py is a straight SQL passthrough with nothing to unit test
beyond "does it run" -- that's covered by manually running the app (see
docs/plans/2026-09-07-competition-hub.md Task 7). get_standings() is the
one function with real branching logic (is there a current league table,
or not), so it's the one function with a real test here, against a small
hand-built DuckDB fixture -- same pattern as tests/test_weather_source.py's
build_db().
"""

from pathlib import Path

import duckdb
import pandas as pd

from app.queries import (
    get_competitions,
    get_current_season_id,
    get_match_detail,
    get_matches_for_picker,
    get_recent_matches,
    get_standings,
    get_upcoming_matches,
)


def build_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("""
        create table main.dim_competitions (
            competition_code varchar, competition_name varchar
        )
    """)
    con.execute("""
        insert into main.dim_competitions values
            ('PL', 'Premier League'), ('CL', 'UEFA Champions League')
    """)
    con.close()
    return db_path


def test_get_competitions_returns_code_and_name(tmp_path: Path) -> None:
    con = duckdb.connect(str(build_db(tmp_path)), read_only=True)

    rows = get_competitions(con)

    assert set(rows["competition_code"]) == {"PL", "CL"}
    assert set(rows["competition_name"]) == {"Premier League", "UEFA Champions League"}


def test_get_current_season_id_is_the_max_per_competition(tmp_path: Path) -> None:
    db_path = build_db(tmp_path)
    duckdb.connect(str(db_path)).execute("""
        create table main.dim_seasons (season_id integer, competition_code varchar);
        insert into main.dim_seasons values (2501, 'PL'), (2502, 'PL'), (2601, 'CL')
    """)
    con = duckdb.connect(str(db_path), read_only=True)

    assert get_current_season_id(con, "PL") == 2502
    assert get_current_season_id(con, "CL") == 2601


def build_standings_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("""
        create table main.fct_standings_snapshot (
            competition_code varchar, season_id integer, team_id bigint,
            snapshot_date date, stage varchar, table_type varchar,
            position integer, played_games integer, won integer, draw integer,
            lost integer, points integer, goals_for integer, goals_against integer,
            goal_difference integer, form varchar
        );
        create table main.dim_teams (team_id bigint, team_name varchar)
    """)
    con.close()
    return db_path


def test_a_normal_league_phase_returns_the_table_ordered_by_position(tmp_path: Path) -> None:
    db_path = build_standings_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.dim_teams values (1, 'Team A'), (2, 'Team B');
        insert into main.fct_standings_snapshot values
            ('PL', 2502, 2, '2026-09-07', 'REGULAR_SEASON', 'TOTAL', 2, 3, 2,0,1, 6,5,3,2, 'WWL'),
            ('PL', 2502, 1, '2026-09-07', 'REGULAR_SEASON', 'TOTAL', 1, 3, 3,0,0, 9,7,1,6, 'WWW')
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    result = get_standings(con, "PL", 2502)

    assert result.message is None
    assert result.table is not None
    assert list(result.table["team_name"]) == ["Team A", "Team B"]
    assert list(result.table["position"]) == [1, 2]


def test_only_the_latest_snapshot_date_is_returned(tmp_path: Path) -> None:
    """get_standings' most load-bearing behavior after the stage branch:
    show the CURRENT table only. A second, earlier snapshot_date with
    different positions must not leak into the result -- this would still
    pass with the snapshot_date filter deleted from the table query if this
    fixture only had one snapshot_date (as the "normal league phase" test
    above does), so this test exists specifically to catch that regression.
    """
    db_path = build_standings_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.dim_teams values (1, 'Team A'), (2, 'Team B');
        insert into main.fct_standings_snapshot values
            ('PL', 2502, 1, '2026-08-31', 'REGULAR_SEASON', 'TOTAL', 2, 2, 1,0,1, 3,3,4,-1, 'WL'),
            ('PL', 2502, 2, '2026-08-31', 'REGULAR_SEASON', 'TOTAL', 1, 2, 2,0,0, 6,4,1,3, 'WW'),
            ('PL', 2502, 2, '2026-09-07', 'REGULAR_SEASON', 'TOTAL', 2, 3, 2,0,1, 6,5,3,2, 'WWL'),
            ('PL', 2502, 1, '2026-09-07', 'REGULAR_SEASON', 'TOTAL', 1, 3, 3,0,0, 9,7,1,6, 'WWW')
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    result = get_standings(con, "PL", 2502)

    assert result.table is not None
    assert len(result.table) == 2
    assert list(result.table["team_name"]) == ["Team A", "Team B"]
    assert list(result.table["position"]) == [1, 2]
    assert list(result.table["points"]) == [9, 6]


def test_no_rows_at_all_returns_a_message_not_an_empty_table(tmp_path: Path) -> None:
    con = duckdb.connect(str(build_standings_db(tmp_path)), read_only=True)

    result = get_standings(con, "CL", 2601)

    assert result.table is None
    assert result.message is not None
    assert "no standings" in result.message.lower()


def test_a_knockout_phase_snapshot_returns_the_knockout_message(tmp_path: Path) -> None:
    """The real case this project cannot currently exercise live (see the
    plan's "Verified facts" section) -- CL's current data is all
    LEAGUE_STAGE today. Constructed here so the branch has real coverage.
    """
    db_path = build_standings_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.dim_teams values (1, 'Team A');
        insert into main.fct_standings_snapshot values
            ('CL', 2601, 1, '2027-03-01', 'QUARTER_FINALS', 'TOTAL',
             null, null, null,null,null, null,null,null,null, null)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    result = get_standings(con, "CL", 2601)

    assert result.table is None
    assert result.message is not None
    assert "knockout" in result.message.lower()


def build_matches_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("""
        create table main.fct_matches (
            match_id bigint, competition_code varchar, season_id integer,
            kickoff_utc timestamp, kickoff_time_confirmed boolean, status varchar,
            home_team_id bigint, away_team_id bigint,
            full_time_home integer, full_time_away integer
        );
        create table main.dim_teams (team_id bigint, team_name varchar);
        insert into main.dim_teams values (1, 'Team A'), (2, 'Team B')
    """)
    con.close()
    return db_path


def test_recent_matches_are_finished_or_awarded_newest_first(tmp_path: Path) -> None:
    db_path = build_matches_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_matches values
            (1, 'PL', 2502, '2026-09-01 15:00:00', true, 'FINISHED', 1, 2, 2, 1),
            (2, 'PL', 2502, '2026-09-08 15:00:00', true, 'FINISHED', 2, 1, 0, 0),
            (3, 'PL', 2502, '2026-09-15 15:00:00', true, 'SCHEDULED', 1, 2, null, null)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_recent_matches(con, "PL", 2502)

    assert list(rows["match_id"]) == [2, 1]


def test_upcoming_matches_are_scheduled_or_timed_soonest_first(tmp_path: Path) -> None:
    db_path = build_matches_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_matches values
            (3, 'PL', 2502, '2026-09-22 15:00:00', true, 'TIMED', 1, 2, null, null),
            (4, 'PL', 2502, '2026-09-15 00:00:00', false, 'SCHEDULED', 2, 1, null, null),
            (5, 'PL', 2502, '2026-09-01 15:00:00', true, 'FINISHED', 1, 2, 1, 1)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_upcoming_matches(con, "PL", 2502)

    assert list(rows["match_id"]) == [4, 3]
    assert rows.iloc[0]["kickoff_time_confirmed"] == False  # noqa: E712


def test_matches_for_picker_are_ordered_by_kickoff_ascending(tmp_path: Path) -> None:
    db_path = build_matches_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_matches values
            (1, 'PL', 2502, '2026-09-08 15:00:00', true, 'FINISHED', 1, 2, 2, 1),
            (2, 'PL', 2502, '2026-09-01 15:00:00', true, 'FINISHED', 2, 1, 0, 0)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_matches_for_picker(con, "PL", 2502)

    assert list(rows["match_id"]) == [2, 1]
    assert list(rows["home_team_name"]) == ["Team B", "Team A"]


def build_match_detail_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("""
        create table main.fct_matches (
            match_id bigint, competition_code varchar, season_id integer,
            matchday integer, stage varchar,
            kickoff_utc timestamp, kickoff_time_confirmed boolean, status varchar,
            home_team_id bigint, away_team_id bigint, venue_key varchar,
            full_time_home integer, full_time_away integer
        );
        create table main.dim_teams (team_id bigint, team_name varchar);
        create table main.dim_venues (
            venue_key varchar, canonical_venue_name varchar, display_name varchar,
            capacity integer, latitude double, longitude double, needs_review boolean
        );
        create table main.fct_match_weather (
            match_id bigint, temperature_2m double, precipitation double,
            wind_speed_10m double, data_type varchar
        );
        insert into main.dim_teams values (1, 'Team A'), (2, 'Team B')
    """)
    con.close()
    return db_path


def test_match_detail_joins_teams_venue_and_weather(tmp_path: Path) -> None:
    db_path = build_match_detail_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_matches values
            (1, 'PL', 2502, 3, 'REGULAR_SEASON', '2026-09-12 14:00:00', true,
             'FINISHED', 1, 2, 'v1', 2, 1);
        insert into main.dim_venues values
            ('v1', 'Anfield', 'Anfield, Liverpool', 54074, 53.4308, -2.9608, false);
        insert into main.fct_match_weather values
            (1, 18.5, 0.0, 12.0, 'actual')
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    detail = get_match_detail(con, 1)

    assert detail is not None
    assert detail["home_team_name"] == "Team A"
    assert detail["away_team_name"] == "Team B"
    assert detail["canonical_venue_name"] == "Anfield"
    assert detail["capacity"] == 54074
    assert detail["temperature_2m"] == 18.5
    assert detail["weather_data_type"] == "actual"


def test_match_detail_handles_no_weather_and_unresolved_venue(tmp_path: Path) -> None:
    """No fct_match_weather row, and a needs_review venue with null coordinates
    -- both real, both must produce nulls, not an error.
    """
    db_path = build_match_detail_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_matches values
            (2, 'PL', 2502, 4, 'REGULAR_SEASON', '2026-09-19 15:00:00', true,
             'SCHEDULED', 1, 2, 'v2', null, null);
        insert into main.dim_venues values
            ('v2', 'Griffin Park', 'Griffin Park (demolished)', null, null, null, true)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    detail = get_match_detail(con, 2)

    assert detail is not None
    assert detail["venue_needs_review"] == True  # noqa: E712
    assert pd.isna(detail["latitude"])
    assert pd.isna(detail["weather_data_type"])


def test_match_detail_returns_none_for_an_unknown_match_id(tmp_path: Path) -> None:
    con = duckdb.connect(str(build_match_detail_db(tmp_path)), read_only=True)

    assert get_match_detail(con, 999) is None
