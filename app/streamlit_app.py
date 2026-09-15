"""Router: places the logo, defines the app's 3 top-nav pages, and hands off
to st.navigation. The 8 old page files under pages/ still exist on disk but
are no longer reachable from here -- the follow-up implementation plan
deletes them once leagues.py/teams.py/players.py carry their content for
real.

streamlit run app/streamlit_app.py
"""

import streamlit as st

st.set_page_config(page_title="Football Tracker", layout="wide")
# "app/assets/logo.png", not "assets/logo.png" -- unlike st.Page (which
# resolves relative to this script's own directory), st.logo/st.image
# resolve a local path via plain os.path.isfile()/open() against the
# process's CWD. This app is always launched as `streamlit run
# app/streamlit_app.py` from the repo root (locally) or from Dockerfile.app's
# WORKDIR /app (in Cloud Run, where COPY app/ ./app/ puts the real file at
# /app/app/assets/logo.png) -- CWD is the repo root/WORKDIR in both cases,
# so the CWD-relative path is app/assets/logo.png either way. Verified by
# reading streamlit's image_to_url() in image_utils.py directly, not
# assumed.
st.logo("app/assets/logo.png", size="medium")

pages = [
    st.Page("pages/leagues.py", title="Leagues"),
    st.Page("pages/teams.py", title="Teams"),
    st.Page("pages/players.py", title="Players"),
]
st.navigation(pages, position="top").run()
