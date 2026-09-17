"""Headless regression test for the app's router (app/streamlit_app.py).

Runs the actual entrypoint with Streamlit's own no-browser test harness --
this is what would have caught the st.logo CWD-path bug (see git history)
automatically, and guards the 3 new pages against a future regression the
same way.
"""

from pathlib import Path

import duckdb
import pytest
from streamlit.testing.v1 import AppTest

# AppTest.from_file() resolves a relative path against the *calling test
# file's* directory, not the pytest invocation's CWD -- anchor on this file's
# own location (same reasoning as app/streamlit_app.py's LOGO_PATH fix) so
# this test isn't sensitive to where pytest happens to be run from.
APP_ENTRYPOINT = Path(__file__).parent.parent / "app" / "streamlit_app.py"


def _build_fixture_warehouse(db_path: Path) -> None:
    """A hand-built DuckDB covering only the star-schema tables the
    Leagues/Teams/Players pages query unconditionally at load time --
    before any dialog opens or button is clicked. Not a full dbt rebuild,
    and deliberately not one: this is app/queries.py:DEFAULT_DB_PATH,
    which is the real local dev warehouse (gitignored, only populated by
    actually running the pipeline) and never exists in CI; the dbt-built
    `ci.duckdb` (Makefile's `ci` target) is empty-sourced on purpose and
    would still fail here, since teams.py and players.py each default a
    competition selectbox to dim_competitions' first row and look it back
    up with `.iloc[0]`, which raises IndexError on zero rows.

    One fixture competition is therefore load-bearing; every other table
    stays empty -- traced against app/queries.py to confirm every
    function these 3 page-load paths reach tolerates zero rows (LEFT
    JOINs, `.empty` branches, or a NULL season_id that no bound `= ?` can
    match). Giving a page a new *unconditional* query -- one that runs
    outside a dialog or button click -- means extending this fixture too;
    nothing else will catch the gap before CI does, the same way nothing
    caught this one.
    """
    con = duckdb.connect(str(db_path))
    try:
        con.execute("""
            create table dim_competitions (
                competition_code varchar, competition_name varchar,
                area_name varchar, emblem varchar, area_flag varchar
            )
        """)
        con.execute(
            "insert into dim_competitions "
            "values ('PL', 'Premier League', 'England', NULL, NULL)"
        )
        con.execute("""
            create table dim_seasons (
                season_id bigint, competition_code varchar,
                start_date date, end_date date
            )
        """)
        con.execute("""
            create table dim_teams (
                team_id bigint, team_name varchar, crest varchar
            )
        """)
        con.execute("""
            create table fct_matches (
                match_id bigint, competition_code varchar, season_id bigint,
                home_team_id bigint, away_team_id bigint
            )
        """)
        con.execute("""
            create table dim_players (
                player_id bigint, player_name varchar, position varchar,
                nationality varchar, team_id bigint
            )
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
            create table mart_cross_league_stats (
                competition_code varchar, season_id bigint,
                decided_matches bigint, avg_goals_per_match double,
                avg_goal_margin double, home_win_rate double
            )
        """)
    finally:
        con.close()


@pytest.fixture(autouse=True)
def _fixture_warehouse_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """app/queries.py:DEFAULT_DB_PATH is relative ("football_data.duckdb"),
    resolved by duckdb.connect() against the process's CWD at connect
    time, not at import time -- chdir-ing here is enough to redirect
    get_connection() at the fixture built above without touching app code.

    get_connection() is @st.cache_resource-decorated with no args passed
    at any call site, so in practice only the first test in this module
    actually opens a connection -- the rest hit that cache and never see
    their own tmp_path. Rebuilding the fixture per test anyway keeps this
    module correct independent of that caching detail, and it's cheap.
    """
    _build_fixture_warehouse(tmp_path / "football_data.duckdb")
    monkeypatch.chdir(tmp_path)


def test_app_starts_with_no_exceptions_and_defaults_to_leagues() -> None:
    at = AppTest.from_file(str(APP_ENTRYPOINT))
    at.run()

    assert len(at.exception) == 0
    assert at.title[0].value == "Leagues"


def test_teams_page_loads_with_no_exceptions() -> None:
    at = AppTest.from_file(str(APP_ENTRYPOINT))
    at.run()
    at.switch_page("pages/teams.py")
    at.run()

    assert len(at.exception) == 0
    assert at.title[0].value == "Teams"


def test_players_page_loads_with_no_exceptions() -> None:
    at = AppTest.from_file(str(APP_ENTRYPOINT))
    at.run()
    at.switch_page("pages/players.py")
    at.run()

    assert len(at.exception) == 0
    assert at.title[0].value == "Players"
