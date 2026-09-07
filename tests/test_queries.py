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

from app.queries import get_competitions, get_current_season_id


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
