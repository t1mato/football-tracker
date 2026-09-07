"""Tests for weather ingestion. No test opens a socket."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import dlt
import duckdb
import pytest
import requests
import responses

from football_pipeline.weather_source import (
    FINISHED_STATUSES,
    MatchNeedingWeather,
    OpenMeteoClient,
    OutOfRangeError,
    iter_match_weather,
    select_matches_needing_weather,
    weather_source,
)

FORECAST_HOST = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_HOST = "https://archive-api.open-meteo.com/v1/archive"

HOURLY_BODY = {
    "latitude": 53.42,
    "longitude": -2.95,
    "hourly": {
        "time": ["2026-09-01T00:00", "2026-09-01T01:00"],
        "temperature_2m": [15.0, 14.5],
        "precipitation": [0.0, 0.1],
        "wind_speed_10m": [10.0, 11.0],
    },
}


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


@responses.activate
def test_fetch_hourly_returns_the_parsed_body() -> None:
    responses.get(FORECAST_HOST, json=HOURLY_BODY, status=200)

    body = OpenMeteoClient().fetch_hourly(
        FORECAST_HOST, latitude=53.43, longitude=-2.96,
        start_date="2026-09-01", end_date="2026-09-01",
    )

    assert body["hourly"]["time"] == ["2026-09-01T00:00", "2026-09-01T01:00"]
    assert responses.calls[0].request.params["latitude"] == "53.43"
    assert responses.calls[0].request.params["hourly"] == (
        "temperature_2m,precipitation,wind_speed_10m"
    )
    assert responses.calls[0].request.params["timezone"] == "UTC"


@responses.activate
def test_an_out_of_range_400_is_clipped_and_retried_once() -> None:
    """The real probe's error shape: a 400 whose body states the exact bounds."""
    responses.get(
        FORECAST_HOST,
        json={"error": True, "reason": "Parameter 'end_date' is out of allowed "
                                        "range from 2026-06-06 to 2026-09-22"},
        status=400,
    )
    responses.get(FORECAST_HOST, json=HOURLY_BODY, status=200)

    OpenMeteoClient().fetch_hourly(
        FORECAST_HOST, latitude=53.43, longitude=-2.96,
        start_date="2026-05-01", end_date="2026-09-25",
    )

    assert len(responses.calls) == 2
    retried = responses.calls[1].request.params
    assert retried["start_date"] == "2026-06-06"
    assert retried["end_date"] == "2026-09-22"


@responses.activate
def test_a_second_out_of_range_400_after_clipping_raises() -> None:
    """A clipped retry that ALSO 400s gives up rather than retrying forever.

    The requested range overlaps the allowed window (so clipping succeeds
    and a second real request goes out), but that second request 400s too
    -- one retry only, ever.
    """
    for _ in range(2):
        responses.get(
            FORECAST_HOST,
            json={"error": True, "reason": "Parameter 'start_date' is out of "
                                            "allowed range from 2026-06-06 to 2026-09-22"},
            status=400,
        )

    with pytest.raises(OutOfRangeError):
        OpenMeteoClient().fetch_hourly(
            FORECAST_HOST, latitude=53.43, longitude=-2.96,
            start_date="2026-01-01", end_date="2026-09-25",
        )

    assert len(responses.calls) == 2


@responses.activate
def test_a_request_with_no_overlap_at_all_raises_without_a_wasted_retry() -> None:
    """Clipping to an empty range means don't bother retrying -- there's
    nothing a second identical request could return that the first didn't.
    """
    responses.get(
        FORECAST_HOST,
        json={"error": True, "reason": "Parameter 'start_date' is out of "
                                        "allowed range from 2026-06-06 to 2026-09-22"},
        status=400,
    )

    with pytest.raises(OutOfRangeError):
        OpenMeteoClient().fetch_hourly(
            FORECAST_HOST, latitude=53.43, longitude=-2.96,
            start_date="2020-01-01", end_date="2020-01-31",
        )

    assert len(responses.calls) == 1


@responses.activate
def test_a_server_error_propagates_without_retrying() -> None:
    """No retry for a failure mode the probe never observed."""
    responses.get(FORECAST_HOST, json={}, status=500)

    with pytest.raises(requests.HTTPError):
        OpenMeteoClient().fetch_hourly(
            FORECAST_HOST, latitude=53.43, longitude=-2.96,
            start_date="2026-09-01", end_date="2026-09-01",
        )

    assert len(responses.calls) == 1


ANFIELD_SEP_BODY = {
    "hourly": {
        "time": ["2026-09-01T14:00", "2026-09-01T15:00", "2026-09-20T12:00"],
        "temperature_2m": [16.0, 16.5, 18.0],
        "precipitation": [0.0, 0.2, 0.0],
        "wind_speed_10m": [12.0, 13.0, 9.0],
    }
}


@responses.activate
def test_one_finished_and_one_upcoming_match_hit_different_endpoints() -> None:
    responses.get(ARCHIVE_HOST, json=ANFIELD_SEP_BODY, status=200)
    responses.get(FORECAST_HOST, json=ANFIELD_SEP_BODY, status=200)

    matches = [
        MatchNeedingWeather(1, "anfield", "2026-09-01", 15, "FINISHED", 53.43, -2.96),
        MatchNeedingWeather(2, "anfield", "2026-09-20", 12, "TIMED", 53.43, -2.96),
    ]

    rows = list(iter_match_weather(OpenMeteoClient(), matches))

    assert len(responses.calls) == 2
    assert {r["match_id"] for r in rows} == {1, 2}
    row_1 = next(r for r in rows if r["match_id"] == 1)
    assert row_1["data_type"] == "actual"
    assert row_1["temperature_2m"] == 16.5
    assert row_1["venue_key"] == "anfield"
    row_2 = next(r for r in rows if r["match_id"] == 2)
    assert row_2["data_type"] == "forecast"
    assert row_2["temperature_2m"] == 18.0


@responses.activate
def test_two_matches_at_the_same_venue_share_one_call() -> None:
    responses.get(ARCHIVE_HOST, json=ANFIELD_SEP_BODY, status=200)

    matches = [
        MatchNeedingWeather(1, "anfield", "2026-09-01", 14, "FINISHED", 53.43, -2.96),
        MatchNeedingWeather(2, "anfield", "2026-09-01", 15, "FINISHED", 53.43, -2.96),
    ]

    rows = list(iter_match_weather(OpenMeteoClient(), matches))

    assert len(responses.calls) == 1
    assert {r["match_id"] for r in rows} == {1, 2}


@responses.activate
def test_a_match_whose_hour_is_missing_from_the_response_is_skipped() -> None:
    """Clipping (Task 2) can shrink the range below what a match needs --
    that match is silently absent this run, not an error.
    """
    responses.get(ARCHIVE_HOST, json={"hourly": {
        "time": ["2026-09-01T14:00"], "temperature_2m": [16.0],
        "precipitation": [0.0], "wind_speed_10m": [12.0],
    }}, status=200)

    matches = [MatchNeedingWeather(1, "anfield", "2026-09-01", 23, "FINISHED", 53.43, -2.96)]

    rows = list(iter_match_weather(OpenMeteoClient(), matches))

    assert rows == []


@responses.activate
def test_an_out_of_range_venue_is_skipped_without_failing_the_run() -> None:
    for _ in range(2):
        responses.get(
            ARCHIVE_HOST,
            json={"error": True, "reason": "Parameter 'start_date' is out of "
                                            "allowed range from 2026-06-06 to 2026-09-22"},
            status=400,
        )

    matches = [MatchNeedingWeather(1, "anfield", "2020-01-01", 12, "FINISHED", 53.43, -2.96)]

    rows = list(iter_match_weather(OpenMeteoClient(), matches))

    assert rows == []


@responses.activate
def test_the_source_exposes_one_merge_resource_keyed_on_match_id(tmp_path: Path) -> None:
    responses.get(ARCHIVE_HOST, json=ANFIELD_SEP_BODY, status=200)

    db_path = build_db(tmp_path)
    source = weather_source(client=OpenMeteoClient(), db_path=db_path)

    assert set(source.resources) == {"match_weather"}
    resource = source.resources["match_weather"]
    assert resource.write_disposition == "merge"
    assert resource._hints["primary_key"] == "match_id"


def test_an_actual_reading_overwrites_an_earlier_forecast(tmp_path: Path) -> None:
    """This is dlt's merge behaviour at write time, not a fact about data at
    rest -- can't be asserted by inspecting resource metadata alone.

    with_raw_schema=False: dlt must own raw.match_weather's creation here,
    including its _dlt_id/_dlt_load_id bookkeeping columns. A pre-existing
    hand-built table (the shape the other tests use to test the selection
    query) conflicts with dlt trying to add those columns afterward.
    """
    db_path = build_db(tmp_path, with_raw_schema=False)
    pipelines_dir = tmp_path / "pipelines"

    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, FORECAST_HOST, json=ANFIELD_SEP_BODY, status=200)
        upcoming = [MatchNeedingWeather(2, "anfield", "2026-09-20", 12, "TIMED", 53.43, -2.96)]
        pipeline = dlt.pipeline(
            pipeline_name="test_weather",
            destination=dlt.destinations.duckdb(credentials=str(db_path)),
            dataset_name="raw",
            pipelines_dir=str(pipelines_dir),
        )

        @dlt.resource(name="match_weather", write_disposition="merge", primary_key="match_id")
        def forecast_run() -> Iterator[dict[str, Any]]:
            yield from iter_match_weather(OpenMeteoClient(), upcoming)

        pipeline.run(forecast_run())

    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, ARCHIVE_HOST, json=ANFIELD_SEP_BODY, status=200)
        finished = [MatchNeedingWeather(2, "anfield", "2026-09-20", 12, "FINISHED", 53.43, -2.96)]
        pipeline = dlt.pipeline(
            pipeline_name="test_weather",
            destination=dlt.destinations.duckdb(credentials=str(db_path)),
            dataset_name="raw",
            pipelines_dir=str(pipelines_dir),
        )

        @dlt.resource(name="match_weather", write_disposition="merge", primary_key="match_id")
        def actual_run() -> Iterator[dict[str, Any]]:
            yield from iter_match_weather(OpenMeteoClient(), finished)

        pipeline.run(actual_run())

    con = duckdb.connect(str(db_path), read_only=True)
    rows = con.execute("select data_type from raw.match_weather where match_id = 2").fetchall()
    con.close()
    assert rows == [("actual",)]
