"""Tests for backend/main.py -- the FastAPI app's routing/serialization
layer. warehouse.queries' own logic is already covered by
tests/test_warehouse_queries.py; these tests are about the HTTP layer on
top of it (does the connection get created once at startup, does a
DataFrame turn into the JSON shape the frontend expects), not a retest of
query correctness.
"""

from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("""
        create table dim_competitions (
            competition_code varchar, competition_name varchar,
            area_name varchar, emblem varchar, area_flag varchar
        )
    """)
    con.execute(
        "insert into dim_competitions "
        "values ('PL', 'Premier League', 'England', 'emblem.png', 'flag.svg')"
    )
    con.close()

    app = create_app(db_path=db_path)
    # Starlette's TestClient only runs the app's lifespan (startup/shutdown)
    # when used as a context manager -- a bare `TestClient(app)` never fires
    # `create_app`'s lifespan, so `app.state.con` is never set and the
    # /api/competitions route raises AttributeError. `with` is required, not
    # stylistic, for any route that reads `request.app.state.con`.
    with TestClient(app) as client:
        yield client


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_competitions_returns_the_seeded_row(client: TestClient) -> None:
    response = client.get("/api/competitions")

    assert response.status_code == 200
    body = response.json()
    assert body == [
        {
            "competition_code": "PL",
            "competition_name": "Premier League",
            "area_name": "England",
            "emblem": "emblem.png",
            "area_flag": "flag.svg",
        }
    ]
