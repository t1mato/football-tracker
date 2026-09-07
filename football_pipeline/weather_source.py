"""dlt resource: Open-Meteo weather per match.

Recurring, unlike venues.py's one-shot geocoding backfill -- a forecast is
provisionally true and gets superseded by an actual reading once a match has
been played. Read docs/specs/2026-09-07-weather-ingestion-design.md before
changing anything here; it records why each decision was made.
"""

from dataclasses import dataclass
from pathlib import Path

import duckdb

FINISHED_STATUSES = frozenset({"FINISHED", "AWARDED"})

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
