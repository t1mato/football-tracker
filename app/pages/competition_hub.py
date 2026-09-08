"""Competition Hub -- standings + recent results/fixtures per competition."""

import streamlit as st

from app.formatting import match_display
from app.queries import (
    get_competitions,
    get_connection,
    get_current_season_id,
    get_recent_matches,
    get_standings,
    get_upcoming_matches,
)

st.title("Competition Hub")

con = get_connection()
competitions = get_competitions(con)

selected_name = st.selectbox("Competition", competitions["competition_name"])
selected_code = competitions.loc[
    competitions["competition_name"] == selected_name, "competition_code"
].iloc[0]

season_id = get_current_season_id(con, selected_code)

st.subheader("Standings")
standings = get_standings(con, selected_code, season_id)
if standings.table is not None:
    st.dataframe(standings.table, hide_index=True)
else:
    st.info(standings.message)


results_col, fixtures_col = st.columns(2)

with results_col:
    st.subheader("Recent Results")
    recent = get_recent_matches(con, selected_code, season_id)
    st.dataframe(match_display(recent), hide_index=True)

with fixtures_col:
    st.subheader("Upcoming Fixtures")
    upcoming = get_upcoming_matches(con, selected_code, season_id)
    st.dataframe(match_display(upcoming), hide_index=True)
