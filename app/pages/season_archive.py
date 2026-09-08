"""Season Archive -- browse standings and top scorers for any backfilled
season of a competition, per PLAN.md item 7.
"""

import streamlit as st

from app.formatting import season_label
from app.queries import (
    get_competition_seasons,
    get_competitions,
    get_connection,
    get_current_season_id,
    get_reconstructed_final_standings,
    get_standings,
    get_top_scorers,
)

st.title("Season Archive")

con = get_connection()
competitions = get_competitions(con)

selected_comp_name = st.selectbox("Competition", competitions["competition_name"])
selected_comp_code = competitions.loc[
    competitions["competition_name"] == selected_comp_name, "competition_code"
].iloc[0]

seasons = get_competition_seasons(con, selected_comp_code).set_index("season_id")
if seasons.empty:
    st.info("No seasons available for this competition.")
    st.stop()

selected_season_id = int(
    st.selectbox(
        "Season",
        seasons.index,
        format_func=lambda sid: season_label(
            seasons.loc[sid, "start_date"], seasons.loc[sid, "end_date"]
        ),
    )
)

current_season_id = get_current_season_id(con, selected_comp_code)

st.subheader("Standings")
if selected_season_id == current_season_id:
    result = get_standings(con, selected_comp_code, selected_season_id)
    if result.table is not None:
        st.dataframe(result.table, hide_index=True)
    else:
        st.info(result.message)
else:
    standings = get_reconstructed_final_standings(con, selected_comp_code, selected_season_id)
    if standings.empty:
        st.info("No standings data available for this season.")
    else:
        columns = ["position", "team_name", "points", "goal_difference", "goals_for"]
        if standings["group_name"].notna().any():
            columns = ["group_name", *columns]
        st.dataframe(standings[columns], hide_index=True)
        st.caption(
            "Reconstructed from match results, not the official final table -- "
            "may not exactly match real-world tiebreakers (head-to-head record, "
            "disciplinary points) or points deductions, and teams tied on every "
            "stat share a position number (e.g. two teams both shown as position "
            "11, with none at position 12)."
        )

st.subheader("Top Scorers")
scorers = get_top_scorers(con, selected_comp_code, selected_season_id)
if scorers.empty:
    st.info("No scorers recorded for this season.")
else:
    st.dataframe(scorers, hide_index=True)
