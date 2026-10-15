"""Dagster assets: dlt ingestion (football-data.org) and dbt, as one lineage graph.

No dagster-dbt: its current release line requires dbt-core<1.12, which
conflicts with this project's dbt-core>=1.12 floor (verified against 1.12.3
all session -- see the "Verified dbt behaviour" section of PLAN.md). Rather
than downgrade a deliberately-pinned, already-verified dependency to fit an
orchestration library, dbt is invoked the same way the Makefile already does:
a plain `dbt build` subprocess call, cwd'd into the transform/ directory. The
trade-off is coarse-grained lineage -- one Dagster asset for the whole dbt
build, not one per dbt model -- which is an acceptable loss for what this
project actually needs from orchestration right now.

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

import subprocess  # nosec B404 -- used only for a fixed dbt-build invocation, see _run_dbt_build below
from pathlib import Path

from dagster import AssetExecutionContext, Definitions, asset

from football_pipeline.pipeline import ingest_current_season

REPO_ROOT = Path(__file__).resolve().parent.parent
TRANSFORM_DIR = REPO_ROOT / "transform"
DBT_EXECUTABLE = REPO_ROOT / ".venv" / "bin" / "dbt"


def _run_dbt_build(context: AssetExecutionContext) -> None:
    args = [str(DBT_EXECUTABLE), "build"]

    result = subprocess.run(  # nosec B603 -- args is built entirely from hardcoded
        # strings (DBT_EXECUTABLE and the literal "build"); no
        # external/untrusted input reaches this call, and shell=True is
        # deliberately not used.
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
    The season itself is discovered live from /competitions on each run,
    not hardcoded -- see ingest_current_season's docstring.
    """
    ingest_current_season()


@asset(deps=[football_data_ingestion], group_name="transform")
def star_schema_build(context: AssetExecutionContext) -> None:
    """The whole dbt project, built once after ingestion."""
    _run_dbt_build(context)


defs = Definitions(assets=[football_data_ingestion, star_schema_build])
