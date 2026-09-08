"""Router: defines the app's pages and hands off to st.navigation.

streamlit run app/streamlit_app.py
"""

import streamlit as st

st.set_page_config(page_title="Football Tracker", layout="wide")

pages = [
    st.Page("pages/competition_hub.py", title="Competition Hub"),
    st.Page("pages/match_center.py", title="Match Center"),
    st.Page("pages/team_profile.py", title="Team Profile"),
    st.Page("pages/top_scorers.py", title="Top Scorers"),
    st.Page("pages/head_to_head.py", title="Head-to-Head"),
    st.Page("pages/cross_league.py", title="Cross-League Dashboard"),
    st.Page("pages/season_archive.py", title="Season Archive"),
]
st.navigation(pages).run()
