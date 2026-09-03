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

SECRETS_PATH = Path(".dlt/secrets.toml")
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


if __name__ == "__main__":
    requested = tuple(int(a) for a in sys.argv[1:]) or (CURRENT_SEASON,)
    print(f"loading seasons: {requested}")
    print(run(requested))
