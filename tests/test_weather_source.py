"""Tests for weather ingestion. No test opens a socket."""

from pathlib import Path

import duckdb
import pytest

from football_pipeline.weather_source import (
    FINISHED_STATUSES,
    select_matches_needing_weather,
)


def build_db(tmp_path: Path, *, with_raw_schema: bool = True) -> Path:
    """A real temporary DuckDB file with hand-built fixture tables.

    This is a DB read, not an HTTP call -- there is nothing to mock. Building
    the actual schema shape (main.fct_matches, main.dim_venues, optionally
    raw.match_weather) is more honest than stubbing the query result.
    """
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("""
        create table main.dim_venues (
            venue_key varchar, latitude double, longitude double
        )
    """)
    con.execute("""
        insert into main.dim_venues values
            ('anfield', 53.4309, -2.9609),
            ('needs_review_venue', null, null)
    """)
    con.execute("""
        create table main.fct_matches (
            match_id bigint, venue_key varchar, kickoff_date_utc date,
            kickoff_hour_utc integer, kickoff_time_confirmed boolean, status varchar
        )
    """)
    con.execute("""
        insert into main.fct_matches values
            (1, 'anfield', '2026-09-01', 15, true, 'FINISHED'),
            (2, 'anfield', '2026-09-20', 12, true, 'TIMED'),
            (3, 'anfield', '2026-08-01', 0, false, 'SCHEDULED'),
            (4, 'needs_review_venue', '2026-09-05', 18, true, 'TIMED')
    """)
    if with_raw_schema:
        con.execute("create schema raw")
        con.execute("""
            create table raw.match_weather (
                match_id bigint, venue_key varchar, weather_date varchar,
                weather_hour integer, temperature_2m double, precipitation double,
                wind_speed_10m double, data_type varchar
            )
        """)
    con.close()
    return db_path


def test_excludes_matches_with_unconfirmed_kickoff(tmp_path: Path) -> None:
    """Match 3 has kickoff_time_confirmed=false -- there is no hour to ask for."""
    matches = select_matches_needing_weather(build_db(tmp_path))

    assert 3 not in {m.match_id for m in matches}


def test_excludes_matches_whose_venue_has_no_coordinates(tmp_path: Path) -> None:
    """Match 4's venue is still needs_review in dim_venues -- nothing to call with."""
    matches = select_matches_needing_weather(build_db(tmp_path))

    assert 4 not in {m.match_id for m in matches}


def test_excludes_matches_that_already_have_an_actual_reading(tmp_path: Path) -> None:
    """An actual reading is ground truth and is never re-fetched."""
    db_path = build_db(tmp_path)
    duckdb.connect(str(db_path)).execute("""
        insert into raw.match_weather values
            (1, 'anfield', '2026-09-01', 15, 18.0, 0.0, 10.0, 'actual')
    """)

    matches = select_matches_needing_weather(db_path)

    assert 1 not in {m.match_id for m in matches}


def test_includes_a_forecast_row_candidate_for_refresh(tmp_path: Path) -> None:
    """Match 1 already has a row, but it's a forecast, not yet an actual --
    it's still a candidate so an upcoming-turned-finished match gets upgraded.
    """
    db_path = build_db(tmp_path)
    duckdb.connect(str(db_path)).execute("""
        insert into raw.match_weather values
            (1, 'anfield', '2026-09-01', 15, 18.0, 0.0, 10.0, 'forecast')
    """)

    matches = select_matches_needing_weather(db_path)

    assert 1 in {m.match_id for m in matches}


def test_works_before_raw_match_weather_exists(tmp_path: Path) -> None:
    """The very first run: raw.match_weather has never been created yet."""
    db_path = build_db(tmp_path, with_raw_schema=False)

    matches = select_matches_needing_weather(db_path)

    assert {m.match_id for m in matches} == {1, 2}


def test_a_selected_match_carries_its_venue_coordinates(tmp_path: Path) -> None:
    matches = select_matches_needing_weather(build_db(tmp_path))

    match_2 = next(m for m in matches if m.match_id == 2)
    assert match_2.latitude == pytest.approx(53.4309)
    assert match_2.longitude == pytest.approx(-2.9609)
    assert match_2.weather_date == "2026-09-20"
    assert match_2.weather_hour == 12
    assert match_2.status == "TIMED"


def test_finished_statuses_used_to_split_forecast_from_archive_candidates() -> None:
    assert frozenset({"FINISHED", "AWARDED"}) == FINISHED_STATUSES
