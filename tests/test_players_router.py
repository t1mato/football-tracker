"""Tests for backend/routers/players.py. Same pattern as
tests/test_leagues_router.py and tests/test_teams_router.py: FastAPI
TestClient + a hand-built DuckDB fixture, one test per endpoint's real
behavior (not just "returns 200").
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
        insert into dim_teams values (1, 'Team A', 'a.png'), (2, 'Team B', NULL)
    """)
    con.execute("""
        create table dim_players (
            player_id bigint, player_name varchar, position varchar,
            nationality varchar, date_of_birth date, team_id bigint
        )
    """)
    con.execute("""
        insert into dim_players values
            (101, 'Alice Smith', 'Forward', 'England', '2000-06-15', 1),
            (102, 'Bob Jones', 'Defender', 'Spain', NULL, 2)
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
        create table fct_scorers (
            player_id bigint, competition_code varchar, season_id bigint,
            team_id bigint, team_name varchar, player_name varchar,
            goals bigint, assists bigint, played_matches bigint,
            penalties bigint
        )
    """)
    con.execute("""
        insert into fct_scorers values
            (101, 'PL', 2526, 1, 'Team A', 'Alice Smith', 12, 4, 20, 2)
    """)
    con.close()

    with TestClient(create_app(db_path=db_path)) as test_client:
        yield test_client


def test_players_directory_returns_every_player(client: TestClient) -> None:
    response = client.get("/api/players")

    assert response.status_code == 200
    body = response.json()
    names = {row["player_name"] for row in body}
    assert names == {"Alice Smith", "Bob Jones"}
    alice = next(row for row in body if row["player_name"] == "Alice Smith")
    assert alice["team_name"] == "Team A"
    assert alice["crest"] == "a.png"


def test_player_bio_returns_the_players_fields(client: TestClient) -> None:
    response = client.get("/api/players/101")

    assert response.status_code == 200
    body = response.json()
    assert body["player_name"] == "Alice Smith"
    assert body["position"] == "Forward"
    assert body["team_name"] == "Team A"


def test_player_bio_404s_for_an_unknown_id(client: TestClient) -> None:
    response = client.get("/api/players/999")

    assert response.status_code == 404


def test_scoring_history_returns_the_players_fct_scorers_rows(client: TestClient) -> None:
    response = client.get("/api/players/101/scoring-history")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["competition_name"] == "Premier League"
    assert body[0]["goals"] == 12


def test_scoring_history_is_empty_for_a_player_with_no_contributions(client: TestClient) -> None:
    response = client.get("/api/players/102/scoring-history")

    assert response.status_code == 200
    assert response.json() == []
