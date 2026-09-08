"""Cross-League Dashboard -- current season stats across every tracked
competition, per PLAN.md item 6.
"""

import pandas as pd
import streamlit as st

from app.queries import get_connection, get_cross_league_stats

st.title("Cross-League Dashboard")

con = get_connection()
stats = get_cross_league_stats(con)

display = stats.copy()
display["Matches Played"] = display["decided_matches"].apply(
    lambda n: str(int(n)) if pd.notna(n) else ""
)
display["Avg Goals/Match"] = display["avg_goals_per_match"].apply(
    lambda v: f"{v:.1f}" if pd.notna(v) else ""
)
display["Avg Goal Margin"] = display["avg_goal_margin"].apply(
    lambda v: f"{v:.1f}" if pd.notna(v) else ""
)
display["Home Win %"] = display["home_win_rate"].apply(
    lambda rate: f"{rate:.0%}" if pd.notna(rate) else ""
)

st.dataframe(
    display[
        ["competition_name", "Matches Played", "Avg Goals/Match", "Avg Goal Margin", "Home Win %"]
    ].rename(columns={"competition_name": "Competition"}),
    hide_index=True,
)
st.caption(
    "Matches Played shows how far into the season each competition's "
    "numbers are based on -- early-season averages are noisy, and a "
    "competition with no matches yet this season shows blank stats."
)
