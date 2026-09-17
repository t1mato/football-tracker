"""Router: places the logo, defines the app's 3 top-nav pages, and hands off
to st.navigation. Two old page files still exist on disk but are no longer
reachable from here (match_center.py's weather/venue detail and
team_profile.py's position-over-time chart have no new home yet) -- the
other 6 have been deleted now that leagues.py/teams.py/players.py carry
their content for real.

streamlit run app/streamlit_app.py
"""

from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Football Tracker", layout="wide")
# Path(__file__)-relative, not a CWD-relative string -- st.logo/st.image
# resolve a local path via plain os.path.isfile()/open() against the
# process's CWD (unlike st.Page, which resolves relative to this script's
# own directory), so a CWD-relative string breaks -- hard -- if this app is
# ever launched from a different working directory (confirmed live: a wrong
# CWD makes st.logo raise and abort the entire script, no nav, no page,
# nothing). Anchoring to this file's own location removes the hazard
# outright rather than just getting the currently-known launch paths right.
LOGO_PATH = Path(__file__).parent / "assets" / "logo.png"
st.logo(str(LOGO_PATH), size="medium")

pages = [
    st.Page("pages/leagues.py", title="Leagues"),
    st.Page("pages/teams.py", title="Teams"),
    st.Page("pages/players.py", title="Players"),
]
st.navigation(pages, position="top").run()
