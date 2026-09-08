"""Top Scorers -- leaderboard for one competition's current season."""

import streamlit as st

from app.queries import (
    get_competitions,
    get_connection,
    get_current_season_id,
    get_top_scorers,
)

st.title("Top Scorers")

con = get_connection()
competitions = get_competitions(con)

selected_name = st.selectbox("Competition", competitions["competition_name"])
selected_code = competitions.loc[
    competitions["competition_name"] == selected_name, "competition_code"
].iloc[0]

season_id = get_current_season_id(con, selected_code)

scorers = get_top_scorers(con, selected_code, season_id)
if scorers.empty:
    st.info("No scorers recorded yet this season in this competition.")
else:
    st.dataframe(scorers, hide_index=True)
