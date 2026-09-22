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
        create table fct_standings_snapshot (
            competition_code varchar, season_id bigint, team_id bigint,
            snapshot_date date, stage varchar, table_type varchar,
            position integer, played_games integer, won integer,
            draw integer, lost integer, goals_for integer,
            goals_against integer, goal_difference integer,
            points integer, form varchar
        )
    """)
    con.execute("""
        insert into fct_standings_snapshot values
            ('PL', 2526, 1, '2026-01-15', 'REGULAR_SEASON', 'TOTAL',
             1, 20, 15, 3, 2, 40, 15, 25, 48, 'WWDWL')
    """)
    con.execute("""
        create table mart_team_form (
            team_id bigint, competition_code varchar, season_id bigint,
            last_5_results varchar
        )
    """)
    con.execute("""
        create table mart_standings_over_time (
            competition_code varchar, season_id bigint, team_id bigint,
            group_name varchar, matchday integer, position integer,
            cumulative_points integer, cumulative_goal_difference integer,
            cumulative_goals_for integer
        )
    """)
    con.execute("""
        insert into mart_standings_over_time values
            ('PL', 2425, 1, NULL, 38, 3, 70, 20, 65)
    """)
    con.execute("""
        create table fct_scorers (
            player_id bigint, competition_code varchar, season_id bigint,
            team_id bigint, team_name varchar, player_name varchar,
            goals bigint, assists bigint, played_matches bigint,
            penalties bigint
        )
    """)
    con.execute("""
        insert into fct_scorers values
            (501, 'PL', 2526, 1, 'Team A', 'Top Scorer', 12, 4, 20, 2)
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


def test_match_detail_returns_the_real_match(client: TestClient) -> None:
    response = client.get("/api/matches/1001")

    assert response.status_code == 200
    body = response.json()
    assert body["home_team_name"] == "Team A"
    assert body["full_time_home"] == 2


def test_match_detail_404s_for_an_unknown_match_id(client: TestClient) -> None:
    response = client.get("/api/matches/999999")

    assert response.status_code == 404


def test_standings_returns_the_current_table(client: TestClient) -> None:
    response = client.get("/api/leagues/PL/standings?season=2526")

    assert response.status_code == 200
    body = response.json()
    assert body["message"] is None
    assert body["table"][0]["team_name"] == "Team A"
    assert body["table"][0]["points"] == 48


def test_reconstructed_standings_returns_the_final_matchday(client: TestClient) -> None:
    response = client.get("/api/leagues/PL/reconstructed-standings?season=2425")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["position"] == 3
    assert body[0]["points"] == 70


def test_results_returns_the_finished_match(client: TestClient) -> None:
    response = client.get("/api/leagues/PL/results?season=2526")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["full_time_home"] == 2


def test_fixtures_returns_no_upcoming_matches(client: TestClient) -> None:
    response = client.get("/api/leagues/PL/fixtures?season=2526")

    assert response.status_code == 200
    assert response.json() == []


def test_scorers_returns_the_ranked_leaderboard(client: TestClient) -> None:
    response = client.get("/api/leagues/PL/scorers?season=2526")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["player_name"] == "Top Scorer"
    assert body[0]["goals"] == 12


def test_assists_returns_the_ranked_leaderboard(client: TestClient) -> None:
    response = client.get("/api/leagues/PL/assists?season=2526")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["player_name"] == "Top Scorer"
    assert body[0]["assists"] == 4


def test_position_history_returns_every_teams_matchday_positions(client: TestClient) -> None:
    response = client.get("/api/leagues/PL/position-history?season=2425")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["team_name"] == "Team A"
    assert body[0]["matchday"] == 38
    assert body[0]["position"] == 3
    assert body[0]["crest"] == "a.png"
