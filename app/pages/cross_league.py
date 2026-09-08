"""Cross-League Dashboard -- current season stats across every tracked
competition, per PLAN.md item 6.
"""

import streamlit as st

from app.formatting import format_stat
from app.queries import get_connection, get_cross_league_stats

st.title("Cross-League Dashboard")

con = get_connection()
stats = get_cross_league_stats(con)

display = stats.copy()
# format_stat renders these as strings (not numeric columns) so a null
# shows as a genuinely blank cell instead of Streamlit's default "None"
# text -- the cost is that st.dataframe's interactive column sort becomes
# lexicographic, not numeric, on these four columns. Not visible with
# today's low match counts, but will misorder once any competition passes
# 99 decided matches this season (e.g. "100" sorting before "99").
display["Matches Played"] = display["decided_matches"].apply(lambda n: format_stat(n, ".0f"))
display["Avg Goals/Match"] = display["avg_goals_per_match"].apply(
    lambda v: format_stat(v, ".1f")
)
display["Avg Goal Margin"] = display["avg_goal_margin"].apply(lambda v: format_stat(v, ".1f"))
display["Home Win %"] = display["home_win_rate"].apply(lambda v: format_stat(v, ".0%"))

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
