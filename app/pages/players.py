"""Players -- a searchable directory with a bio+scoring-history popup
(concept A), plus the cross-league Golden Boot leaderboard as a second
tab (concept B, today's Top Scorers page relocated).
"""

import pandas as pd
import streamlit as st

from app.formatting import season_label
from app.queries import (
    get_competitions,
    get_connection,
    get_current_season_id,
    get_player_bio,
    get_player_scoring_history,
    get_players_directory,
    get_top_scorers,
)

st.title("Players")

con = get_connection()

tab_directory, tab_leaderboard = st.tabs(["Directory", "Golden Boot"])


@st.dialog("Player detail", width="large")
def show_player_dialog(player_id: int) -> None:
    bio = get_player_bio(con, player_id)
    if bio is None:
        st.info("Player not found.")
        return

    st.markdown(f"### {bio['player_name']}")
    if pd.notna(bio["crest"]):
        st.image(bio["crest"], width=48)

    cols = st.columns(3)
    cols[0].metric("Position", bio["position"] if pd.notna(bio["position"]) else "Unknown")
    cols[1].metric("Nationality", bio["nationality"] if pd.notna(bio["nationality"]) else "Unknown")
    if pd.notna(bio["date_of_birth"]):
        age = (pd.Timestamp.now() - pd.Timestamp(bio["date_of_birth"])).days // 365
        cols[2].metric("Age", age)
    else:
        cols[2].metric("Age", "Unknown")
    st.caption(f"Club: {bio['team_name']}" if pd.notna(bio["team_name"]) else "Club: Unknown")

    st.subheader("Scoring history")
    history = get_player_scoring_history(con, player_id)
    if history.empty:
        st.info("No goal/assist contributions recorded for this player.")
    else:
        display = history.copy()
        display["Season"] = display.apply(
            lambda r: season_label(r["start_date"], r["end_date"]), axis=1
        )
        st.dataframe(
            display[
                ["Season", "competition_name", "goals", "assists", "played_matches", "penalties"]
            ].rename(columns={
                "competition_name": "Competition", "goals": "G", "assists": "A",
                "played_matches": "MP", "penalties": "Pen",
            }),
            hide_index=True,
        )


with tab_directory:
    directory = get_players_directory(con)

    search = st.text_input("Search by name")
    teams = ["All"] + sorted(directory["team_name"].dropna().unique().tolist())
    team_filter = st.selectbox("Club", teams)

    filtered = directory
    if search:
        filtered = filtered[filtered["player_name"].str.contains(search, case=False, na=False)]
    if team_filter != "All":
        filtered = filtered[filtered["team_name"] == team_filter]

    st.caption(f"{len(filtered)} player(s)")

    cols = st.columns(4)
    for i, row in enumerate(filtered.itertuples()):
        with cols[i % 4], st.container(border=True):
            if pd.notna(row.crest):
                st.image(row.crest, width=40)
            st.markdown(f"**{row.player_name}**")
            st.caption(row.team_name if pd.notna(row.team_name) else "Unknown club")
            if st.button("View", key=f"view_player_{row.player_id}"):
                show_player_dialog(row.player_id)

with tab_leaderboard:
    competitions = get_competitions(con)
    selected_name = st.selectbox(
        "Competition", competitions["competition_name"], key="leaderboard_competition"
    )
    selected_code = competitions.loc[
        competitions["competition_name"] == selected_name, "competition_code"
    ].iloc[0]
    season_id = get_current_season_id(con, selected_code)

    scorers = get_top_scorers(con, selected_code, season_id)
    if scorers.empty:
        st.info("No scorers recorded yet this season in this competition.")
    else:
        st.dataframe(
            scorers,
            column_config={"crest": st.column_config.ImageColumn("", width="small")},
            hide_index=True,
        )
