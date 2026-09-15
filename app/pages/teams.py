"""Teams -- league-filtered grid of teams, each opening a popup with
cross-competition Form/Fixtures, this-league Stats/Streaks, and a
Compare vs... head-to-head lookup.
"""

import pandas as pd
import streamlit as st

from app.formatting import format_score
from app.queries import (
    get_competitions,
    get_connection,
    get_current_season_id,
    get_current_teams,
    get_head_to_head,
    get_head_to_head_matches,
    get_standings,
    get_streaks,
    get_team_recent_form,
    get_team_upcoming,
    get_teams_for_league,
)

st.title("Teams")

con = get_connection()
competitions = get_competitions(con)


def _result_badge(result: object) -> str:
    if pd.isna(result):
        return ""
    return {"W": "🟢 W", "D": "🟡 D", "L": "🔴 L"}.get(str(result), "")


@st.dialog("Team detail", width="large")
def show_team_dialog(team_id: int, team_name: str, crest: object,
                      league_code: str, league_season_id: int) -> None:
    st.markdown(f"### {team_name}")
    if pd.notna(crest):
        st.image(crest, width=64)

    tab_form, tab_fixtures, tab_stats, tab_streaks, tab_compare = st.tabs(
        ["Form", "Fixtures", "Stats", "Streaks", "Compare vs..."]
    )

    with tab_form:
        form = get_team_recent_form(con, team_id)
        if form.empty:
            st.info("No finished matches recorded yet.")
        else:
            display = form.copy()
            display["Score"] = display.apply(
                lambda r: format_score(r["goals_for"], r["goals_against"]), axis=1
            )
            display["Result"] = display["result"].map(_result_badge)
            st.dataframe(
                display[
                    ["kickoff_date_utc", "opponent_crest", "opponent_team_name",
                     "competition_name", "Score", "Result"]
                ].rename(columns={
                    "kickoff_date_utc": "Date", "opponent_team_name": "Opponent",
                    "competition_name": "Competition",
                }),
                column_config={
                    "opponent_crest": st.column_config.ImageColumn("", width="small"),
                },
                hide_index=True,
            )

    with tab_fixtures:
        upcoming = get_team_upcoming(con, team_id)
        if upcoming.empty:
            st.info("No upcoming fixtures scheduled.")
        else:
            st.dataframe(
                upcoming[
                    ["kickoff_date_utc", "opponent_crest", "opponent_team_name",
                     "competition_name"]
                ].rename(columns={
                    "kickoff_date_utc": "Date", "opponent_team_name": "Opponent",
                    "competition_name": "Competition",
                }),
                column_config={
                    "opponent_crest": st.column_config.ImageColumn("", width="small"),
                },
                hide_index=True,
            )

    with tab_stats:
        result = get_standings(con, league_code, league_season_id)
        if result.table is None:
            st.info(result.message)
        else:
            row = result.table[result.table["team_id"] == team_id]
            if row.empty:
                st.info("No season stats available for this team in this league yet.")
            else:
                r = row.iloc[0]
                cols = st.columns(4)
                cols[0].metric("Position", int(r["position"]))
                cols[1].metric("Played", int(r["played_games"]))
                cols[2].metric("Points", int(r["points"]))
                cols[3].metric("GD", int(r["goal_difference"]))
                cols2 = st.columns(4)
                cols2[0].metric("Won", int(r["won"]))
                cols2[1].metric("Drawn", int(r["draw"]))
                cols2[2].metric("Lost", int(r["lost"]))
                cols2[3].metric("GF-GA", f"{int(r['goals_for'])}-{int(r['goals_against'])}")

    with tab_streaks:
        streaks = get_streaks(con, league_code)
        row = streaks[streaks["team_id"] == team_id]
        if row.empty:
            st.info("No streak data available for this team in this league yet.")
        else:
            r = row.iloc[0]
            cols = st.columns(2)
            cols[0].metric("Current win streak", int(r["current_win_streak"]))
            cols[1].metric("Current unbeaten streak", int(r["current_unbeaten_streak"]))
            cols2 = st.columns(2)
            cols2[0].metric("Longest win streak", int(r["longest_win_streak"]))
            cols2[1].metric("Longest unbeaten streak", int(r["longest_unbeaten_streak"]))

    with tab_compare:
        all_teams = get_current_teams(con)
        opponents = all_teams[all_teams["team_id"] != team_id]
        opponent_name = st.selectbox(
            "Compare against", opponents["team_name"], key=f"compare_{team_id}"
        )
        opponent_id = int(
            opponents.loc[opponents["team_name"] == opponent_name, "team_id"].iloc[0]
        )
        record = get_head_to_head(con, team_id, opponent_id)
        if record is None:
            st.info("These two teams haven't played each other yet.")
        else:
            st.write(
                f"Played {int(record['matches_played'])}: "
                f"{team_name} {int(record['team_1_wins'])}W, "
                f"{opponent_name} {int(record['team_2_wins'])}W, "
                f"{int(record['draws'])}D "
                f"({int(record['team_1_goals'])}-{int(record['team_2_goals'])} goals)"
            )


selected_name = st.selectbox("League", competitions["competition_name"])
selected_code = competitions.loc[
    competitions["competition_name"] == selected_name, "competition_code"
].iloc[0]
season_id = get_current_season_id(con, selected_code)

teams = get_teams_for_league(con, selected_code, season_id)

cols = st.columns(3)
for i, row in enumerate(teams.itertuples()):
    with cols[i % 3]:
        with st.container(border=True):
            if pd.notna(row.crest):
                st.image(row.crest, width=48)
            st.markdown(f"**{row.team_name}**")
            if st.button("View", key=f"view_team_{row.team_id}"):
                show_team_dialog(row.team_id, row.team_name, row.crest, selected_code, season_id)
