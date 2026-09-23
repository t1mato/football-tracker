# Football Statistics Tracker

A full-stack football analytics platform: a rate-limited ELT pipeline ingests
fixtures, results, standings, squads and scorers from six competitions,
models them into a Kimball-style dimensional warehouse, and serves them
through a React + FastAPI app running live on Google Cloud.

Built as a hands-on data engineering project: the emphasis is on the
practices — idempotent loading, rate-limit handling, tested transformations,
serverless orchestration, cross-database portability — rather than on
shipping quickly.

**Live app:** https://app-avejvktoea-uc.a.run.app

## Features

- **Leagues** — a card grid for all six competitions, each opening a table
  (standings), a league-wide position-movement chart, recent results,
  upcoming fixtures, and top scorers/assists
- **Teams** — a grid of teams per league/season, each with recent form,
  fixtures, season stats, its own position-over-time chart, and a
  head-to-head comparison against any other team
- **Players** — a searchable, filterable directory with a bio and full
  scoring history per player

## Architecture

```
football-data.org API ─┐
OpenStreetMap Nominatim ┼─► rate-limited ingestion (dlt)
Open-Meteo ─────────────┘      ingest → transform → weather → transform
                                (4-stage, fail-fast Cloud Workflow, nightly)
                           │
                           ▼
                raw tables in BigQuery (DuckDB locally)
                           │
                           ▼
                dbt: staging (typing/cleaning) → marts (dimensional model)
                           │
                           ▼
        FastAPI (TTL-cached query layer) ──► React + TypeScript (Vite)
```

The warehouse is a Kimball-style dimensional model: 6 conformed dimensions
(competitions, seasons, teams, players, venues, dates) and 5 fact tables
(matches, standings snapshots, scorers, match weather, a team-perspective
unpivot of matches), with 5 derived marts on top for form, streaks,
head-to-head and season-position reconstruction. 168 automated dbt tests
(generic + unit tests with inline fixtures) enforce it.

A few design points worth noting:

- **Standings are snapshotted on every run.** The upstream API exposes only
  the *current* table, so historical league positions exist only because we
  persist them ourselves.
- **The source API serves a rolling window of past seasons.** Older seasons
  eventually become unavailable, so anything not yet ingested is lost
  permanently — which is much of the point of keeping a warehouse.
- **The backend caches query results** (a TTL cache in front of DuckDB/
  BigQuery, keyed on request arguments), cutting production API latency by
  ~90% for repeat reads — see `backend/caching.py`.
- **Production availability is actively monitored**, not assumed: a
  synthetic multi-region uptime check backs a 99%, 30-day-rolling Cloud
  Monitoring SLO, since the app scales to zero and real traffic alone can't
  be relied on for a continuous signal.

## Data Sources

| Source | Auth | Limit | Provides |
|---|---|---|---|
| [football-data.org](https://www.football-data.org) v4 | API token | 10 req/min | competitions, seasons, teams, squads, matches, standings, scorers |
| [OpenStreetMap Nominatim](https://nominatim.org) | none | 1 req/sec | venue geocoding (one-time) |
| [Open-Meteo](https://open-meteo.com) | none | ~10k calls/day | matchday forecast and historical weather |

Competitions covered: Premier League (`PL`), La Liga (`PD`), Bundesliga
(`BL1`), Serie A (`SA`), Ligue 1 (`FL1`), UEFA Champions League (`CL`) —
7,655+ matches backfilled across 4 seasons each.

The 10 requests/minute cap on the free tier is handled by a token-bucket
limiter that reports wait times rather than blocking, and corrects itself
downward from the server's own `Retry-After`/`X-Requests-Available-Minute`
headers.

## Technology Stack

| Layer | Tool |
|---|---|
| Ingestion | Python 3.12, [dlt](https://dlthub.com) |
| Warehouse | DuckDB (local), BigQuery (production) |
| Transformation | dbt-core |
| Orchestration | Dagster (local), Cloud Scheduler + Cloud Workflows + Cloud Run Jobs (production) |
| Backend | FastAPI, TTL-cached query layer |
| Frontend | React, TypeScript, Vite, TanStack Query, Tailwind CSS |
| Infrastructure | Terraform, GCP (Cloud Run, BigQuery, Cloud Monitoring), GitHub Actions CI/CD via Workload Identity Federation (no long-lived keys) |
| Dependencies | uv (Python), npm (frontend) |
| Quality | Ruff, Mypy (strict), Bandit, pytest (279 tests), Vitest |
| CI/CD | GitHub Actions (lint/type-check/test/dbt build on every push), Docker, automatic image build + manual `terraform apply` cutover |

dbt was chosen over BigQuery-native Dataform so the warehouse stays
swappable; cross-database macros are used throughout to keep that true —
the same dbt project runs unchanged against DuckDB locally and BigQuery in
production.

## Project Structure

```
football_pipeline/     Ingestion
  rate_limiter.py         token-bucket limiter (10 req/min)
  client.py                rate-limited HTTP client
  football_data_source.py  dlt source definitions
  venues.py                one-time venue geocoding
  weather_source.py        per-venue weather
  pipeline.py               pipeline entrypoint
transform/              dbt project (staging -> marts, seeds for CI)
orchestration/          Dagster asset definitions (local dev)
warehouse/              connector-agnostic query layer (DuckDB/BigQuery)
backend/                FastAPI app: routers + TTL query cache
frontend/               React + TypeScript app (Vite)
terraform/              GCP infrastructure as code
scripts/                one-off/manual scripts (e.g. latency benchmarking)
tests/                  pytest suite (pipeline, backend, warehouse)
```

Top-level directories are deliberately *not* named `dbt/` or `dagster/`, as
that shadows the installed packages on `sys.path`.

## Getting Started

```bash
uv sync --all-extras                 # install Python deps
uv run pytest                        # run the Python test suite

cd frontend && npm install           # install frontend deps
```

Ingestion requires a free football-data.org API token in
`.dlt/secrets.toml` (gitignored):

```toml
[sources.football_data]
api_token = "your_token_here"
```

Running the app locally (two processes):

```bash
.venv/bin/uvicorn backend.main:app --reload   # FastAPI, localhost:8000
cd frontend && npm run dev                    # Vite, localhost:5173
```

dbt/Dagster targets are in the `Makefile` (`make build`, `make test`,
`make ci`, `make dagster-dev`).

## Additional Documentation

Design notes, the validated behaviour of the upstream APIs, and the phased
roadmap are kept in local working documents (`CLAUDE.md`, `PLAN.md`,
`docs/`) that are intentionally not published to this repository.

## Status

Live in production. Ingestion, transformation, orchestration, and the app
layer are all built and running unattended on a nightly schedule.
