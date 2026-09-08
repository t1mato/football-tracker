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
    get_competition_seasons,
    get_competitions,
    get_cross_league_stats,
    get_current_season_id,
    get_current_teams,
    get_head_to_head,
    get_head_to_head_matches,
    get_match_detail,
    get_matches_for_picker,
    get_recent_matches,
    get_reconstructed_final_standings,
    get_standings,
    get_streaks,
    get_team_competitions,
    get_team_form,
    get_team_position_history,
    get_teams_in_season,
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


def test_top_scorers_treats_null_assists_as_zero(tmp_path: Path) -> None:
    """assists is frequently NULL in the real data -- confirmed via a live
    football-data.org API call that NULL is the API's own encoding of
    zero assists, not "unknown" or "not tracked". coalesce(assists, 0)
    means a NULL-assists player ranks (and displays) exactly as a
    zero-assists player would, not as an unranked/blank outlier.
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

    # Tied on goals (8). Player B has 1 assist, Player A has NULL assists
    # -- coalesced to 0, so B (1 > 0) ranks above A, same relative order
    # NULLS LAST used to produce, but now via an explicit, portable value
    # rather than an unverified cross-database NULL-ordering default.
    assert list(rows["player_name"]) == ["Player B", "Player A"]
    a_row = rows[rows["player_name"] == "Player A"].iloc[0]
    assert a_row["assists"] == 0
    assert pd.notna(a_row["assists"])


def test_top_scorers_does_not_leak_a_different_season_or_competition(
    tmp_path: Path,
) -> None:
    """rank() is computed over the filtered set, so a broken
    competition_code/season_id scope doesn't just add extra rows -- it
    silently corrupts every rank value with cross-season/cross-competition
    data. Deleting the WHERE clause (or just its season_id half) would
    make every OTHER get_top_scorers test in this file still pass, since
    they all insert rows for only one (competition_code, season_id) pair
    -- this test exists specifically to catch that regression.
    """
    db_path = build_scorers_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_scorers values
            ('PL', 2502, 1, 'Player A', 10, 'Team X', 10, 8, 2, 0),
            ('PL', 2403, 2, 'Player B', 11, 'Team Y', 10, 20, 5, 0),
            ('SA', 2502, 3, 'Player C', 12, 'Team Z', 10, 15, 3, 0)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_top_scorers(con, "PL", 2502)

    # Player B (a different PL season) and Player C (a different
    # competition's same season_id) must both be excluded -- if either
    # leaked in, Player A (8 goals) would not be the lone, rank-1 row.
    assert list(rows["player_name"]) == ["Player A"]
    assert list(rows["rank"]) == [1]


def test_top_scorers_returns_the_expected_columns(tmp_path: Path) -> None:
    db_path = build_scorers_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_scorers values
            ('PL', 2502, 1, 'Player A', 10, 'Team X', 10, 8, 2, 0)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_top_scorers(con, "PL", 2502)

    assert list(rows.columns) == [
        "rank", "player_name", "team_name", "goals",
        "assists", "played_matches", "penalties",
    ]


def build_cross_league_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("""
        create table main.dim_competitions (
            competition_code varchar, competition_name varchar
        );
        create table main.dim_seasons (
            competition_code varchar, season_id bigint
        );
        create table main.mart_cross_league_stats (
            competition_code varchar, season_id bigint, decided_matches bigint,
            avg_goals_per_match double, avg_goal_margin double, home_win_rate double
        );
        insert into main.dim_competitions values
            ('PL', 'Premier League'), ('CL', 'UEFA Champions League');
        insert into main.dim_seasons values
            ('PL', 2401), ('PL', 2502), ('CL', 2350), ('CL', 2454)
    """)
    con.close()
    return db_path


def test_cross_league_stats_returns_real_numbers_for_a_competition_with_data(
    tmp_path: Path,
) -> None:
    db_path = build_cross_league_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.mart_cross_league_stats values
            ('PL', 2502, 30, 2.5, 1.2, 0.4)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_cross_league_stats(con)

    pl_row = rows[rows["competition_name"] == "Premier League"].iloc[0]
    assert pl_row["decided_matches"] == 30
    assert pl_row["avg_goals_per_match"] == 2.5
    assert pl_row["avg_goal_margin"] == 1.2
    assert pl_row["home_win_rate"] == 0.4


def test_cross_league_stats_includes_a_competition_with_no_current_season_row(
    tmp_path: Path,
) -> None:
    """UEFA Champions League's current season (2454, the max season_id for
    CL) has no mart_cross_league_stats row at all -- zero decided matches
    means the mart's group by never produces a row. This must still
    appear in the result, with null stats, not be silently dropped by an
    inner join.
    """
    db_path = build_cross_league_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.mart_cross_league_stats values
            ('PL', 2502, 30, 2.5, 1.2, 0.4)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_cross_league_stats(con)

    assert "UEFA Champions League" in list(rows["competition_name"])
    cl_row = rows[rows["competition_name"] == "UEFA Champions League"].iloc[0]
    assert pd.isna(cl_row["decided_matches"])
    assert pd.isna(cl_row["avg_goals_per_match"])
    assert pd.isna(cl_row["home_win_rate"])


def test_cross_league_stats_does_not_leak_a_prior_seasons_row(tmp_path: Path) -> None:
    """PL's current season is 2502 (the max season_id). A mart row that
    exists only for PL's OLDER season (2401) must not be picked up as if
    it were the current season's stats -- same class of leak
    get_team_form is already tested against.
    """
    db_path = build_cross_league_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.mart_cross_league_stats values
            ('PL', 2401, 38, 3.0, 1.5, 0.5)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_cross_league_stats(con)

    pl_row = rows[rows["competition_name"] == "Premier League"].iloc[0]
    assert pd.isna(pl_row["decided_matches"])


def test_cross_league_stats_has_exactly_one_row_per_competition(tmp_path: Path) -> None:
    con = duckdb.connect(str(build_cross_league_db(tmp_path)), read_only=True)

    rows = get_cross_league_stats(con)

    assert len(rows) == 2
    assert set(rows["competition_name"]) == {"Premier League", "UEFA Champions League"}


def test_cross_league_stats_returns_the_expected_columns(tmp_path: Path) -> None:
    con = duckdb.connect(str(build_cross_league_db(tmp_path)), read_only=True)

    rows = get_cross_league_stats(con)

    assert list(rows.columns) == [
        "competition_name", "decided_matches", "avg_goals_per_match",
        "avg_goal_margin", "home_win_rate",
    ]


def build_head_to_head_db(tmp_path: Path) -> Path:
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
        create table main.dim_competitions (
            competition_code varchar, competition_name varchar
        );
        create table main.mart_head_to_head (
            team_a_id bigint, team_b_id bigint, matches_played bigint,
            team_a_wins bigint, team_b_wins bigint, draws bigint,
            team_a_goals bigint, team_b_goals bigint
        );
        insert into main.dim_teams values (1, 'Team A'), (2, 'Team B'), (3, 'Team C');
        insert into main.dim_competitions values
            ('PL', 'Premier League'), ('FAC', 'FA Cup')
    """)
    con.close()
    return db_path


def test_head_to_head_remaps_the_aggregate_regardless_of_argument_order(
    tmp_path: Path,
) -> None:
    """mart_head_to_head keys team_a_id = least(1, 2) = 1, team_b_id = 2 --
    an ordering the page's two selectboxes have no relationship to. This
    proves get_head_to_head(con, 1, 2) and get_head_to_head(con, 2, 1)
    describe the same real-world record, just with team_1_*/team_2_*
    swapped, not two different answers.
    """
    db_path = build_head_to_head_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.mart_head_to_head values (1, 2, 5, 3, 1, 1, 9, 4)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    forward = get_head_to_head(con, 1, 2)
    backward = get_head_to_head(con, 2, 1)

    assert forward is not None
    assert backward is not None
    assert (forward["team_1_wins"], forward["team_2_wins"]) == (3, 1)
    assert (forward["team_1_goals"], forward["team_2_goals"]) == (9, 4)
    assert (backward["team_1_wins"], backward["team_2_wins"]) == (1, 3)
    assert (backward["team_1_goals"], backward["team_2_goals"]) == (4, 9)
    assert forward["draws"] == backward["draws"] == 1
    assert forward["matches_played"] == backward["matches_played"] == 5


def test_head_to_head_returns_none_when_the_pair_never_met(tmp_path: Path) -> None:
    con = duckdb.connect(str(build_head_to_head_db(tmp_path)), read_only=True)

    assert get_head_to_head(con, 1, 3) is None


def test_head_to_head_matches_finds_meetings_regardless_of_home_away(
    tmp_path: Path,
) -> None:
    db_path = build_head_to_head_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_matches values
            (1, 'PL', 2401, '2024-09-01 15:00:00', true, 'FINISHED', 1, 2, 2, 1),
            (2, 'FAC', 2501, '2025-03-01 15:00:00', true, 'FINISHED', 2, 1, 0, 3)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_head_to_head_matches(con, 1, 2)

    # Newest first (match 2 before match 1), and found regardless of which
    # team was recorded as home in a given fixture.
    assert list(rows["home_team_name"]) == ["Team B", "Team A"]
    assert list(rows["competition_name"]) == ["FA Cup", "Premier League"]


def test_head_to_head_matches_excludes_unfinished_fixtures(tmp_path: Path) -> None:
    db_path = build_head_to_head_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_matches values
            (1, 'PL', 2401, '2024-09-01 15:00:00', true, 'FINISHED', 1, 2, 2, 1),
            (2, 'PL', 2502, '2026-09-20 15:00:00', true, 'SCHEDULED', 1, 2, null, null)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_head_to_head_matches(con, 1, 2)

    assert len(rows) == 1
    assert rows.iloc[0]["full_time_home"] == 2


def test_head_to_head_matches_is_empty_when_the_pair_never_met(
    tmp_path: Path,
) -> None:
    con = duckdb.connect(str(build_head_to_head_db(tmp_path)), read_only=True)

    rows = get_head_to_head_matches(con, 1, 3)

    assert rows.empty


def build_season_archive_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("""
        create table main.dim_seasons (
            season_id bigint, competition_code varchar, start_date date, end_date date
        );
        create table main.dim_teams (team_id bigint, team_name varchar);
        create table main.mart_standings_over_time (
            team_id bigint, competition_code varchar, season_id bigint, group_name varchar,
            matchday bigint, cumulative_points bigint, cumulative_goal_difference bigint,
            cumulative_goals_for bigint, position bigint
        );
        insert into main.dim_teams values
            (1, 'Team A'), (2, 'Team B'), (3, 'Team C'), (4, 'Team D');
        insert into main.dim_seasons values
            (2403, 'PL', '2025-08-15', '2026-05-24'),
            (2502, 'PL', '2026-08-21', '2027-05-30'),
            (1630, 'CL', '2023-09-19', '2024-06-01')
    """)
    con.close()
    return db_path


def test_competition_seasons_returns_only_the_requested_competition_ordered_desc(
    tmp_path: Path,
) -> None:
    con = duckdb.connect(str(build_season_archive_db(tmp_path)), read_only=True)

    rows = get_competition_seasons(con, "PL")

    assert list(rows["season_id"]) == [2502, 2403]


def test_reconstructed_standings_returns_only_the_final_matchday(tmp_path: Path) -> None:
    db_path = build_season_archive_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.mart_standings_over_time values
            (1, 'PL', 2403, null, 1, 3, 2, 3, 1),
            (2, 'PL', 2403, null, 1, 0, -2, 1, 2),
            (1, 'PL', 2403, null, 2, 6, 4, 5, 1),
            (2, 'PL', 2403, null, 2, 3, -1, 3, 2)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_reconstructed_final_standings(con, "PL", 2403)

    # Only matchday 2's rows (2), not all 4 across both matchdays.
    assert len(rows) == 2
    assert set(rows["points"]) == {6, 3}


def test_reconstructed_standings_passes_through_the_marts_own_position(
    tmp_path: Path,
) -> None:
    db_path = build_season_archive_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.mart_standings_over_time values
            (1, 'PL', 2403, null, 1, 5, 0, 5, 1),
            (2, 'PL', 2403, null, 1, 5, 0, 5, 1)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_reconstructed_final_standings(con, "PL", 2403)

    # Team A and Team B are tied on every stat this query selects (points,
    # goal_difference, goals_for). mart_standings_over_time computes
    # position with rank(), so tied teams genuinely share a position --
    # both 1, not split into 1 and 2. This proves the query passes that
    # value through as-is rather than recomputing its own tie-break (e.g.
    # via row_number(), which would arbitrarily split the tie).
    positions = dict(zip(rows["team_name"], rows["position"], strict=True))
    assert positions["Team A"] == 1
    assert positions["Team B"] == 1


def test_reconstructed_standings_keeps_each_groups_own_position_and_final_matchday(
    tmp_path: Path,
) -> None:
    db_path = build_season_archive_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.mart_standings_over_time values
            (1, 'CL', 1630, 'GROUP_A', 1, 3, 1, 4, 1),
            (2, 'CL', 1630, 'GROUP_A', 1, 0, -1, 3, 2),
            (1, 'CL', 1630, 'GROUP_A', 2, 6, 2, 7, 1),
            (2, 'CL', 1630, 'GROUP_A', 2, 3, 0, 5, 2),
            (3, 'CL', 1630, 'GROUP_B', 1, 4, 3, 5, 1),
            (4, 'CL', 1630, 'GROUP_B', 1, 1, -3, 2, 2),
            (3, 'CL', 1630, 'GROUP_B', 2, 4, 3, 5, 1),
            (4, 'CL', 1630, 'GROUP_B', 2, 4, 1, 6, 2),
            (3, 'CL', 1630, 'GROUP_B', 3, 7, 4, 8, 1),
            (4, 'CL', 1630, 'GROUP_B', 3, 4, 2, 7, 2)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_reconstructed_final_standings(con, "CL", 1630)

    # GROUP_A has final matchday 2; GROUP_B has final matchday 3. Each group's
    # own final matchday must be used independently -- not a single global max
    # that could pick one group's last matchday for every group. Verify:
    # (1) exactly 4 rows (2 from GROUP_A's matchday 2, 2 from GROUP_B's matchday 3)
    # (2) GROUP_A rows are at matchday 2 (not the earlier matchday 1)
    # (3) GROUP_B rows are at matchday 3 (not the earlier matchdays 1 or 2)
    # A buggy global-max implementation would drop GROUP_A entirely (no matchday-3
    # rows) or include stale GROUP_A data, failing either the length check or
    # the specific position/matchday assertions below.
    assert len(rows) == 4, f"Expected 4 rows, got {len(rows)}"

    group_a_rows = rows[rows["group_name"] == "GROUP_A"]
    group_b_rows = rows[rows["group_name"] == "GROUP_B"]

    assert len(group_a_rows) == 2, f"Expected 2 GROUP_A rows, got {len(group_a_rows)}"
    assert len(group_b_rows) == 2, f"Expected 2 GROUP_B rows, got {len(group_b_rows)}"

    # GROUP_A's matchday-2 position values: position 1 has 6 points, position 2 has 3 points
    assert set(group_a_rows["points"]) == {6, 3}, \
        f"GROUP_A should have points {{6, 3}} from matchday 2, got {set(group_a_rows['points'])}"
    assert set(group_a_rows.loc[group_a_rows["position"] == 1, "team_name"]) == {"Team A"}
    assert set(group_a_rows.loc[group_a_rows["position"] == 2, "team_name"]) == {"Team B"}

    # GROUP_B's matchday-3 position values: position 1 has 7 points, position 2 has 4 points
    assert set(group_b_rows["points"]) == {7, 4}, \
        f"GROUP_B should have points {{7, 4}} from matchday 3, got {set(group_b_rows['points'])}"
    assert set(group_b_rows.loc[group_b_rows["position"] == 1, "team_name"]) == {"Team C"}
    assert set(group_b_rows.loc[group_b_rows["position"] == 2, "team_name"]) == {"Team D"}


def test_reconstructed_standings_is_empty_when_the_season_has_no_data(
    tmp_path: Path,
) -> None:
    con = duckdb.connect(str(build_season_archive_db(tmp_path)), read_only=True)

    rows = get_reconstructed_final_standings(con, "PL", 2403)

    assert rows.empty


def build_streaks_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("""
        create table main.dim_teams (team_id bigint, team_name varchar);
        create table main.mart_streaks (
            team_id bigint, competition_code varchar,
            current_win_streak bigint, current_unbeaten_streak bigint,
            longest_win_streak bigint, longest_unbeaten_streak bigint
        );
        insert into main.dim_teams values (1, 'Team A'), (2, 'Team B'), (3, 'Team C')
    """)
    con.close()
    return db_path


def test_streaks_returns_only_the_requested_competition(tmp_path: Path) -> None:
    db_path = build_streaks_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.mart_streaks values
            (1, 'PL', 3, 5, 8, 10),
            (2, 'CL', 1, 1, 4, 4)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_streaks(con, "PL")

    assert list(rows["team_name"]) == ["Team A"]


def test_streaks_passes_through_all_four_stats_unchanged(tmp_path: Path) -> None:
    db_path = build_streaks_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.mart_streaks values
            (1, 'PL', 3, 5, 8, 10)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_streaks(con, "PL")

    row = rows.iloc[0]
    assert row["current_win_streak"] == 3
    assert row["current_unbeaten_streak"] == 5
    assert row["longest_win_streak"] == 8
    assert row["longest_unbeaten_streak"] == 10


def test_streaks_is_empty_when_the_competition_has_no_data(tmp_path: Path) -> None:
    con = duckdb.connect(str(build_streaks_db(tmp_path)), read_only=True)

    rows = get_streaks(con, "PL")

    assert rows.empty


def test_teams_in_season_includes_home_and_away_appearances(tmp_path: Path) -> None:
    """The same home+away UNION get_current_teams already uses, but scoped
    to one (competition, season) pair. Team 1 appears only as home_team_id,
    Team 2 only as away_team_id -- both sides of the UNION must be covered,
    not just one.
    """
    db_path = build_matches_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_matches values
            (1, 'PL', 2502, '2026-09-01 15:00:00', true, 'FINISHED', 1, 2, 2, 1)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_teams_in_season(con, "PL", 2502)

    assert set(rows["team_id"]) == {1, 2}


def test_teams_in_season_excludes_a_different_season_of_the_same_competition(
    tmp_path: Path,
) -> None:
    db_path = build_matches_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_matches values
            (1, 'PL', 2403, '2025-09-01 15:00:00', true, 'FINISHED', 1, 3, 2, 2),
            (2, 'PL', 2502, '2026-09-01 15:00:00', true, 'FINISHED', 2, 1, 0, 0)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_teams_in_season(con, "PL", 2502)

    # Team 3 only ever appears in season 2403 (a prior season) -- it must
    # not leak into the 2502 result just because it shares a competition
    # with teams (1, 2) that genuinely played in 2502.
    assert set(rows["team_id"]) == {1, 2}
    assert 3 not in set(rows["team_id"])


def test_teams_in_season_excludes_a_different_competition(tmp_path: Path) -> None:
    db_path = build_matches_db(tmp_path)
    con = duckdb.connect(str(db_path))
    con.execute("""
        insert into main.fct_matches values
            (1, 'PL', 2502, '2026-09-01 15:00:00', true, 'FINISHED', 1, 2, 1, 0),
            (2, 'CL', 2502, '2026-09-02 15:00:00', true, 'FINISHED', 2, 1, 0, 0)
    """)
    con.close()
    con = duckdb.connect(str(db_path), read_only=True)

    rows = get_teams_in_season(con, "PL", 2502)

    # Both teams also appear in a CL match sharing the same season_id --
    # the competition_code filter, not just season_id, must scope this.
    assert set(rows["team_id"]) == {1, 2}
    cl_rows = get_teams_in_season(con, "CL", 2502)
    assert set(cl_rows["team_id"]) == {1, 2}
