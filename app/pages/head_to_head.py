"""Head-to-Head -- all-time record between two teams, per PLAN.md item 5."""

import streamlit as st

from app.formatting import format_kickoff, format_score
from app.queries import (
    get_connection,
    get_current_teams,
    get_head_to_head,
    get_head_to_head_matches,
)

st.title("Head-to-Head")

con = get_connection()
teams = get_current_teams(con)

team_1_name = st.selectbox("Team 1", teams["team_name"])
team_1_id = int(teams.loc[teams["team_name"] == team_1_name, "team_id"].iloc[0])

remaining_teams = teams[teams["team_name"] != team_1_name]
team_2_name = st.selectbox("Team 2", remaining_teams["team_name"])
team_2_id = int(
    remaining_teams.loc[remaining_teams["team_name"] == team_2_name, "team_id"].iloc[0]
)

record = get_head_to_head(con, team_1_id, team_2_id)

if record is None:
    st.info("These two teams haven't played each other yet.")
else:
    st.subheader(f"{team_1_name} vs {team_2_name} — all-time record")
    st.write(
        f"Played {int(record['matches_played'])}: "
        f"{team_1_name} {int(record['team_1_wins'])}W, "
        f"{team_2_name} {int(record['team_2_wins'])}W, "
        f"{int(record['draws'])}D "
        f"({int(record['team_1_goals'])}-{int(record['team_2_goals'])} goals)"
    )

    st.subheader("Past meetings")
    matches = get_head_to_head_matches(con, team_1_id, team_2_id)
    display = matches.copy()
    display["Kickoff"] = display.apply(format_kickoff, axis=1)
    display["Score"] = display.apply(
        lambda r: format_score(r["full_time_home"], r["full_time_away"]), axis=1
    )
    st.dataframe(
        display[
            ["Kickoff", "competition_name", "home_team_name", "Score", "away_team_name"]
        ].rename(
            columns={
                "competition_name": "Competition",
                "home_team_name": "Home",
                "away_team_name": "Away",
            }
        ),
        hide_index=True,
    )
