"""Headless regression test for the app's router (app/streamlit_app.py).

Runs the actual entrypoint with Streamlit's own no-browser test harness --
this is what would have caught the st.logo CWD-path bug (see git history)
automatically, and guards the 3 new pages against a future regression the
same way.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

# AppTest.from_file() resolves a relative path against the *calling test
# file's* directory, not the pytest invocation's CWD -- anchor on this file's
# own location (same reasoning as app/streamlit_app.py's LOGO_PATH fix) so
# this test isn't sensitive to where pytest happens to be run from.
APP_ENTRYPOINT = Path(__file__).parent.parent / "app" / "streamlit_app.py"


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
