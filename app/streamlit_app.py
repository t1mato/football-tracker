"""Competition Hub -- standings + recent results/fixtures per competition.

streamlit run app/streamlit_app.py
"""

import pandas as pd
import streamlit as st

from app.queries import (
    get_competitions,
    get_connection,
    get_current_season_id,
    get_recent_matches,
    get_standings,
    get_upcoming_matches,
)

st.set_page_config(page_title="Competition Hub", layout="wide")
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


def _format_kickoff(row: pd.Series) -> str:
    date_str = row["kickoff_utc"].strftime("%Y-%m-%d")
    if not row["kickoff_time_confirmed"]:
        return f"{date_str} (time TBD)"
    return row["kickoff_utc"].strftime("%Y-%m-%d %H:%M UTC")


def _match_display(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Kickoff"] = out.apply(_format_kickoff, axis=1)
    out["Score"] = out.apply(
        lambda r: f"{int(r['full_time_home'])}-{int(r['full_time_away'])}"
        if pd.notna(r["full_time_home"])
        else "",
        axis=1,
    )
    return out[["Kickoff", "home_team_name", "Score", "away_team_name"]].rename(
        columns={"home_team_name": "Home", "away_team_name": "Away"}
    )


results_col, fixtures_col = st.columns(2)

with results_col:
    st.subheader("Recent Results")
    recent = get_recent_matches(con, selected_code, season_id)
    st.dataframe(_match_display(recent), hide_index=True)

with fixtures_col:
    st.subheader("Upcoming Fixtures")
    upcoming = get_upcoming_matches(con, selected_code, season_id)
    st.dataframe(_match_display(upcoming), hide_index=True)
