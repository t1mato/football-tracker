"""Tests for app/formatting.py -- pure DataFrame/Series transforms with zero
Streamlit dependency, but real business logic. Three real bugs have been
found in this exact code (a pd.NA crash, an empty-DataFrame crash, and a
timezone-rendering bug), none of which "just look at the rendered page"
reliably catches -- the wrong output still looks plausible. Hence real unit
tests here rather than relying on manual app verification.
"""

import pandas as pd

from app.formatting import (
    format_kickoff,
    format_score,
    format_stat,
    format_weather,
    match_display,
    venue_is_resolved,
)


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


def test_format_score_renders_home_dash_away() -> None:
    assert format_score(2, 1) == "2-1"


def test_format_score_handles_a_null_home_score() -> None:
    """DuckDB's nullable Int64 columns surface as pandas.NA, not None --
    match that exact shape, since that mismatch is what caused the
    original pd.NA bug this function's logic is protecting against.
    """
    home = pd.array([None], dtype="Int64")[0]
    assert format_score(home, 1) == ""


def test_format_score_handles_a_null_away_score() -> None:
    """The original inline lambda only checked full_time_home's null-ness --
    an away-only null would have crashed identically. This function checks
    both.
    """
    away = pd.array([None], dtype="Int64")[0]
    assert format_score(2, away) == ""


def test_format_weather_labels_an_actual_reading() -> None:
    result = format_weather(18.5, 0.0, 12.0, "actual")

    assert "Actual" in result
    assert "18" in result
    assert "12" in result


def test_format_weather_labels_a_forecast_reading() -> None:
    result = format_weather(20.0, 1.5, 8.0, "forecast")

    assert "Forecast" in result


def test_venue_is_resolved_is_false_for_a_genuinely_null_venue() -> None:
    """A match whose venue_key has no dim_venues row at all -- distinct from
    a resolved-but-flagged venue. DuckDB's actual nullable-boolean null shape
    (pandas' boolean dtype, pd.NA), not Python None -- this is exactly the
    state the reviewer found live in the warehouse (4 CL matches, season
    2557, with a null venue_key).
    """
    needs_review = pd.array([None], dtype="boolean")[0]

    assert venue_is_resolved(needs_review) is False


def test_venue_is_resolved_is_false_when_flagged_for_review() -> None:
    assert venue_is_resolved(True) is False


def test_venue_is_resolved_is_true_when_resolved_and_not_flagged() -> None:
    assert venue_is_resolved(False) is True


def test_format_stat_formats_a_present_value() -> None:
    assert format_stat(3.944444, ".1f") == "3.9"


def test_format_stat_formats_a_percentage() -> None:
    assert format_stat(0.555556, ".0%") == "56%"


def test_format_stat_formats_a_whole_number_with_no_decimal_point() -> None:
    assert format_stat(18, ".0f") == "18"


def test_format_stat_returns_empty_string_for_a_null_int64_value() -> None:
    """DuckDB's nullable Int64 columns surface as pandas.NA, not None or
    NaN -- reproduce that exact shape, matching the pattern this file
    already uses for format_score's null tests.
    """
    value = pd.array([None], dtype="Int64")[0]
    assert format_stat(value, ".0f") == ""


def test_format_stat_returns_empty_string_for_a_null_float() -> None:
    import math

    assert format_stat(math.nan, ".1f") == ""


def test_format_weather_handles_no_data_type_without_crashing() -> None:
    """A LEFT JOIN to fct_match_weather with no matching row -- all four
    columns null together, since DuckDB fills every column of a missing
    row with NULL, not just some of them.
    """
    result = format_weather(None, None, None, None)

    assert "no weather" in result.lower()
