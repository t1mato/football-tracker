"""Pure DataFrame/Series -> str formatting for Competition Hub's match tables.

Moved out of streamlit_app.py because these two functions are real business
logic with zero Streamlit dependency (pure pandas in, pandas/str out), and
three real bugs have been found in exactly this code (a pd.NA crash, an
empty-DataFrame crash, and a timezone-rendering bug) that "just look at the
rendered page" does not reliably catch -- the wrong output still looks
plausible. Living in their own module makes them unit-testable without a
Streamlit runtime.
"""

import pandas as pd


def format_score(full_time_home: object, full_time_away: object) -> str:
    """Empty string when either side is null -- a scheduled match, or (rare)
    an AWARDED match recorded with no goals. The original inline version in
    match_display only checked full_time_home; this checks both, since
    nothing guarantees they're null/non-null together for every match this
    project will ever see.
    """
    if pd.notna(full_time_home) and pd.notna(full_time_away):
        return f"{int(full_time_home)}-{int(full_time_away)}"
    return ""


def format_kickoff(row: pd.Series) -> str:
    date_str = row["kickoff_utc"].strftime("%Y-%m-%d")
    if not row["kickoff_time_confirmed"]:
        return f"{date_str} (time TBD)"
    return row["kickoff_utc"].strftime("%Y-%m-%d %H:%M UTC")


def format_weather(
    temperature_2m: object, precipitation: object, wind_speed_10m: object, data_type: object
) -> str:
    """Branches on data_type being null, the same way format_kickoff branches
    on kickoff_time_confirmed -- a LEFT JOIN with no matching row leaves
    every weather column null together, so checking data_type alone is
    enough to detect "no reading yet" without checking all four columns.
    """
    if pd.isna(data_type):
        return "No weather data available for this match yet."
    label = "Forecast" if data_type == "forecast" else "Actual"
    return (
        f"{label}: {temperature_2m:.0f}°C, "
        f"{precipitation:.1f}mm precipitation, {wind_speed_10m:.0f} km/h wind"
    )


def format_stat(value: object, format_spec: str) -> str:
    """Formats a nullable numeric stat for display, blank instead of a
    literal "None" -- st.dataframe renders NaN/pd.NA/None as visible
    "None" text by default (confirmed live against a not-yet-started
    competition's row), not an empty cell, so the null check has to
    happen before the value ever reaches the widget.

    format_spec is a standard Python format-spec string (e.g. ".0f",
    ".1f", ".0%") -- the same mini-language f-strings use, so callers
    read naturally as format_stat(value, ".1f") mirroring f"{value:.1f}".
    """
    if pd.notna(value):
        return format(value, format_spec)
    return ""


def season_label(start_date: object, end_date: object) -> str:
    """Human-readable season label like "2024/25", derived from a
    season's start/end dates -- season_id itself is an opaque
    API-assigned integer with no calendar meaning to a reader.
    """
    return f"{start_date.year}/{str(end_date.year)[-2:]}"


def venue_is_resolved(venue_needs_review: object) -> bool:
    """True only when a match's venue is both present and not flagged for
    review. `venue_needs_review` is null when the match's `venue_key` has no
    corresponding `dim_venues` row at all (never geocoded / never joined) --
    a different, unflagged state from a resolved venue with `needs_review =
    true`. Both must render as "not resolved", so a naive
    `if venue_needs_review:` would raise `TypeError: boolean value of NA is
    ambiguous` on the null case instead of falling through correctly.
    """
    return not (pd.isna(venue_needs_review) or venue_needs_review)


def match_display(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Kickoff", "Home", "Score", "Away"])
    out = df.copy()
    out["Kickoff"] = out.apply(format_kickoff, axis=1)
    out["Score"] = out.apply(
        lambda r: format_score(r["full_time_home"], r["full_time_away"]), axis=1
    )
    return out[["Kickoff", "home_team_name", "Score", "away_team_name"]].rename(
        columns={"home_team_name": "Home", "away_team_name": "Away"}
    )
