"""dlt pipeline entrypoint. Loads football-data.org into DuckDB (or
BigQuery, via PIPELINE_DESTINATION=bigquery).

    python -m football_pipeline.pipeline              # current season
    python -m football_pipeline.pipeline 2023 2024    # backfill
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

REPO_ROOT = Path(__file__).resolve().parent.parent
TRANSFORM_DIR = REPO_ROOT / "transform"
DBT_EXECUTABLE = REPO_ROOT / ".venv" / "bin" / "dbt"

# Bump this every August when the season rolls over. If it is left behind,
# nightly runs keep requesting the stale season and fixtures silently stop
# appearing -- there is no error, just a competition that quietly goes stale.
# /competitions already returns each competition's currentSeason, so this
# could be derived from a live call instead of hardcoded, if that indirection
# is ever worth the extra request.
CURRENT_SEASON = 2026


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


def run(seasons: tuple[int, ...]) -> Any:
    pipeline = dlt.pipeline(
        pipeline_name="football_data",
        destination=_destination(),
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

    Deliberately ignores PIPELINE_DESTINATION -- always local DuckDB, never
    BigQuery. select_matches_needing_weather() opens a direct, read-only
    DuckDB connection to db_path to decide which matches need a weather
    call, independent of dlt's destination entirely; parameterizing this
    function's write side alone would not make that read work against
    BigQuery. See docs/specs/2026-09-08-bigquery-destination-design.md's
    "run_weather() is explicitly out of scope" section. The guard below
    makes that scoping loud instead of silently writing to the wrong
    place when PIPELINE_DESTINATION=bigquery is set.
    """
    if os.environ.get("PIPELINE_DESTINATION") == "bigquery":
        raise NotImplementedError(
            "run_weather() does not support PIPELINE_DESTINATION=bigquery yet -- "
            "select_matches_needing_weather() reads a local DuckDB file directly, "
            "independent of the dlt destination. See "
            "docs/specs/2026-09-08-bigquery-destination-design.md "
            "for why this was scoped out of the BigQuery destination work."
        )
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


def run_transform() -> subprocess.CompletedProcess[str]:
    """Runs `dbt build --target prod`, excluding stg_match_weather and its
    descendant fct_match_weather -- the same exclusion
    orchestration/definitions.py's star_schema_build already applies
    locally, because weather isn't wired to BigQuery yet (run_weather()
    raises NotImplementedError under PIPELINE_DESTINATION=bigquery). A
    plain `dbt build --target prod` would fail trying to build those two
    models against a raw.match_weather table nothing has ever populated
    in BigQuery.
    """
    args = [
        str(DBT_EXECUTABLE), "build",
        "--target", "prod",
        "--exclude", "stg_match_weather+",
    ]
    result = subprocess.run(  # nosec B603 -- args is built entirely from
        # hardcoded strings (DBT_EXECUTABLE plus the literal flags/values
        # above); no external/untrusted input reaches this call, and
        # shell=True is deliberately not used. Same justification as
        # orchestration/definitions.py._run_dbt_build.
        args, cwd=TRANSFORM_DIR, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"dbt build failed (exit {result.returncode}): {result.stderr}")
    return result


if __name__ == "__main__":
    if sys.argv[1:2] == ["weather"]:
        print(run_weather())
    else:
        requested = tuple(int(a) for a in sys.argv[1:]) or (CURRENT_SEASON,)
        print(f"loading seasons: {requested}")
        print(run(requested))
