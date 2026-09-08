"""Streaks & Records -- current and all-time win/unbeaten streaks per
team, within one competition, per PLAN.md item 8.
"""

import streamlit as st

from app.queries import get_competitions, get_connection, get_streaks

st.title("Streaks & Records")

con = get_connection()
competitions = get_competitions(con)

selected_name = st.selectbox("Competition", competitions["competition_name"])
selected_code = competitions.loc[
    competitions["competition_name"] == selected_name, "competition_code"
].iloc[0]

streaks = get_streaks(con, selected_code)

if streaks.empty:
    st.info("No streak data available for this competition.")
else:
    st.subheader("Current Streaks")
    current = streaks[
        ["team_name", "current_win_streak", "current_unbeaten_streak"]
    ].sort_values(
        by=["current_win_streak", "current_unbeaten_streak", "team_name"],
        ascending=[False, False, True],
    )
    st.dataframe(current, hide_index=True)

    st.subheader("All-Time Records")
    longest = streaks[
        ["team_name", "longest_win_streak", "longest_unbeaten_streak"]
    ].sort_values(
        by=["longest_win_streak", "longest_unbeaten_streak", "team_name"],
        ascending=[False, False, True],
    )
    st.dataframe(longest, hide_index=True)
