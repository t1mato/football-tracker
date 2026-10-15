"""dlt pipeline entrypoint. Loads football-data.org into DuckDB (or
BigQuery, via PIPELINE_DESTINATION=bigquery).

    python -m football_pipeline.pipeline              # current season
    python -m football_pipeline.pipeline 2023 2024    # backfill
    python -m football_pipeline.pipeline ingest       # current season only, explicit
    python -m football_pipeline.pipeline transform    # dbt build --target prod
"""

import os
import subprocess  # nosec B404 -- used only for a fixed dbt-build invocation, see run_transform below
import sys
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import dlt

from football_pipeline.client import FootballDataClient
from football_pipeline.football_data_source import discover_current_season, football_data_source
from football_pipeline.rate_limiter import RateLimiter

SECRETS_PATH = Path(".dlt/secrets.toml")

REPO_ROOT = Path(__file__).resolve().parent.parent
TRANSFORM_DIR = REPO_ROOT / "transform"
DBT_EXECUTABLE = REPO_ROOT / ".venv" / "bin" / "dbt"


def _destination() -> str | Any:
    """Local dev is unaffected -- returns the exact "duckdb" literal
    already used today unless PIPELINE_DESTINATION=bigquery is set.

    No project= kwarg: dlt.destinations.bigquery's real constructor has
    none (verified against the installed package, not assumed from
    docs). The project resolves entirely through Application Default
    Credentials -- gcloud auth application-default login locally, a
    Cloud Run Job's attached service account in production -- confirmed
    live with a real load: credentials=None correctly resolved to the
    right project via ADC alone, with no explicit project anywhere in
    this function.
    """
    if os.environ.get("PIPELINE_DESTINATION") == "bigquery":
        return dlt.destinations.bigquery(location="US")
    return "duckdb"


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


def run(seasons: tuple[int, ...], client: FootballDataClient | None = None) -> Any:
    pipeline = dlt.pipeline(
        pipeline_name="football_data",
        destination=_destination(),
        dataset_name="raw",
    )
    source = football_data_source(
        client=client or build_client(),
        seasons=seasons,
        run_date=datetime.now(UTC).date(),
    )
    return pipeline.run(source)


def ingest_current_season() -> Any:
    """Discovers the current season live from /competitions and ingests it,
    sharing one rate-limited client between the discovery call and the
    ingest run itself -- one FootballDataClient means one token bucket, so
    the two calls stay accounted for against the same 10 req/min budget
    instead of each getting its own fresh bucket. Used by both main()'s
    default/"ingest" paths and orchestration/definitions.py's
    football_data_ingestion asset.
    """
    client = build_client()
    season = discover_current_season(client)
    print(f"loading seasons: {(season,)}")
    return run((season,), client=client)


def run_transform() -> subprocess.CompletedProcess[str]:
    """Runs `dbt build --target prod` over the whole project in one pass."""
    args = [str(DBT_EXECUTABLE), "build", "--target", "prod"]
    result = subprocess.run(  # nosec B603 -- args is built entirely from
        # hardcoded strings (DBT_EXECUTABLE plus the literal flags/values
        # above); no external/untrusted input reaches this call, and
        # shell=True is deliberately not used. Same justification as
        # orchestration/definitions.py._run_dbt_build.
        args, cwd=TRANSFORM_DIR, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"dbt build failed (exit {result.returncode}): {' '.join(args)}")
    return result


def main(argv: list[str]) -> None:
    if argv[:1] == ["ingest"]:
        print(ingest_current_season())
    elif argv[:1] == ["transform"]:
        print(run_transform())
    elif argv:
        if not all(a.isdigit() for a in argv):
            raise SystemExit(
                f"unknown mode {' '.join(argv)!r}: expected 'ingest', 'transform', "
                "or one or more season years"
            )
        requested = tuple(int(a) for a in argv)
        print(f"loading seasons: {requested}")
        print(run(requested))
    else:
        print(ingest_current_season())


if __name__ == "__main__":
    main(sys.argv[1:])
