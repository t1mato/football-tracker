"""Streaks & Records -- current and all-time win/unbeaten streaks per
team, within one competition, per PLAN.md item 8.
"""

import streamlit as st

from app.queries import (
    get_competitions,
    get_connection,
    get_current_season_id,
    get_streaks,
    get_teams_in_season,
)

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
    # mart_streaks has no notion of "still competing" -- it reports every
    # team that's ever had a decided match in this competition, including
    # ones that left years ago (relegated, or eliminated from a prior
    # Champions League edition). Filtering to the current season's roster
    # keeps "Current Streaks" from rendering a stale, long-gone team's
    # streak indistinguishably from a genuinely active one.
    current_season_id = get_current_season_id(con, selected_code)
    current_team_ids = set(
        get_teams_in_season(con, selected_code, current_season_id)["team_id"]
    )

    st.subheader("Current Streaks")
    current = streaks[streaks["team_id"].isin(current_team_ids)][
        ["team_name", "current_win_streak", "current_unbeaten_streak"]
    ].sort_values(
        by=["current_win_streak", "current_unbeaten_streak", "team_name"],
        ascending=[False, False, True],
    )
    st.dataframe(current, hide_index=True)
    st.caption(
        "A streak can span the season boundary -- it doesn't reset just "
        "because a new season started."
    )

    st.subheader("All-Time Records")
    longest = streaks[
        ["team_name", "longest_win_streak", "longest_unbeaten_streak"]
    ].sort_values(
        by=["longest_win_streak", "longest_unbeaten_streak", "team_name"],
        ascending=[False, False, True],
    )
    st.dataframe(longest, hide_index=True)
    st.caption(
        '"All-time" means this project\'s backfilled history (around 4 '
        "seasons), not the competition's full real-world record."
    )
