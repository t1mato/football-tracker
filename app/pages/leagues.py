"""Leagues -- card grid of the 6 tracked competitions, each opening a
popup with its full Table, Recent Results, Fixtures, Leaders, and Streaks.
The Cross-League Dashboard lives as its own section below the grid, since
comparing every league at once doesn't fit inside any one league's popup.
"""

import pandas as pd
import streamlit as st

from app.formatting import format_kickoff, format_score, season_label
from app.queries import (
    get_competition_seasons,
    get_competitions,
    get_connection,
    get_cross_league_stats,
    get_current_season_id,
    get_league_fixtures,
    get_league_recent_results,
    get_reconstructed_final_standings,
    get_standings,
    get_streaks,
    get_teams_in_season,
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

    tab_table, tab_results, tab_fixtures, tab_leaders, tab_streaks = st.tabs(
        ["Table", "Recent Results", "Fixtures", "Leaders", "Streaks"]
    )

    seasons = get_competition_seasons(con, competition_code)
    current_season_id = get_current_season_id(con, competition_code)
    if seasons.empty:
        season_id = current_season_id
    else:
        labels = {
            row.season_id: season_label(row.start_date, row.end_date)
            for row in seasons.itertuples()
        }
        selected_label = st.selectbox(
            "Season", options=list(labels.values()), key=f"season_{competition_code}"
        )
        season_id = next(sid for sid, label in labels.items() if label == selected_label)

    with tab_table:
        if season_id == current_season_id:
            result = get_standings(con, competition_code, season_id)
            if result.table is None:
                st.info(result.message)
            else:
                display = result.table[
                    ["crest", "team_name", "played_games", "won", "draw", "lost",
                     "goal_difference", "points"]
                ].copy()
                display.insert(0, "position", result.table["position"])
                display = display.rename(columns={
                    "played_games": "P", "won": "W", "draw": "D", "lost": "L",
                    "goal_difference": "GD", "points": "Pts", "team_name": "Team",
                    "position": "#",
                })
                styled = display.style.map(_color_gd, subset=["GD"])
                st.dataframe(
                    styled,
                    column_config={"crest": st.column_config.ImageColumn("", width="small")},
                    hide_index=True,
                )
        else:
            reconstructed = get_reconstructed_final_standings(con, competition_code, season_id)
            if reconstructed.empty:
                st.info("No reconstructed final table available for this season.")
            else:
                st.dataframe(
                    reconstructed.rename(columns={
                        "position": "#", "team_name": "Team", "points": "Pts",
                        "goal_difference": "GD", "goals_for": "GF",
                    }),
                    hide_index=True,
                )

    with tab_results:
        results = get_league_recent_results(con, competition_code, season_id)
        if results.empty:
            st.info("No results yet this season.")
        else:
            results = results.copy()
            results["Kickoff (UTC)"] = results.apply(format_kickoff, axis=1)
            results["Score"] = results.apply(
                lambda r: format_score(r["full_time_home"], r["full_time_away"]), axis=1
            )
            display_cols = results[
                ["home_crest", "home_team_name", "Score", "away_team_name", "away_crest",
                 "Kickoff (UTC)"]
            ]
            st.dataframe(
                display_cols,
                column_config={
                    "home_crest": st.column_config.ImageColumn("", width="small"),
                    "home_team_name": "Home",
                    "away_crest": st.column_config.ImageColumn("", width="small"),
                    "away_team_name": "Away",
                },
                hide_index=True,
            )

    with tab_fixtures:
        fixtures = get_league_fixtures(con, competition_code, season_id)
        if fixtures.empty:
            st.info("No upcoming fixtures scheduled.")
        else:
            fixtures = fixtures.copy()
            fixtures["Kickoff (UTC)"] = fixtures.apply(format_kickoff, axis=1)
            display_cols = fixtures[
                ["home_crest", "home_team_name", "Kickoff (UTC)", "away_team_name", "away_crest"]
            ]
            st.dataframe(
                display_cols,
                column_config={
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
                    "rank": "Rank",
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

    with tab_streaks:
        streaks = get_streaks(con, competition_code)
        if streaks.empty:
            st.info("No streak data available for this competition.")
        else:
            st.caption(
                "Streaks reflect current form as of today, across the current "
                "season's active teams -- independent of the season selected above."
            )
            current_team_ids = set(
                get_teams_in_season(con, competition_code, current_season_id)["team_id"]
            )

            st.subheader("Current Streaks")
            current = streaks[streaks["team_id"].isin(current_team_ids)][
                ["team_name", "current_win_streak", "current_unbeaten_streak"]
            ].sort_values(
                by=["current_win_streak", "current_unbeaten_streak", "team_name"],
                ascending=[False, False, True],
            )
            st.dataframe(
                current,
                column_config={
                    "team_name": "Team",
                    "current_win_streak": "Win Streak",
                    "current_unbeaten_streak": "Unbeaten Streak",
                },
                hide_index=True,
            )
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
            st.dataframe(
                longest,
                column_config={
                    "team_name": "Team",
                    "longest_win_streak": "Longest Win Streak",
                    "longest_unbeaten_streak": "Longest Unbeaten Streak",
                },
                hide_index=True,
            )
            st.caption(
                '"All-time" means this project\'s backfilled history (around 4 '
                "seasons), not the competition's full real-world record."
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
# Copy before mutating -- get_cross_league_stats is st.cache_data-cached, so
# the DataFrame it returns may be the same object handed to other callers/
# reruns. Same local convention app/pages/cross_league.py already uses.
cross_league = cross_league.copy()
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
