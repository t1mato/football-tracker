"""Tests for football_pipeline/pipeline.py's destination selection and CLI modes.

Directly tested here: _destination(), run()'s destination pass-through,
run_weather()'s destination branching, run_transform()/
run_transform_weather()'s dbt-build invocations, and main()'s mode
dispatch. run()'s, run_weather()'s, and build_client()'s actual live
behavior is not -- they make real API calls or read real local secrets,
and are exercised by actually running the pipeline, not by a mocked unit
test. CI never calls a live API (see CLAUDE.md's Testing and CI section).
"""

import subprocess
from pathlib import Path

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
    """--exclude source:raw.match_weather+ excludes the raw.match_weather
    source node, its descendant models (stg_match_weather,
    fct_match_weather), and its two source-attached generic tests --
    weather isn't wired to BigQuery yet, so a plain `dbt build --target
    prod` would fail trying to build/test against an empty raw.match_weather.
    A model-only exclusion (`stg_match_weather+`) was tried first and found,
    via a live run against football-tracker-508022, to miss the two
    source-attached tests entirely (they're upstream siblings, not
    descendants, of the model).
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
        "--exclude", "source:raw.match_weather+",
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


def test_main_ingest_mode_runs_current_season(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "football_pipeline.pipeline.ingest_current_season", lambda: calls.append("ingest")
    )
    monkeypatch.setattr(
        "football_pipeline.pipeline.run_weather", lambda: calls.append("weather")
    )
    monkeypatch.setattr(
        "football_pipeline.pipeline.run_transform", lambda: calls.append("transform")
    )

    from football_pipeline.pipeline import main

    main(["ingest"])

    assert calls == ["ingest"]


def test_main_transform_mode_runs_dbt_build(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr("football_pipeline.pipeline.run", lambda seasons: calls.append("run"))
    monkeypatch.setattr(
        "football_pipeline.pipeline.run_weather", lambda: calls.append("weather")
    )
    monkeypatch.setattr(
        "football_pipeline.pipeline.run_transform", lambda: calls.append("transform")
    )

    from football_pipeline.pipeline import main

    main(["transform"])

    assert calls == ["transform"]


def test_main_weather_mode_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pins the pre-existing "weather" branch so this refactor cannot
    silently drop it.
    """
    calls: list[str] = []
    monkeypatch.setattr("football_pipeline.pipeline.run", lambda seasons: calls.append("run"))
    monkeypatch.setattr(
        "football_pipeline.pipeline.run_weather", lambda: calls.append("weather")
    )
    monkeypatch.setattr(
        "football_pipeline.pipeline.run_transform", lambda: calls.append("transform")
    )

    from football_pipeline.pipeline import main

    main(["weather"])

    assert calls == ["weather"]


def test_main_bare_args_defaults_to_current_season(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pins today's bare `python -m football_pipeline.pipeline` behavior --
    it must keep working identically after this refactor.
    """
    calls: list[str] = []
    monkeypatch.setattr(
        "football_pipeline.pipeline.ingest_current_season", lambda: calls.append("ingest")
    )
    monkeypatch.setattr(
        "football_pipeline.pipeline.run_weather", lambda: calls.append("weather")
    )
    monkeypatch.setattr(
        "football_pipeline.pipeline.run_transform", lambda: calls.append("transform")
    )

    from football_pipeline.pipeline import main

    main([])

    assert calls == ["ingest"]


def test_ingest_current_season_shares_one_client_between_discovery_and_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The whole point of ingest_current_season existing as its own function
    (instead of inlining discover_current_season() at each main() call
    site) is that discovery and the actual ingest run share one
    FootballDataClient -- one token bucket accounting for both calls,
    instead of each getting its own fresh one.
    """
    sentinel_client = object()
    calls: list[object] = []

    monkeypatch.setattr(
        "football_pipeline.pipeline.build_client", lambda: sentinel_client
    )
    monkeypatch.setattr(
        "football_pipeline.pipeline.discover_current_season",
        lambda client: calls.append(("discover", client)) or 2027,
    )
    monkeypatch.setattr(
        "football_pipeline.pipeline.run",
        lambda seasons, client=None: calls.append(("run", seasons, client)),
    )

    from football_pipeline.pipeline import ingest_current_season

    ingest_current_season()

    assert calls == [
        ("discover", sentinel_client),
        ("run", (2027,), sentinel_client),
    ]


def test_main_season_args_still_backfills(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr("football_pipeline.pipeline.run", lambda seasons: calls.append(seasons))
    monkeypatch.setattr(
        "football_pipeline.pipeline.run_weather", lambda: calls.append("weather")
    )
    monkeypatch.setattr(
        "football_pipeline.pipeline.run_transform", lambda: calls.append("transform")
    )

    from football_pipeline.pipeline import main

    main(["2023", "2024"])

    assert calls == [(2023, 2024)]


def test_run_transform_weather_invokes_dbt_build_with_weather_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mirror of test_run_transform_invokes_dbt_build_with_prod_target_and_weather_exclusion,
    but --select instead of --exclude -- this is the second dbt invocation
    in production's now-4-step chain, run only after weather ingestion has
    populated raw.match_weather.
    """
    captured: dict[str, object] = {}

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("football_pipeline.pipeline.subprocess.run", fake_run)

    from football_pipeline.pipeline import DBT_EXECUTABLE, TRANSFORM_DIR, run_transform_weather

    run_transform_weather()

    assert captured["args"] == [
        str(DBT_EXECUTABLE), "build",
        "--target", "prod",
        "--select", "source:raw.match_weather+",
    ]
    kwargs = captured["kwargs"]
    assert kwargs["cwd"] == TRANSFORM_DIR  # type: ignore[index]


def test_run_transform_weather_raises_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr("football_pipeline.pipeline.subprocess.run", fake_run)

    from football_pipeline.pipeline import run_transform_weather

    with pytest.raises(RuntimeError, match="dbt build failed"):
        run_transform_weather()


def test_main_transform_weather_mode_runs_dbt_build(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr("football_pipeline.pipeline.run", lambda seasons: calls.append("run"))
    monkeypatch.setattr(
        "football_pipeline.pipeline.run_weather", lambda: calls.append("weather")
    )
    monkeypatch.setattr(
        "football_pipeline.pipeline.run_transform", lambda: calls.append("transform")
    )
    monkeypatch.setattr(
        "football_pipeline.pipeline.run_transform_weather",
        lambda: calls.append("transform-weather"),
    )

    from football_pipeline.pipeline import main

    main(["transform-weather"])

    assert calls == ["transform-weather"]


def test_run_weather_uses_duckdb_selection_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("PIPELINE_DESTINATION", raising=False)
    calls: list[str] = []

    class FakePipeline:
        def run(self, source: object) -> str:
            return "ran"

    monkeypatch.setattr("football_pipeline.pipeline.dlt.pipeline", lambda **kwargs: FakePipeline())
    monkeypatch.setattr(
        "football_pipeline.pipeline.select_matches_needing_weather",
        lambda db_path: calls.append("duckdb_select") or [],
    )
    monkeypatch.setattr(
        "football_pipeline.pipeline.select_matches_needing_weather_bigquery",
        lambda client: calls.append("bigquery_select") or [],
    )

    from football_pipeline.pipeline import run_weather

    run_weather(db_path=tmp_path / "test.duckdb")

    assert calls == ["duckdb_select"]


def test_run_weather_uses_bigquery_selection_and_destination_when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pins the one behavioral change this task made to run_weather() --
    without this test, reverting the PIPELINE_DESTINATION branch back to
    always calling the DuckDB path would leave the suite green.
    """
    monkeypatch.setenv("PIPELINE_DESTINATION", "bigquery")
    monkeypatch.setenv("GCP_PROJECT", "football-tracker-508022")
    captured_kwargs: dict[str, object] = {}
    calls: list[str] = []

    class FakePipeline:
        def run(self, source: object) -> str:
            return "ran"

    def fake_pipeline(**kwargs: object) -> object:
        captured_kwargs.update(kwargs)
        return FakePipeline()

    monkeypatch.setattr("football_pipeline.pipeline.dlt.pipeline", fake_pipeline)
    monkeypatch.setattr(
        "football_pipeline.pipeline.bigquery.Client", lambda project: object()
    )
    monkeypatch.setattr(
        "football_pipeline.pipeline.select_matches_needing_weather_bigquery",
        lambda client: calls.append("bigquery_select") or [],
    )
    monkeypatch.setattr(
        "football_pipeline.pipeline.select_matches_needing_weather",
        lambda db_path: calls.append("duckdb_select") or [],
    )

    from football_pipeline.pipeline import run_weather

    run_weather()

    assert calls == ["bigquery_select"]
    destination = captured_kwargs["destination"]
    assert destination.destination_name == "bigquery"  # type: ignore[attr-defined]
