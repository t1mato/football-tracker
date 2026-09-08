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
    get_current_teams,
    get_match_detail,
    get_matches_for_picker,
    get_recent_matches,
    get_standings,
    get_team_competitions,
    get_team_form,
    get_team_position_history,
    get_top_scorers,
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
    assert list(result.table["team_id"]) == [1, 2]


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


def test_match_detail_handles_a_null_venue_key(tmp_path: Path) -> None:
    """A match whose venue_key is itself null -- no dim_venues row to join
    to at all, distinct from test_match_detail_handles_no_weather_and_
    unresolved_venue above (which joins to a real, resolved-false venue
    row). This is the exact state the final whole-branch review found live
    in the warehouse: 4 Champions League matches (season 2557) with a null
    venue_key. The LEFT JOIN still produces a row, but every dim_venues
    column -- including venue_needs_review -- comes back null, not false.
    """
    db_path = build_match_detail_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_matches values
            (3, 'CL', 2557, null, 'LEAGUE_STAGE', '2026-09-12 14:00:00', true,
             'SCHEDULED', 1, 2, null, null, null)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    detail = get_match_detail(con, 3)

    assert detail is not None
    assert pd.isna(detail["venue_needs_review"])


def test_match_detail_returns_none_for_an_unknown_match_id(tmp_path: Path) -> None:
    con = duckdb.connect(str(build_match_detail_db(tmp_path)), read_only=True)

    assert get_match_detail(con, 999) is None


def build_team_profile_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("""
        create table main.dim_teams (team_id bigint, team_name varchar);
        create table main.dim_competitions (
            competition_code varchar, competition_name varchar
        );
        create table main.dim_seasons (season_id integer, competition_code varchar);
        create table main.fct_matches (
            match_id bigint, competition_code varchar, season_id integer,
            home_team_id bigint, away_team_id bigint
        );
        create table main.mart_team_form (
            team_id bigint, competition_code varchar, season_id integer,
            last_5_results varchar, wins integer, draws integer, losses integer,
            goals_for integer, goals_against integer
        );
        create table main.mart_standings_over_time (
            team_id bigint, competition_code varchar, season_id integer,
            matchday integer, position integer
        )
    """)
    con.close()
    return db_path


def test_current_teams_includes_home_and_away_current_season_appearances(
    tmp_path: Path,
) -> None:
    db_path = build_team_profile_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.dim_teams values
            (1, 'Team A'), (2, 'Team B'), (3, 'Team C'), (4, 'Team D');
        insert into main.dim_seasons values (2501, 'PL'), (2502, 'PL');
        insert into main.fct_matches values
            (1, 'PL', 2502, 1, 2),
            (2, 'PL', 2501, 3, 1),
            (3, 'PL', 2502, 4, 1)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_current_teams(con)

    # Team 1 appears in TWO current-season matches (match 1 as home_team_id,
    # match 3 as away_team_id), but UNION deduplicates it to exactly one row.
    # This verifies the deduplication behavior, not just home/away inclusion.
    assert set(rows["team_id"]) == {1, 2, 4}
    assert 3 not in set(rows["team_id"])
    assert rows[rows["team_id"] == 1]["team_id"].count() == 1  # Team 1 appears exactly once


def test_team_competitions_covers_every_current_competition_for_one_team(
    tmp_path: Path,
) -> None:
    db_path = build_team_profile_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.dim_teams values (1, 'Team A'), (2, 'Team B'), (3, 'Team C');
        insert into main.dim_competitions values
            ('PL', 'Premier League'), ('CL', 'Champions League');
        insert into main.dim_seasons values (2502, 'PL'), (2601, 'CL');
        insert into main.fct_matches values
            (1, 'PL', 2502, 1, 2),
            (2, 'CL', 2601, 1, 3),
            (3, 'PL', 2502, 2, 3),
            (4, 'PL', 2502, 3, 1)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_team_competitions(con, 1)

    assert set(rows["competition_code"]) == {"PL", "CL"}
    # Team 1 appears in TWO PL matches (match 1 as home_team_id, match 4 as
    # away_team_id), but DISTINCT deduplicates it to exactly one PL row.
    # This verifies that DISTINCT is load-bearing.
    assert len(rows) == 2
    pl_rows = rows[rows["competition_code"] == "PL"]
    assert len(pl_rows) == 1


def test_team_form_returns_the_row_when_one_exists(tmp_path: Path) -> None:
    db_path = build_team_profile_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.mart_team_form values
            (1, 'PL', 2502, 'WWDLW', 3, 1, 1, 8, 4)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    form = get_team_form(con, 1, "PL", 2502)

    assert form is not None
    assert form["last_5_results"] == "WWDLW"
    assert form["wins"] == 3


def test_team_form_returns_none_when_the_team_has_no_results_yet(tmp_path: Path) -> None:
    """A team with zero counted results this season/competition has no row
    in mart_team_form at all -- not a null-valued one. This is the real
    case this function exists to handle, not an edge case to skip.
    """
    con = duckdb.connect(str(build_team_profile_db(tmp_path)), read_only=True)

    form = get_team_form(con, 1, "CL", 2601)

    assert form is None


def test_team_form_does_not_leak_a_different_seasons_row(tmp_path: Path) -> None:
    """mart_team_form is scoped to (team_id, competition_code, season_id) --
    a row from a prior season/competition edition must never be returned
    for a different season_id, even for the same team+competition.
    """
    db_path = build_team_profile_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.mart_team_form values
            (1, 'CL', 1630, 'WDDWL', 2, 2, 1, 7, 6)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    form = get_team_form(con, 1, "CL", 2557)

    assert form is None


def test_position_history_is_ordered_by_matchday(tmp_path: Path) -> None:
    db_path = build_team_profile_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.mart_standings_over_time values
            (1, 'PL', 2502, 3, 2),
            (1, 'PL', 2502, 1, 5),
            (1, 'PL', 2502, 2, 4)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_team_position_history(con, 1, "PL", 2502)

    assert list(rows["matchday"]) == [1, 2, 3]
    assert list(rows["position"]) == [5, 4, 2]


def test_position_history_is_empty_when_the_reconstruction_has_nothing_yet(
    tmp_path: Path,
) -> None:
    """A team/competition/season with nothing in mart_standings_over_time
    yet (not started, or entirely in a non-league-table stage) is a real,
    valid state -- an empty DataFrame, not an error. The page must show a
    message here, not an empty or broken chart.
    """
    con = duckdb.connect(str(build_team_profile_db(tmp_path)), read_only=True)

    rows = get_team_position_history(con, 1, "CL", 2601)

    assert rows.empty


def build_scorers_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("""
        create table main.fct_scorers (
            competition_code varchar, season_id bigint, player_id bigint,
            player_name varchar, team_id bigint, team_name varchar,
            played_matches bigint, goals bigint, assists bigint, penalties bigint
        )
    """)
    con.close()
    return db_path


def test_top_scorers_sorts_by_goals_then_assists_then_fewer_matches(
    tmp_path: Path,
) -> None:
    db_path = build_scorers_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_scorers values
            ('PL', 2502, 1, 'Player A', 10, 'Team X', 10, 8, 2, 0),
            ('PL', 2502, 2, 'Player B', 11, 'Team Y', 12, 8, 3, 0),
            ('PL', 2502, 3, 'Player C', 12, 'Team Z', 15, 5, 1, 0)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_top_scorers(con, "PL", 2502)

    # Player B and Player A are tied on goals (8); assists breaks the tie
    # (3 beats 2), so B ranks above A. Player C trails both on goals alone.
    assert list(rows["player_name"]) == ["Player B", "Player A", "Player C"]
    assert list(rows["rank"]) == [1, 2, 3]


def test_top_scorers_breaks_a_goals_and_assists_tie_by_fewer_matches_played(
    tmp_path: Path,
) -> None:
    db_path = build_scorers_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_scorers values
            ('PL', 2502, 1, 'Player A', 10, 'Team X', 20, 8, 2, 0),
            ('PL', 2502, 2, 'Player B', 11, 'Team Y', 14, 8, 2, 0)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_top_scorers(con, "PL", 2502)

    # Tied on goals (8) and assists (2) -- Player B needed fewer matches
    # (14 vs 20) to get there, so B ranks above A.
    assert list(rows["player_name"]) == ["Player B", "Player A"]
    assert list(rows["rank"]) == [1, 2]


def test_top_scorers_gives_fully_tied_players_the_same_rank(tmp_path: Path) -> None:
    """rank(), not row_number() and not dense_rank() -- two players equal
    on every sort key must share a rank, and the next distinct row's rank
    must skip accordingly (1, 2, 2, 4), not run consecutively (1, 2, 2, 3,
    which dense_rank() would give instead). This is the whole reason
    rank() was chosen over the other two window functions in the spec,
    and a test that only checks "sorted correctly" would pass even if
    this were silently swapped to either one.
    """
    db_path = build_scorers_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_scorers values
            ('PL', 2502, 1, 'Player A', 10, 'Team X', 10, 10, 5, 0),
            ('PL', 2502, 2, 'Player B', 11, 'Team Y', 10, 8, 3, 0),
            ('PL', 2502, 3, 'Player C', 12, 'Team Z', 10, 8, 3, 0),
            ('PL', 2502, 4, 'Player D', 13, 'Team W', 10, 5, 1, 0)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_top_scorers(con, "PL", 2502)

    # A is alone at the top (rank 1). B and C are fully tied (8 goals, 3
    # assists, 10 matches each) and must both be rank 2. D is the next
    # distinct entry and must be rank 4, not rank 3 -- proving rank()'s
    # gap-preserving behavior (two players placed ahead of D), not just
    # "B and C are adjacent."
    ranks_by_name = dict(zip(rows["player_name"], rows["rank"], strict=True))
    assert ranks_by_name["Player A"] == 1
    assert ranks_by_name["Player B"] == 2
    assert ranks_by_name["Player C"] == 2
    assert ranks_by_name["Player D"] == 4


def test_top_scorers_is_empty_when_the_competition_has_no_scorers_yet(
    tmp_path: Path,
) -> None:
    """Zero fct_scorers rows for this competition/season is a real, valid
    state (season just started, nobody has scored) -- an empty DataFrame,
    not an error. The page must show a message here, not an empty or
    broken table.
    """
    con = duckdb.connect(str(build_scorers_db(tmp_path)), read_only=True)

    rows = get_top_scorers(con, "PL", 2502)

    assert rows.empty


def test_top_scorers_sorts_null_assists_last_not_first(tmp_path: Path) -> None:
    """assists is frequently NULL in the real data (not every scorer has a
    tracked assist count) -- NULLS LAST must be explicit, not left to
    whichever warehouse's default happens to apply, since DuckDB and
    BigQuery are not guaranteed to agree on NULL ordering under DESC.
    """
    db_path = build_scorers_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_scorers values
            ('PL', 2502, 1, 'Player A', 10, 'Team X', 10, 8, null, 0),
            ('PL', 2502, 2, 'Player B', 11, 'Team Y', 10, 8, 1, 0)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_top_scorers(con, "PL", 2502)

    # Tied on goals (8). Player B has 1 assist, Player A has NULL assists.
    # NULLS LAST means the null-assists player sorts after the real value,
    # not before it (which is what NULLS FIRST -- a real possible default
    # on some warehouses -- would do instead).
    assert list(rows["player_name"]) == ["Player B", "Player A"]
