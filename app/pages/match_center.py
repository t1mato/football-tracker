"""Match Center -- per-match venue and weather detail.

Deep link: ?match_id=<id> lands directly on that match, with both pickers
defaulted to it.
"""

import pandas as pd
import streamlit as st

from app.formatting import format_kickoff, format_score, format_weather, venue_is_resolved
from app.queries import (
    get_competitions,
    get_connection,
    get_current_season_id,
    get_match_detail,
    get_matches_for_picker,
)

st.title("Match Center")

con = get_connection()

query_match_id_raw = st.query_params.get("match_id")
default_match_id = (
    int(query_match_id_raw)
    if query_match_id_raw and query_match_id_raw.isdigit()
    else None
)
default_detail = get_match_detail(con, default_match_id) if default_match_id else None

competitions = get_competitions(con)
comp_names = list(competitions["competition_name"])

if default_detail is not None:
    default_comp_name = competitions.loc[
        competitions["competition_code"] == default_detail["competition_code"],
        "competition_name",
    ].iloc[0]
    default_comp_index = comp_names.index(default_comp_name)
else:
    default_comp_index = 0

selected_name = st.selectbox("Competition", comp_names, index=default_comp_index)
selected_code = competitions.loc[
    competitions["competition_name"] == selected_name, "competition_code"
].iloc[0]

season_id = get_current_season_id(con, selected_code)
matches = get_matches_for_picker(con, selected_code, season_id)

if matches.empty:
    st.info("No matches found for this competition's current season.")
    st.stop()

match_ids = list(matches["match_id"])
labels = [
    f"{r.home_team_name} vs {r.away_team_name} — {r.kickoff_utc:%Y-%m-%d}"
    for r in matches.itertuples()
]

if default_match_id is not None and default_match_id in match_ids:
    default_match_index = match_ids.index(default_match_id)
else:
    default_match_index = 0

selected_label = st.selectbox("Match", labels, index=default_match_index)
selected_match_id = match_ids[labels.index(selected_label)]

detail = get_match_detail(con, selected_match_id)
if detail is None:
    st.error("Could not load this match's detail.")
    st.stop()

st.header(f"{detail['home_team_name']} vs {detail['away_team_name']}")
if pd.notna(detail["matchday"]):
    stage_label = f"Matchday {int(detail['matchday'])}"
else:
    stage_label = detail["stage"].replace("_", " ").title()
st.caption(f"{selected_name} — {stage_label}")
st.write(format_kickoff(detail))
score = format_score(detail["full_time_home"], detail["full_time_away"])
if score:
    st.write(f"Score: {score}")

st.subheader("Venue")
if not venue_is_resolved(detail["venue_needs_review"]):
    st.info("Venue location not yet resolved.")
else:
    st.write(detail["venue_display_name"])
    if pd.notna(detail["capacity"]):
        st.write(f"Capacity: {int(detail['capacity']):,}")
    st.map(
        data={"lat": [detail["latitude"]], "lon": [detail["longitude"]]},
        zoom=13,
    )
st.caption(
    "Venue is shown as the home team's usual ground. Neutral-venue fixtures "
    "(e.g. a Champions League final) may not reflect the actual match location."
)

st.subheader("Weather")
st.write(
    format_weather(
        detail["temperature_2m"],
        detail["precipitation"],
        detail["wind_speed_10m"],
        detail["weather_data_type"],
    )
)
