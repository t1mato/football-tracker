"""Team Profile -- season record, form guide, position over time, per
competition the team is currently in.
"""

import altair as alt
import streamlit as st

from app.queries import (
    get_connection,
    get_current_teams,
    get_standings,
    get_team_competitions,
    get_team_form,
    get_team_position_history,
)

st.title("Team Profile")

con = get_connection()
teams = get_current_teams(con)

selected_team_name = st.selectbox("Team", teams["team_name"])
selected_team_id = int(
    teams.loc[teams["team_name"] == selected_team_name, "team_id"].iloc[0]
)

competitions = get_team_competitions(con, selected_team_id)

if competitions.empty:
    st.info("This team has no current-season matches in any tracked competition.")
    st.stop()

for row in competitions.itertuples():
    st.subheader(row.competition_name)

    standings = get_standings(con, row.competition_code, int(row.season_id))
    if standings.table is not None:
        team_row = standings.table[standings.table["team_id"] == selected_team_id]
        if team_row.empty:
            st.info("Not in the latest published table for this competition yet.")
        else:
            st.dataframe(team_row, hide_index=True)
    else:
        st.info(standings.message)

    form = get_team_form(con, selected_team_id, row.competition_code, int(row.season_id))
    if form is not None:
        st.write(
            f"Last 5: {form['last_5_results']} "
            f"({form['wins']}W {form['draws']}D {form['losses']}L, "
            f"{form['goals_for']}-{form['goals_against']})"
        )
    else:
        st.info("No matches played yet this season in this competition.")

    history = get_team_position_history(
        con, selected_team_id, row.competition_code, int(row.season_id)
    )
    if history.empty:
        st.info("No position history to chart yet this season in this competition.")
    else:
        chart = (
            alt.Chart(history)
            .mark_line(point=True, strokeWidth=2)
            .encode(
                x=alt.X("matchday:Q", title="Matchday", axis=alt.Axis(tickMinStep=1)),
                y=alt.Y("position:Q", scale=alt.Scale(reverse=True), title="Position"),
                tooltip=["matchday", "position"],
            )
        )
        st.altair_chart(chart, width="stretch")
        st.caption(
            "Reconstructed from match results, not the official table -- may drift "
            "from it (points deductions, tiebreakers not captured here), and omits "
            "a team that hasn't yet played the season's latest matchday."
        )
