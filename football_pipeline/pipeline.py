"""dlt pipeline entrypoint. Loads football-data.org into DuckDB.

    python -m football_pipeline.pipeline              # current season
    python -m football_pipeline.pipeline 2023 2024    # backfill
"""

import sys
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import dlt

from football_pipeline.client import FootballDataClient
from football_pipeline.football_data_source import football_data_source
from football_pipeline.rate_limiter import RateLimiter
from football_pipeline.weather_source import (
    DEFAULT_LIMITER_CAPACITY,
    DEFAULT_LIMITER_PER_SECONDS,
    OpenMeteoClient,
    weather_source,
)

SECRETS_PATH = Path(".dlt/secrets.toml")
DEFAULT_DB_PATH = Path("football_data.duckdb")

# Bump this every August when the season rolls over. If it is left behind,
# nightly runs keep requesting the stale season and fixtures silently stop
# appearing -- there is no error, just a competition that quietly goes stale.
# /competitions already returns each competition's currentSeason, so this
# could be derived from a live call instead of hardcoded, if that indirection
# is ever worth the extra request.
CURRENT_SEASON = 2026


def build_client() -> FootballDataClient:
    """One client, one limiter, for the whole run.

    A client per resource would give each its own token bucket, and eight
    buckets against a shared 10 req/min server cap earns a 429.
    """
    with open(SECRETS_PATH, "rb") as f:
        token: str = tomllib.load(f)["sources"]["football_data"]["api_token"]
    return FootballDataClient(
        api_token=token,
        limiter=RateLimiter(capacity=10, per_seconds=60, clock=time.monotonic),
    )


def run(seasons: tuple[int, ...]) -> Any:
    pipeline = dlt.pipeline(
        pipeline_name="football_data",
        destination="duckdb",
        dataset_name="raw",
    )
    source = football_data_source(
        client=build_client(),
        seasons=seasons,
        run_date=datetime.now(UTC).date(),
    )
    return pipeline.run(source)


def run_weather(db_path: Path = DEFAULT_DB_PATH) -> Any:
    """Reads fct_matches/dim_venues from db_path and writes raw.match_weather
    back into the same file -- destination must be pinned explicitly, since
    dlt's bare "duckdb" destination defaults to a file named after
    pipeline_name, not this project's actual warehouse file.
    """
    pipeline = dlt.pipeline(
        pipeline_name="football_weather",
        destination=dlt.destinations.duckdb(credentials=str(db_path)),
        dataset_name="raw",
    )
    client = OpenMeteoClient(
        limiter=RateLimiter(
            capacity=DEFAULT_LIMITER_CAPACITY,
            per_seconds=DEFAULT_LIMITER_PER_SECONDS,
            clock=time.monotonic,
        )
    )
    source = weather_source(client=client, db_path=db_path)
    return pipeline.run(source)


if __name__ == "__main__":
    if sys.argv[1:2] == ["weather"]:
        print(run_weather())
    else:
        requested = tuple(int(a) for a in sys.argv[1:]) or (CURRENT_SEASON,)
        print(f"loading seasons: {requested}")
        print(run(requested))
