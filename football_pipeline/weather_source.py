"""dlt resource: Open-Meteo weather per match.

Recurring, unlike venues.py's one-shot geocoding backfill -- a forecast is
provisionally true and gets superseded by an actual reading once a match has
been played. Read docs/specs/2026-09-07-weather-ingestion-design.md before
changing anything here; it records why each decision was made.
"""

import logging
import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path
from typing import Any

import dlt
import duckdb
import requests

from football_pipeline.rate_limiter import RateLimiter

FINISHED_STATUSES = frozenset({"FINISHED", "AWARDED"})

FORECAST_HOST = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_HOST = "https://archive-api.open-meteo.com/v1/archive"

HOURLY_VARS = "temperature_2m,precipitation,wind_speed_10m"

logger = logging.getLogger(__name__)

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


class RateLimitExceeded(Exception):
    """The server kept returning 429 after we exhausted our retries."""


# Conservative on purpose: the real per-minute cap appears to be cost-weighted
# (date-range-days x variable-count), not a flat request count -- 25 large,
# multi-year requests tripped it in under 10 seconds while 300 small,
# 1-day ones ran a full 60s with no failure (measured 2026-09-07, see the
# design doc). capacity=10 gives roughly 2.5x margin under the measured
# failure point for the expensive request shape this project actually makes.
DEFAULT_LIMITER_CAPACITY = 10
DEFAULT_LIMITER_PER_SECONDS = 60.0

# No Retry-After header exists on this API's 429 (confirmed on the real one);
# the quota window is a minute, so that's the only wait justified without
# guessing -- same reasoning as client.py's DEFAULT_RETRY_AFTER.
_RATE_LIMIT_FALLBACK_WAIT = 60.0


class OpenMeteoClient:
    """Rate-limited like FootballDataClient, for the same reason: a real 429.

    The limiter is optimistic; the server is authoritative. There's no header
    to correct it from here (unlike football-data.org's
    X-Requests-Available-Minute), so a 429 despite proactive throttling
    empties the bucket and falls back to a fixed wait.
    """

    def __init__(
        self,
        *,
        limiter: RateLimiter,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._limiter = limiter
        self._session = session or requests.Session()
        self._sleep = sleep
        self._timeout = timeout
        self._max_retries = max_retries

    def fetch_hourly(
        self, host: str, *, latitude: float, longitude: float, start_date: str, end_date: str
    ) -> dict[str, Any]:
        return self._fetch(
            host,
            latitude,
            longitude,
            start_date,
            end_date,
            retried_range=False,
            attempt=1,
        )

    def _fetch(
        self,
        host: str,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        *,
        retried_range: bool,
        attempt: int,
    ) -> dict[str, Any]:
        wait = self._limiter.acquire()
        if wait > 0:
            self._sleep(wait)

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

        if response.status_code == 429:
            if attempt >= self._max_retries:
                raise RateLimitExceeded(f"still rate limited after {self._max_retries} attempts")
            self._limiter.sync_from_server(0)
            self._sleep(_RATE_LIMIT_FALLBACK_WAIT)
            return self._fetch(
                host,
                latitude,
                longitude,
                start_date,
                end_date,
                retried_range=retried_range,
                attempt=attempt + 1,
            )

        if response.status_code == 400:
            clipped = _clip_to_allowed_range(response.json(), start_date, end_date)
            if clipped is None or retried_range:
                raise OutOfRangeError(f"{host}: {start_date}..{end_date}")
            new_start, new_end = clipped
            return self._fetch(
                host,
                latitude,
                longitude,
                new_start,
                new_end,
                retried_range=True,
                attempt=attempt,
            )

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


def _hour_key(date_str: str, hour: int) -> str:
    return f"{date_str}T{hour:02d}:00"


def iter_match_weather(
    client: OpenMeteoClient, matches: list[MatchNeedingWeather]
) -> Iterator[dict[str, Any]]:
    """One row per match. One HTTP call per venue per endpoint, not per match.

    Groups by (endpoint, venue) so two matches sharing a venue -- and, once
    finished-vs-upcoming is decided, the same endpoint -- cost one call
    between them, scoped to that venue's own min/max needed date.
    """

    def group_key(m: MatchNeedingWeather) -> tuple[bool, str]:
        return (m.status in FINISHED_STATUSES, m.venue_key)

    by_group = sorted(matches, key=group_key)
    for (is_finished, venue_key), group_iter in groupby(by_group, key=group_key):
        group = list(group_iter)
        host = ARCHIVE_HOST if is_finished else FORECAST_HOST
        data_type = "actual" if is_finished else "forecast"
        start_date = min(m.weather_date for m in group)
        end_date = max(m.weather_date for m in group)

        try:
            body = client.fetch_hourly(
                host,
                latitude=group[0].latitude,
                longitude=group[0].longitude,
                start_date=start_date,
                end_date=end_date,
            )
        except OutOfRangeError:
            logger.info(
                "skipping %s: no valid date overlap for %s..%s", venue_key, start_date, end_date
            )
            continue

        time_index = {t: i for i, t in enumerate(body["hourly"]["time"])}
        for m in group:
            idx = time_index.get(_hour_key(m.weather_date, m.weather_hour))
            if idx is None:
                continue
            yield {
                "match_id": m.match_id,
                "venue_key": m.venue_key,
                "weather_date": m.weather_date,
                "weather_hour": m.weather_hour,
                "temperature_2m": body["hourly"]["temperature_2m"][idx],
                "precipitation": body["hourly"]["precipitation"][idx],
                "wind_speed_10m": body["hourly"]["wind_speed_10m"][idx],
                "data_type": data_type,
            }


@dlt.source(name="weather")
def weather_source(client: OpenMeteoClient, db_path: Path) -> Any:
    """One merge resource. The selection query runs once, before dlt starts
    consuming it -- there is exactly one workload decided per run.
    """
    matches = select_matches_needing_weather(db_path)

    @dlt.resource(name="match_weather", write_disposition="merge", primary_key="match_id")
    def match_weather() -> Iterator[dict[str, Any]]:
        yield from iter_match_weather(client, matches)

    return (match_weather,)
