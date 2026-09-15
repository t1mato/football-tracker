"""Leagues -- card grid of the 6 tracked competitions, each opening a
popup with its full Table, Fixtures, and Leaders. The Cross-League
Dashboard lives as its own section below the grid, since comparing every
league at once doesn't fit inside any one league's popup.
"""

import pandas as pd
import streamlit as st

from app.queries import (
    get_competition_seasons,
    get_competitions,
    get_connection,
    get_cross_league_stats,
    get_current_season_id,
    get_league_fixtures,
    get_standings,
    get_top_scorers,
)

st.title("Leagues")

con = get_connection()
competitions = get_competitions(con)


def _color_gd(value: object) -> str:
    if pd.isna(value):
        return ""
    if value > 0:
        return "color: #1E9E5A"
    if value < 0:
        return "color: #D93B3B"
    return "color: inherit"


@st.dialog("League detail", width="large")
def show_league_dialog(competition_code: str, competition_name: str, emblem: str) -> None:
    st.markdown(f"### {competition_name}")
    if pd.notna(emblem):
        st.image(emblem, width=64)

    tab_table, tab_fixtures, tab_leaders = st.tabs(["Table", "Fixtures", "Leaders"])

    seasons = get_competition_seasons(con, competition_code)
    current_season_id = get_current_season_id(con, competition_code)
    if seasons.empty:
        season_id = current_season_id
    else:
        labels = {
            row.season_id: f"{row.start_date.year}/{str(row.end_date.year)[-2:]}"
            for row in seasons.itertuples()
        }
        selected_label = st.selectbox(
            "Season", options=list(labels.values()), key=f"season_{competition_code}"
        )
        season_id = next(sid for sid, label in labels.items() if label == selected_label)

    with tab_table:
        result = get_standings(con, competition_code, season_id)
        if result.table is None:
            st.info(result.message)
        else:
            display = result.table[
                ["crest", "team_name", "played_games", "won", "draw", "lost",
                 "goal_difference", "points"]
            ].rename(columns={
                "played_games": "P", "won": "W", "draw": "D", "lost": "L",
                "goal_difference": "GD", "points": "Pts", "team_name": "Team",
            })
            styled = display.style.map(_color_gd, subset=["GD"])
            st.dataframe(
                styled,
                column_config={"crest": st.column_config.ImageColumn("", width="small")},
                hide_index=True,
            )

    with tab_fixtures:
        fixtures = get_league_fixtures(con, competition_code, season_id)
        if fixtures.empty:
            st.info("No upcoming fixtures scheduled.")
        else:
            st.dataframe(
                fixtures,
                column_config={
                    "kickoff_utc": st.column_config.DatetimeColumn(
                        "Kickoff", format="YYYY-MM-DD HH:mm"
                    ),
                    "kickoff_time_confirmed": None,
                    "home_crest": st.column_config.ImageColumn("", width="small"),
                    "home_team_name": "Home",
                    "away_crest": st.column_config.ImageColumn("", width="small"),
                    "away_team_name": "Away",
                },
                hide_index=True,
            )

    with tab_leaders:
        leaders = get_top_scorers(con, competition_code, season_id)
        if leaders.empty:
            st.info("No scorer data yet for this competition/season.")
        else:
            st.dataframe(
                leaders,
                column_config={
                    "crest": st.column_config.ImageColumn("", width="small"),
                    "player_name": "Player",
                    "team_name": "Team",
                    "goals": "G",
                    "assists": "A",
                    "played_matches": "MP",
                    "penalties": "Pen",
                },
                hide_index=True,
            )


cols = st.columns(3)
for i, row in enumerate(competitions.itertuples()):
    with cols[i % 3], st.container(border=True):
        if pd.notna(row.emblem):
            st.image(row.emblem, width=48)
        st.markdown(f"**{row.competition_name}**")
        flag_col, name_col = st.columns([1, 4])
        with flag_col:
            if pd.notna(row.area_flag):
                st.image(row.area_flag, width=20)
        with name_col:
            st.caption(row.area_name)
        if st.button("View", key=f"view_{row.competition_code}"):
            show_league_dialog(row.competition_code, row.competition_name, row.emblem)

st.divider()
st.subheader("Cross-League Dashboard")
cross_league = get_cross_league_stats(con)
# NumberColumn's printf-style format spec does not auto-multiply by 100 the
# way Python's %-format-spec type (".0%", used by app/pages/cross_league.py
# for this same underlying value) does -- home_win_rate arrives as a
# fraction in [0.0, 1.0], so "%.0f%%" needs the value pre-multiplied or it
# renders 0.42 as "0%" instead of "42%".
cross_league["home_win_rate"] = cross_league["home_win_rate"] * 100
st.dataframe(
    cross_league,
    column_config={
        "competition_name": "Competition",
        "decided_matches": "Decided Matches",
        "avg_goals_per_match": st.column_config.NumberColumn("Avg Goals/Match", format="%.2f"),
        "avg_goal_margin": st.column_config.NumberColumn("Avg Margin", format="%.2f"),
        "home_win_rate": st.column_config.NumberColumn("Home Win %", format="%.0f%%"),
    },
    hide_index=True,
)
