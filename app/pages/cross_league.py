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
display["Avg Goals/Match"] = display["avg_goals_per_match"].round(1)
display["Avg Goal Margin"] = display["avg_goal_margin"].round(1)
display["Home Win %"] = display["home_win_rate"].apply(
    lambda rate: f"{rate:.0%}" if pd.notna(rate) else None
)

st.dataframe(
    display[
        ["competition_name", "decided_matches", "Avg Goals/Match", "Avg Goal Margin", "Home Win %"]
    ].rename(
        columns={
            "competition_name": "Competition",
            "decided_matches": "Matches Played",
        }
    ),
    hide_index=True,
)
st.caption(
    "Matches Played shows how far into the season each competition's "
    "numbers are based on -- early-season averages are noisy, and a "
    "competition with no matches yet this season shows blank stats."
)
