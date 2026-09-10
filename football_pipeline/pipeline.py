"""dlt pipeline entrypoint. Loads football-data.org into DuckDB (or
BigQuery, via PIPELINE_DESTINATION=bigquery).

    python -m football_pipeline.pipeline              # current season
    python -m football_pipeline.pipeline 2023 2024    # backfill
    python -m football_pipeline.pipeline weather      # per-venue weather backfill
    python -m football_pipeline.pipeline ingest       # current season only, explicit
    python -m football_pipeline.pipeline transform    # dbt build --target prod, weather excluded
    python -m football_pipeline.pipeline transform-weather  # dbt build, weather-dependent models
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
from google.cloud import bigquery

from football_pipeline.client import FootballDataClient
from football_pipeline.football_data_source import football_data_source
from football_pipeline.rate_limiter import RateLimiter
from football_pipeline.weather_source import (
    DEFAULT_LIMITER_CAPACITY,
    DEFAULT_LIMITER_PER_SECONDS,
    OpenMeteoClient,
    select_matches_needing_weather,
    select_matches_needing_weather_bigquery,
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
    """Ingests Open-Meteo weather for matches needing it, into whichever
    destination PIPELINE_DESTINATION selects -- local DuckDB by default,
    BigQuery when set to "bigquery". Mirrors _destination()'s branch
    exactly for the write side; the read side also has to branch, since
    select_matches_needing_weather() queries the star schema directly
    (there is no dlt "read arbitrary SQL" API to route through instead).
    See docs/specs/2026-09-10-weather-on-bigquery-design.md.
    """
    if os.environ.get("PIPELINE_DESTINATION") == "bigquery":
        bq_client = bigquery.Client(project=os.environ["GCP_PROJECT"])
        matches = select_matches_needing_weather_bigquery(bq_client)
        destination = _destination()
    else:
        matches = select_matches_needing_weather(db_path)
        destination = dlt.destinations.duckdb(credentials=str(db_path))

    pipeline = dlt.pipeline(
        pipeline_name="football_weather",
        destination=destination,
        dataset_name="raw",
    )
    client = OpenMeteoClient(
        limiter=RateLimiter(
            capacity=DEFAULT_LIMITER_CAPACITY,
            per_seconds=DEFAULT_LIMITER_PER_SECONDS,
            clock=time.monotonic,
        )
    )
    source = weather_source(client=client, matches=matches)
    return pipeline.run(source)


def run_transform() -> subprocess.CompletedProcess[str]:
    """Runs `dbt build --target prod`, excluding everything descended from
    (or attached to) the raw.match_weather source. run_transform_weather(),
    invoked as the next step in production's 4-step chain, builds those
    weather-dependent models after run_weather() has populated raw.match_weather.

    `--exclude source:raw.match_weather+` selects the source node itself,
    both stg_match_weather/fct_match_weather models descended from it, and
    its two source-attached generic tests (source_not_null_..., source_
    unique_...) declared directly on it in _sources.yml. A plain `--exclude
    stg_match_weather+` (the model, not the source) misses those source
    tests entirely -- they're upstream siblings of stg_match_weather, not
    its descendants, so `+` on the model never reaches them. Confirmed live
    against football-tracker-508022: with the model-only exclusion, `dbt
    build --target prod` failed on exactly those two source tests
    ("Not found: Table ...raw.match_weather was not found in location US").
    The source-based selector is a strict superset of the model-based one
    (verified via `dbt list`): every node the old `stg_match_weather+`
    selector excluded is still excluded, and the only thing this widens is
    the two source-attached generic tests above. (fct_match_weather's own
    two unit tests, declared in transform/models/marts/_marts.yml, are
    unaffected either way -- they were already a stg_match_weather+
    descendant under the old selector, so this change excludes nothing new
    there. They're covered by `make ci`/`make tz-check` regardless, since
    unit tests run against inline fixtures, not live data.)
    """
    args = [
        str(DBT_EXECUTABLE), "build",
        "--target", "prod",
        "--exclude", "source:raw.match_weather+",
    ]
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


def run_transform_weather() -> subprocess.CompletedProcess[str]:
    """Builds stg_match_weather/fct_match_weather -- the slice
    run_transform() excludes. Must run after both run_transform() and
    run_weather() have completed in this order:
    run_transform() -> run_weather() -> run_transform_weather(). Mirrors
    orchestration/definitions.py's local weather_dependent_build asset
    (`--select source:raw.match_weather+`).
    """
    args = [
        str(DBT_EXECUTABLE), "build",
        "--target", "prod",
        "--select", "source:raw.match_weather+",
    ]
    result = subprocess.run(  # nosec B603 -- same justification as run_transform above:
        # args is built entirely from hardcoded strings, no external input,
        # shell=True not used.
        args, cwd=TRANSFORM_DIR, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"dbt build failed (exit {result.returncode}): {' '.join(args)}")
    return result


def main(argv: list[str]) -> None:
    if argv[:1] == ["weather"]:
        print(run_weather())
    elif argv[:1] == ["ingest"]:
        print(run((CURRENT_SEASON,)))
    elif argv[:1] == ["transform"]:
        print(run_transform())
    elif argv[:1] == ["transform-weather"]:
        print(run_transform_weather())
    else:
        requested = tuple(int(a) for a in argv) or (CURRENT_SEASON,)
        print(f"loading seasons: {requested}")
        print(run(requested))


if __name__ == "__main__":
    main(sys.argv[1:])
