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


@pytest.fixture
def client_with_frontend(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("""
        create table dim_competitions (
            competition_code varchar, competition_name varchar,
            area_name varchar, emblem varchar, area_flag varchar
        )
    """)
    con.close()

    # A hand-built stand-in for a real `npm run build` output, not the
    # actual frontend/dist -- that directory is gitignored and CI has no
    # Node/npm step to produce it, so pointing this fixture at the real
    # path made these tests fail on a fresh checkout (404 instead of 200)
    # despite passing locally. Same convention as the DuckDB fixture
    # above: hand-built fixture data instead of depending on live/external
    # build state.
    frontend_dist = tmp_path / "dist"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text(
        "<html><body><div id=\"root\"></div></body></html>"
    )
    (frontend_dist / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"></svg>'
    )
    # backend/main.py mounts StaticFiles(directory=frontend_dist / "assets")
    # unconditionally whenever frontend_dist.exists() -- that mount raises
    # at app-construction time if "assets" doesn't exist on disk, even
    # though none of these tests exercise it directly.
    (frontend_dist / "assets").mkdir()

    app = create_app(db_path=db_path, frontend_dist=frontend_dist)
    with TestClient(app) as test_client:
        yield test_client


def test_unknown_api_path_404s(client_with_frontend: TestClient) -> None:
    response = client_with_frontend.get("/api/does-not-exist")

    assert response.status_code == 404


def test_root_path_serves_the_built_index_html(client_with_frontend: TestClient) -> None:
    response = client_with_frontend.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<div id=\"root\">" in response.text


def test_client_side_route_serves_index_html_too(client_with_frontend: TestClient) -> None:
    response = client_with_frontend.get("/teams")

    assert response.status_code == 200
    assert "<div id=\"root\">" in response.text


def test_a_real_built_asset_is_served_directly(client_with_frontend: TestClient) -> None:
    # frontend/public/favicon.svg is copied to the dist root by Vite's
    # build -- confirms the "serve a real file at the dist root directly"
    # branch (not the /assets mount, not the index.html fallback).
    response = client_with_frontend.get("/favicon.svg")

    assert response.status_code == 200
    assert "svg" in response.headers["content-type"]
