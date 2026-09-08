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


def format_kickoff(row: pd.Series) -> str:
    date_str = row["kickoff_utc"].strftime("%Y-%m-%d")
    if not row["kickoff_time_confirmed"]:
        return f"{date_str} (time TBD)"
    return row["kickoff_utc"].strftime("%Y-%m-%d %H:%M UTC")


def match_display(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Kickoff", "Home", "Score", "Away"])
    out = df.copy()
    out["Kickoff"] = out.apply(format_kickoff, axis=1)
    out["Score"] = out.apply(
        lambda r: f"{int(r['full_time_home'])}-{int(r['full_time_away'])}"
        if pd.notna(r["full_time_home"])
        else "",
        axis=1,
    )
    return out[["Kickoff", "home_team_name", "Score", "away_team_name"]].rename(
        columns={"home_team_name": "Home", "away_team_name": "Away"}
    )
