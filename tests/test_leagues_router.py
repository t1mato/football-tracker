"""Tests for backend/routers/leagues.py. Same pattern as
tests/test_backend_main.py: FastAPI TestClient + a hand-built DuckDB
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
        create table dim_seasons (
            season_id bigint, competition_code varchar,
            start_date date, end_date date
        )
    """)
    con.execute("""
        insert into dim_seasons values
            (2526, 'PL', '2025-08-01', '2026-05-31'),
            (2425, 'PL', '2024-08-01', '2025-05-31')
    """)
    con.execute("""
        create table dim_teams (team_id bigint, team_name varchar, crest varchar)
    """)
    con.execute(
        "insert into dim_teams values (1, 'Team A', 'a.png'), (2, 'Team B', 'b.png')"
    )
    con.execute("""
        create table fct_matches (
            match_id bigint, competition_code varchar, season_id bigint,
            home_team_id bigint, away_team_id bigint, status varchar,
            kickoff_utc timestamp, kickoff_time_confirmed boolean,
            stage varchar, matchday integer,
            full_time_home integer, full_time_away integer, venue_key varchar
        )
    """)
    con.execute("""
        insert into fct_matches values
            (1001, 'PL', 2526, 1, 2, 'FINISHED', '2026-01-10 15:00:00', true,
             'REGULAR_SEASON', 20, 2, 1, NULL)
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
        create table mart_cross_league_stats (
            competition_code varchar, season_id bigint, decided_matches bigint,
            avg_goals_per_match double, avg_goal_margin double, home_win_rate double
        )
    """)
    con.close()

    app = create_app(db_path=db_path)
    with TestClient(app) as test_client:
        yield test_client


def test_seasons_returns_both_seasons_newest_first(client: TestClient) -> None:
    response = client.get("/api/leagues/PL/seasons")

    assert response.status_code == 200
    body = response.json()
    assert [row["season_id"] for row in body] == [2526, 2425]


def test_current_season_returns_the_max_season_id(client: TestClient) -> None:
    response = client.get("/api/leagues/PL/current-season")

    assert response.status_code == 200
    assert response.json() == {"season_id": 2526}


def test_teams_in_season_returns_teams_with_a_match(client: TestClient) -> None:
    response = client.get("/api/leagues/PL/teams-in-season?season=2526")

    assert response.status_code == 200
    team_ids = {row["team_id"] for row in response.json()}
    assert team_ids == {1, 2}


def test_cross_league_stats_returns_one_row_per_competition(client: TestClient) -> None:
    response = client.get("/api/cross-league-stats")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["competition_name"] == "Premier League"
    # LEFT JOIN with an empty mart_cross_league_stats -- absence is a real
    # state, not an error (see warehouse/queries.py's own docstring).
    assert body[0]["decided_matches"] is None


def test_match_detail_returns_the_real_match(client: TestClient) -> None:
    response = client.get("/api/matches/1001")

    assert response.status_code == 200
    body = response.json()
    assert body["home_team_name"] == "Team A"
    assert body["full_time_home"] == 2


def test_match_detail_404s_for_an_unknown_match_id(client: TestClient) -> None:
    response = client.get("/api/matches/999999")

    assert response.status_code == 404
