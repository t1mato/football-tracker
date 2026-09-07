"""Dagster assets: dlt ingestion (football-data.org + Open-Meteo weather) and
dbt, as one lineage graph.

No dagster-dbt: its current release line requires dbt-core<1.12, which
conflicts with this project's dbt-core>=1.12 floor (verified against 1.12.3
all session -- see docs/specs/2026-09-07-weather-ingestion-design.md and the
"Verified dbt behaviour" section of PLAN.md). Rather than downgrade a
deliberately-pinned, already-verified dependency to fit an orchestration
library, dbt is invoked the same way the Makefile already does: a plain
`dbt build` subprocess call, cwd'd into the transform/ directory. The
trade-off is coarse-grained lineage -- one Dagster asset per dbt build
step, not one per dbt model -- which is an acceptable loss for what this
project actually needs from orchestration right now.

Two dbt build steps, not one -- there's a genuine dependency cycle through
"dbt" as a whole: weather_ingestion needs fct_matches/dim_venues (built by
dbt) before it can run, and stg_match_weather (also built by dbt) needs
weather_ingestion's output. One subprocess call to `dbt build` cannot pause
partway through to wait for an external asset, so the manifest is split at
that one seam (`stg_match_weather+` vs. everything else) into two separate
invocations, with weather_ingestion materializing in between.

Assumes `dagster dev` (or any invocation of this module) runs from the repo
root, same as `python -m football_pipeline.pipeline` already does today --
pipeline.py's SECRETS_PATH and the dlt-managed DuckDB file are both relative
to that. The dbt side does NOT share this assumption: TRANSFORM_DIR and
DBT_EXECUTABLE below are anchored to this file's own location, not the
launch CWD, specifically because PLAN.md already flagged the alternative as
a silent-data-loss risk (resolving profiles.yml's relative
`../football_data.duckdb` against the wrong directory builds a new, empty
database with no error).
"""

import subprocess
from pathlib import Path

from dagster import AssetExecutionContext, Definitions, asset

from football_pipeline.pipeline import CURRENT_SEASON, run, run_weather

REPO_ROOT = Path(__file__).resolve().parent.parent
TRANSFORM_DIR = REPO_ROOT / "transform"
DBT_EXECUTABLE = REPO_ROOT / ".venv" / "bin" / "dbt"


def _run_dbt_build(context: AssetExecutionContext, *, select: str | None = None,
                    exclude: str | None = None) -> None:
    args = [str(DBT_EXECUTABLE), "build"]
    if select is not None:
        args += ["--select", select]
    if exclude is not None:
        args += ["--exclude", exclude]

    result = subprocess.run(
        args, cwd=TRANSFORM_DIR, capture_output=True, text=True, check=False
    )
    context.log.info(result.stdout)
    if result.returncode != 0:
        context.log.error(result.stderr)
        raise RuntimeError(f"dbt build failed (exit {result.returncode}): {' '.join(args)}")


@asset(group_name="ingestion")
def football_data_ingestion() -> None:
    """One dlt pipeline run populates every raw.* table football-data.org
    feeds, through the one shared rate-limited client pipeline.run() builds.
    """
    run((CURRENT_SEASON,))


@asset(deps=[football_data_ingestion], group_name="transform")
def star_schema_build(context: AssetExecutionContext) -> None:
    """Everything except stg_match_weather and its descendant, fct_match_weather --
    those need weather_ingestion's output first (see module docstring).
    """
    _run_dbt_build(context, exclude="stg_match_weather+")


@asset(deps=[star_schema_build], group_name="ingestion")
def weather_ingestion() -> None:
    """Depends on fct_matches/dim_venues, not just raw.matches/raw.teams --
    the match-selection query in weather_source.py reads the star schema
    directly, per docs/specs/2026-09-07-weather-ingestion-design.md.
    """
    run_weather()


@asset(deps=[weather_ingestion], group_name="transform")
def weather_dependent_build(context: AssetExecutionContext) -> None:
    """stg_match_weather and fct_match_weather -- the two models excluded
    from star_schema_build above.
    """
    _run_dbt_build(context, select="stg_match_weather+")


defs = Definitions(
    assets=[football_data_ingestion, star_schema_build, weather_ingestion, weather_dependent_build],
)
