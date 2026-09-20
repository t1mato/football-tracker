"""Tests for backend/routers/teams.py. Same pattern as
tests/test_leagues_router.py: FastAPI TestClient + a hand-built DuckDB
fixture, one test per endpoint's real behavior (not just "returns 200").
"""

from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("""
        create table dim_teams (team_id bigint, team_name varchar, crest varchar)
    """)
    con.execute("""
        insert into dim_teams values
            (1, 'Team A', 'a.png'), (2, 'Team B', 'b.png'), (3, 'Team C', NULL)
    """)
    con.execute("""
        create table dim_competitions (
            competition_code varchar, competition_name varchar,
            area_name varchar, emblem varchar, area_flag varchar
        )
    """)
    con.execute("""
        insert into dim_competitions
        values ('PL', 'Premier League', 'England', NULL, NULL)
    """)
    con.execute("""
        create table dim_seasons (
            season_id bigint, competition_code varchar,
            start_date date, end_date date
        )
    """)
    con.execute("insert into dim_seasons values (2526, 'PL', '2025-08-01', '2026-05-31')")
    con.execute("""
        create table fct_matches (
            match_id bigint, competition_code varchar, season_id bigint,
            home_team_id bigint, away_team_id bigint, status varchar,
            kickoff_utc timestamp, kickoff_time_confirmed boolean,
            stage varchar, matchday integer,
            full_time_home integer, full_time_away integer, winner varchar,
            venue_key varchar
        )
    """)
    con.execute("""
        insert into fct_matches values
            (1001, 'PL', 2526, 1, 2, 'FINISHED', '2026-01-10 15:00:00', true,
             'REGULAR_SEASON', 20, 2, 1, 'HOME_TEAM', NULL),
            (1002, 'PL', 2526, 3, 1, 'SCHEDULED', '2026-02-01 15:00:00', false,
             'REGULAR_SEASON', 21, NULL, NULL, NULL, NULL)
    """)
    con.execute("""
        create table fct_team_matches (
            match_id bigint, competition_code varchar, season_id bigint,
            kickoff_date_utc date, status varchar, venue_key varchar,
            team_id bigint, opponent_team_id bigint, is_home boolean,
            goals_for integer, goals_against integer, result varchar
        )
    """)
    con.execute("""
        insert into fct_team_matches values
            (1001, 'PL', 2526, '2026-01-10', 'FINISHED', NULL,
             1, 2, true, 2, 1, 'W'),
            (1002, 'PL', 2526, '2026-02-01', 'SCHEDULED', NULL,
             1, 3, true, NULL, NULL, NULL)
    """)
    con.execute("""
        create table dim_venues (
            venue_key varchar, canonical_venue_name varchar,
            display_name varchar, capacity integer,
            latitude double, longitude double, needs_review boolean
        )
    """)
    con.execute("""
        create table fct_match_weather (
            match_id bigint, temperature_2m double, precipitation double,
            wind_speed_10m double, data_type varchar
        )
    """)
    con.close()

    app = create_app(db_path=db_path)
    with TestClient(app) as test_client:
        yield test_client


def test_teams_for_league_returns_rows_with_crest(client: TestClient) -> None:
    response = client.get("/api/teams", params={"league": "PL", "season": 2526})

    assert response.status_code == 200
    body = response.json()
    names = {row["team_name"] for row in body}
    assert names == {"Team A", "Team B", "Team C"}
    team_a = next(row for row in body if row["team_name"] == "Team A")
    assert team_a["crest"] == "a.png"


def test_all_teams_returns_every_current_season_team(client: TestClient) -> None:
    response = client.get("/api/teams/all")

    assert response.status_code == 200
    names = {row["team_name"] for row in response.json()}
    assert names == {"Team A", "Team B", "Team C"}


def test_team_form_returns_finished_matches_only(client: TestClient) -> None:
    response = client.get("/api/teams/1/form")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["opponent_team_name"] == "Team B"
    assert body[0]["result"] == "W"
    assert body[0]["goals_for"] == 2
    assert body[0]["goals_against"] == 1


def test_team_upcoming_returns_scheduled_matches_only(client: TestClient) -> None:
    response = client.get("/api/teams/1/upcoming")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["opponent_team_name"] == "Team C"
    assert body[0]["goals_for"] is None
