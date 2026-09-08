"""Tests for app/formatting.py -- pure DataFrame/Series transforms with zero
Streamlit dependency, but real business logic. Three real bugs have been
found in this exact code (a pd.NA crash, an empty-DataFrame crash, and a
timezone-rendering bug), none of which "just look at the rendered page"
reliably catches -- the wrong output still looks plausible. Hence real unit
tests here rather than relying on manual app verification.
"""

import pandas as pd

from app.formatting import format_kickoff, match_display


def test_a_confirmed_kickoff_renders_date_and_time_with_utc_suffix() -> None:
    row = pd.Series(
        {
            "kickoff_utc": pd.Timestamp("2026-09-12 14:00:00"),
            "kickoff_time_confirmed": True,
        }
    )

    assert format_kickoff(row) == "2026-09-12 14:00 UTC"


def test_an_unconfirmed_kickoff_renders_time_tbd_with_just_the_date() -> None:
    row = pd.Series(
        {
            "kickoff_utc": pd.Timestamp("2026-09-12 14:00:00"),
            "kickoff_time_confirmed": False,
        }
    )

    assert format_kickoff(row) == "2026-09-12 (time TBD)"


def test_a_tz_aware_utc_timestamp_renders_the_correct_utc_time() -> None:
    """Regression test for Finding 1's bug class: constructs a tz-aware
    timestamp directly (independent of any DB connection or session
    TimeZone setting) and pins that format_kickoff renders its UTC wall-
    clock time correctly. This does NOT prove get_connection()'s
    SET TimeZone='UTC' fix works end-to-end -- a tz-aware pandas Timestamp
    already carries its own correct UTC value regardless of session
    settings, so this test would still pass even if that fix were reverted.
    It exists so nobody breaks format_kickoff's own tz-handling later while
    editing this module in isolation; Finding 1's actual end-to-end fix is
    verified separately, against the real warehouse connection.
    """
    row = pd.Series(
        {
            "kickoff_utc": pd.Timestamp("2026-09-12 14:00:00", tz="UTC"),
            "kickoff_time_confirmed": True,
        }
    )

    assert format_kickoff(row) == "2026-09-12 14:00 UTC"


def test_a_null_score_renders_as_empty_string_not_a_crash() -> None:
    """DuckDB's nullable Int64 columns come back from .df() as pandas'
    nullable Int64 dtype (pd.NA), not numpy NaN -- reproduce that exact
    shape here, since that mismatch is what caused the original bug.
    """
    df = pd.DataFrame(
        {
            "kickoff_utc": [pd.Timestamp("2026-09-12 14:00:00")],
            "kickoff_time_confirmed": [True],
            "home_team_name": ["Team A"],
            "away_team_name": ["Team B"],
            "full_time_home": pd.array([None], dtype="Int64"),
            "full_time_away": pd.array([None], dtype="Int64"),
        }
    )

    out = match_display(df)

    assert out.iloc[0]["Score"] == ""


def test_an_empty_dataframe_returns_empty_with_the_same_display_columns() -> None:
    df = pd.DataFrame(
        columns=[
            "kickoff_utc",
            "kickoff_time_confirmed",
            "home_team_name",
            "away_team_name",
            "full_time_home",
            "full_time_away",
        ]
    )

    out = match_display(df)

    assert out.empty
    assert list(out.columns) == ["Kickoff", "Home", "Score", "Away"]
