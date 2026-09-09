"""Tests for football_pipeline/pipeline.py's destination selection.

_destination() is the only piece of pipeline.py tested directly here --
everything else (run(), run_weather(), build_client()) either makes live
API calls or reads real local secrets, and is exercised by actually
running the pipeline (this plan's Task 3), not by a mocked unit test.
CI never calls a live API (see CLAUDE.md's Testing and CI section).
"""

import subprocess

import pytest

from football_pipeline.pipeline import _destination


def test_destination_defaults_to_duckdb_with_no_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PIPELINE_DESTINATION", raising=False)

    assert _destination() == "duckdb"


def test_destination_defaults_to_duckdb_for_any_other_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the exact string "bigquery" switches destinations -- anything
    else (a typo, an unrelated value) must fail safe to the existing
    local behavior, not silently attempt some other destination.
    """
    monkeypatch.setenv("PIPELINE_DESTINATION", "not-a-real-destination")

    assert _destination() == "duckdb"


def test_destination_switches_to_bigquery_when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No project= kwarg is passed -- verified live before this plan was
    written that dlt.destinations.bigquery's real constructor has no
    such parameter; the project resolves entirely through Application
    Default Credentials. destination_name is the stable, dlt-public
    attribute confirmed against the real installed package, not guessed.
    """
    monkeypatch.setenv("PIPELINE_DESTINATION", "bigquery")

    dest = _destination()

    assert dest.destination_name == "bigquery"
    assert dest.config_params.get("location") == "US"


def test_run_passes_destination_through_to_dlt_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pins the one behavioral change this branch made to run() -- without
    this test, reverting destination=_destination() back to the literal
    "duckdb" would leave the entire suite green.
    """
    monkeypatch.setenv("PIPELINE_DESTINATION", "bigquery")
    captured_kwargs: dict[str, object] = {}

    def fake_pipeline(**kwargs: object) -> object:
        captured_kwargs.update(kwargs)

        class FakePipeline:
            def run(self, source: object) -> None:
                return None

        return FakePipeline()

    monkeypatch.setattr("football_pipeline.pipeline.dlt.pipeline", fake_pipeline)
    monkeypatch.setattr("football_pipeline.pipeline.build_client", lambda: object())
    monkeypatch.setattr(
        "football_pipeline.pipeline.football_data_source",
        lambda **kwargs: object(),
    )

    from football_pipeline.pipeline import run

    run((2026,))

    destination = captured_kwargs["destination"]
    assert destination.destination_name == "bigquery"  # type: ignore[attr-defined]


def test_run_transform_invokes_dbt_build_with_prod_target_and_weather_exclusion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--exclude stg_match_weather+ matches star_schema_build's existing
    exclusion in orchestration/definitions.py -- weather isn't wired to
    BigQuery yet, so a plain `dbt build --target prod` would fail trying
    to build stg_match_weather/fct_match_weather against an empty
    raw.match_weather.
    """
    captured: dict[str, object] = {}

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("football_pipeline.pipeline.subprocess.run", fake_run)

    from football_pipeline.pipeline import DBT_EXECUTABLE, TRANSFORM_DIR, run_transform

    run_transform()

    assert captured["args"] == [
        str(DBT_EXECUTABLE), "build",
        "--target", "prod",
        "--exclude", "stg_match_weather+",
    ]
    kwargs = captured["kwargs"]
    assert kwargs["cwd"] == TRANSFORM_DIR  # type: ignore[index]


def test_run_transform_raises_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr("football_pipeline.pipeline.subprocess.run", fake_run)

    from football_pipeline.pipeline import run_transform

    with pytest.raises(RuntimeError, match="dbt build failed"):
        run_transform()
