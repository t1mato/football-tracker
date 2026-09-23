"""Before/after latency benchmark for backend/caching.py's TTL cache.

Throwaway measurement script, not part of `make test`/CI -- same reasoning
as frontend/vitest.bench.config.ts being kept out of `npm test`: timing
numbers are real but environment-sensitive, and shouldn't be able to fail
a CI run. Run manually:

    .venv/bin/python scripts/backend_cache_benchmark.py
    .venv/bin/python scripts/backend_cache_benchmark.py --url https://app-avejvktoea-uc.a.run.app

With no --url: hits each endpoint through the real FastAPI app (TestClient,
in-process -- no network) against this repo's real backfilled local warehouse
(football_data.duckdb: 161 teams, 3045 players, 7655 matches), not a handful
of synthetic test-fixture rows.

With --url: hits the real deployed Cloud Run service over HTTPS instead --
the DuckDB-vs-BigQuery gap CLAUDE.md flags throughout this project applies
here too: BigQuery's per-query network round-trip is the thing this cache
has the most to win against, unlike DuckDB's in-process reads. A GET to
/api/health first forces Cloud Run to finish any scale-from-zero cold start
(min_instance_count=0, terraform/gcp/main.tf) *before* timing begins, so a
container boot never gets counted as query latency.

Either way: "cold" is each endpoint's first call (before backend/queries.py's
@cached has anything for that key); "warm" is the mean of the following
calls, which all hit the cache.
"""

import argparse
import statistics
import time
from pathlib import Path
from typing import Protocol

import httpx
from fastapi.testclient import TestClient

from backend.main import create_app

WARM_CALLS = 20


class ClientLike(Protocol):
    def get(self, path: str) -> httpx.Response: ...

# (label, path) -- a spread of endpoints from cheap single-table lookups
# to the joins/subqueries get_standings and get_reconstructed_final_standings
# run, using real ids/codes/seasons confirmed present in the local warehouse.
ENDPOINTS = [
    ("GET /api/competitions", "/api/competitions"),
    ("GET /api/leagues/PL/standings", "/api/leagues/PL/standings?season=2502"),
    (
        "GET /api/leagues/PL/reconstructed-standings",
        "/api/leagues/PL/reconstructed-standings?season=2502",
    ),
    ("GET /api/leagues/PL/fixtures", "/api/leagues/PL/fixtures?season=2502"),
    ("GET /api/leagues/PL/scorers", "/api/leagues/PL/scorers?season=2502"),
    ("GET /api/players", "/api/players"),
    ("GET /api/players/32570", "/api/players/32570"),
    ("GET /api/players/32570/scoring-history", "/api/players/32570/scoring-history"),
    ("GET /api/teams/all", "/api/teams/all"),
    ("GET /api/teams/67/form", "/api/teams/67/form"),
    ("GET /api/teams/67/upcoming", "/api/teams/67/upcoming"),
]


def time_call(client: ClientLike, path: str) -> float:
    start = time.perf_counter()
    response = client.get(path)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.raise_for_status()
    return elapsed_ms


def run_benchmark(client: ClientLike) -> list[tuple[str, float, float, float]]:
    rows: list[tuple[str, float, float, float]] = []
    for label, path in ENDPOINTS:
        cold_ms = time_call(client, path)
        warm_ms = [time_call(client, path) for _ in range(WARM_CALLS)]
        warm_mean = statistics.mean(warm_ms)
        speedup = cold_ms / warm_mean if warm_mean else float("inf")
        rows.append((label, cold_ms, warm_mean, speedup))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        help="Base URL of a deployed backend (e.g. the Cloud Run app.status.url) "
        "to benchmark over real HTTPS instead of the local warehouse in-process.",
    )
    args = parser.parse_args()

    if args.url:
        with httpx.Client(base_url=args.url, timeout=30) as client:
            # Absorbs a scale-from-zero cold start before any timing starts --
            # see the module docstring's --url section.
            client.get("/api/health").raise_for_status()
            rows = run_benchmark(client)
    else:
        db_path = Path("football_data.duckdb")
        if not db_path.exists():
            raise SystemExit(f"{db_path} not found -- run this from the repo root.")
        app = create_app(db_path=db_path)
        with TestClient(app) as test_client:
            rows = run_benchmark(test_client)

    total_cold = sum(cold_ms for _, cold_ms, _, _ in rows)
    total_warm_mean = sum(warm_mean for _, _, warm_mean, _ in rows)

    name_width = max(len(label) for label, *_ in rows)
    print(f"{'endpoint':<{name_width}}  {'cold (ms)':>10}  {'warm (ms)':>10}  {'speedup':>8}")
    for label, cold_ms, warm_mean, speedup in rows:
        print(f"{label:<{name_width}}  {cold_ms:10.2f}  {warm_mean:10.2f}  {speedup:7.1f}x")

    reduction_pct = (1 - total_warm_mean / total_cold) * 100 if total_cold else 0.0
    print()
    print(
        f"total cold: {total_cold:.2f} ms   "
        f"total warm (mean of {WARM_CALLS}): {total_warm_mean:.2f} ms"
    )
    print(f"aggregate latency reduction: {reduction_pct:.1f}%")


if __name__ == "__main__":
    main()
