"""dlt resource: Open-Meteo weather per match.

Recurring, unlike venues.py's one-shot geocoding backfill -- a forecast is
provisionally true and gets superseded by an actual reading once a match has
been played. Read docs/specs/2026-09-07-weather-ingestion-design.md before
changing anything here; it records why each decision was made.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import requests

FINISHED_STATUSES = frozenset({"FINISHED", "AWARDED"})

HOURLY_VARS = "temperature_2m,precipitation,wind_speed_10m"

# Matches the real probe's error shape: "Parameter 'end_date' is out of
# allowed range from 2026-06-06 to 2026-09-22".
_OUT_OF_RANGE = re.compile(r"out of allowed range from (\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2})")

_SELECT_WITH_RAW = """
    select m.match_id, m.venue_key, m.kickoff_date_utc, m.kickoff_hour_utc,
           m.status, v.latitude, v.longitude
    from main.fct_matches m
    join main.dim_venues v on m.venue_key = v.venue_key
    left join raw.match_weather w
           on w.match_id = m.match_id and w.data_type = 'actual'
    where m.kickoff_time_confirmed
      and v.latitude is not null
      and w.match_id is null
"""

_SELECT_WITHOUT_RAW = """
    select m.match_id, m.venue_key, m.kickoff_date_utc, m.kickoff_hour_utc,
           m.status, v.latitude, v.longitude
    from main.fct_matches m
    join main.dim_venues v on m.venue_key = v.venue_key
    where m.kickoff_time_confirmed
      and v.latitude is not null
"""


@dataclass(frozen=True)
class MatchNeedingWeather:
    match_id: int
    venue_key: str
    weather_date: str
    weather_hour: int
    status: str
    latitude: float
    longitude: float


def _raw_match_weather_exists(con: duckdb.DuckDBPyConnection) -> bool:
    row = con.execute("""
        select 1 from information_schema.tables
        where table_schema = 'raw' and table_name = 'match_weather'
    """).fetchone()
    return row is not None


def select_matches_needing_weather(db_path: Path) -> list[MatchNeedingWeather]:
    """Matches with a confirmed kickoff hour, a geocoded venue, no actual reading yet.

    Read-only: this is ingestion deciding its own workload, the same way
    iter_standings decides its own snapshot date, not a dbt model's job.
    """
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        query = _SELECT_WITH_RAW if _raw_match_weather_exists(con) else _SELECT_WITHOUT_RAW
        rows = con.execute(query).fetchall()
    finally:
        con.close()
    return [
        MatchNeedingWeather(
            match_id=r[0],
            venue_key=r[1],
            weather_date=str(r[2]),
            weather_hour=r[3],
            status=r[4],
            latitude=r[5],
            longitude=r[6],
        )
        for r in rows
    ]


class OutOfRangeError(Exception):
    """Every date in the requested range is outside what the endpoint will serve."""


class OpenMeteoClient:
    """No RateLimiter, no 429/5xx retry -- see the design doc for why.

    The only failure mode the probe observed is a 400 for a date outside the
    endpoint's currently-valid window, and its body states the exact bounds.
    That's the one thing this client handles specially.
    """

    def __init__(
        self, *, session: requests.Session | None = None, timeout: float = 30.0
    ) -> None:
        self._session = session or requests.Session()
        self._timeout = timeout

    def fetch_hourly(
        self, host: str, *, latitude: float, longitude: float, start_date: str, end_date: str
    ) -> dict[str, Any]:
        return self._fetch(host, latitude, longitude, start_date, end_date, retried=False)

    def _fetch(
        self,
        host: str,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        *,
        retried: bool,
    ) -> dict[str, Any]:
        params: dict[str, str | float] = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": HOURLY_VARS,
            "start_date": start_date,
            "end_date": end_date,
            "timezone": "UTC",
        }
        response = self._session.get(
            host,
            params=params,
            timeout=self._timeout,
        )
        if response.status_code == 400:
            clipped = _clip_to_allowed_range(response.json(), start_date, end_date)
            if clipped is None or retried:
                raise OutOfRangeError(f"{host}: {start_date}..{end_date}")
            new_start, new_end = clipped
            return self._fetch(host, latitude, longitude, new_start, new_end, retried=True)

        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data


def _clip_to_allowed_range(
    error_body: dict[str, Any], start_date: str, end_date: str
) -> tuple[str, str] | None:
    """Parses "...out of allowed range from X to Y" and clips to it.

    Returns None if the body doesn't match that shape, or if clipping would
    produce an empty range (the requested window doesn't overlap at all).
    """
    match = _OUT_OF_RANGE.search(error_body.get("reason", ""))
    if match is None:
        return None
    allowed_start, allowed_end = match.groups()
    new_start = max(start_date, allowed_start)
    new_end = min(end_date, allowed_end)
    if new_start > new_end:
        return None
    return new_start, new_end
