# Football Analytics Data Pipeline

A batch ELT pipeline and analytics app for European football data. Ingests
fixtures, results, standings, squads and scorers from six competitions,
models them into a star schema, and serves dashboards over the result.

Built as a hands-on data engineering project: the emphasis is on the
practices — idempotent loading, rate-limit handling, tested transformations,
asset-based orchestration — rather than on shipping quickly.

## Features

- **Competition Hub** — standings, recent results and upcoming fixtures per league
- **Match Center** — per-match venue and weather detail
- **Team Profile** — season record, form guide, league position over time
- **Top Scorers** — goalscoring leaderboards per competition and season
- **Head-to-Head** — aggregated record between any two teams
- **Cross-League Comparison** — goals per game, competitiveness, home advantage
- **Season Archive** — browse prior seasons retained in the warehouse
- **Streaks & Records** — win and unbeaten runs

## Architecture

```
football-data.org API
  -> rate-limited ingestion (dlt)
     + one-time venue geocoding (Nominatim)
     + per-venue weather over date ranges (Open-Meteo)
  -> raw tables in DuckDB (BigQuery in production)
  -> dbt (staging -> marts, star schema)
  -> Dagster (ingestion + dbt as one asset lineage graph)
  -> Streamlit (reads the warehouse directly)
```

The star schema has dimensions for competitions, seasons, teams, players,
venues and dates, and facts for matches, standings snapshots, scorers and
match weather. Derived marts sit on top for form, streaks, head-to-head and
cross-league comparisons.

Two design points worth noting:

- **Standings are snapshotted on every run.** The upstream API exposes only
  the *current* table, so historical league positions exist only because we
  persist them ourselves.
- **The source API serves a rolling window of past seasons.** Older seasons
  eventually become unavailable, so anything not yet ingested is lost
  permanently — which is much of the point of keeping a warehouse.

## Data Sources

| Source | Auth | Limit | Provides |
|---|---|---|---|
| [football-data.org](https://www.football-data.org) v4 | API token | 10 req/min | competitions, seasons, teams, squads, matches, standings, scorers |
| [OpenStreetMap Nominatim](https://nominatim.org) | none | 1 req/sec | venue geocoding (one-time) |
| [Open-Meteo](https://open-meteo.com) | none | ~10k calls/day | matchday forecast and historical weather |

Competitions covered: Premier League (`PL`), La Liga (`PD`), Bundesliga
(`BL1`), Serie A (`SA`), Ligue 1 (`FL1`), UEFA Champions League (`CL`).

The 10 requests/minute cap on the free tier is handled by a token-bucket
limiter that reports wait times rather than blocking, and reconciles itself
against the server's own `X-Requests-Available-Minute` header.

## Technology Stack

| Layer | Tool |
|---|---|
| Ingestion | Python 3.12, [dlt](https://dlthub.com) |
| Warehouse | DuckDB (local), BigQuery (production) |
| Transformation | dbt-core |
| Orchestration | Dagster |
| App | Streamlit |
| Dependencies | uv |
| Quality | Ruff, Mypy (strict), Bandit, pytest |
| CI/CD | GitHub Actions, Docker, Terraform |

dbt was chosen over BigQuery-native Dataform so the warehouse stays
swappable; cross-database macros are used throughout to keep that true.

## Project Structure

```
football_pipeline/     Ingestion
  rate_limiter.py        token-bucket limiter (10 req/min)
  client.py              rate-limited HTTP client
  football_data_source.py  dlt source definitions
  venues.py              one-time venue geocoding
  weather_source.py      per-venue weather
  pipeline.py            pipeline entrypoint
transform/             dbt project (staging -> marts, seeds for CI)
orchestration/         Dagster asset definitions
app/                   Streamlit multipage app
tests/                 pytest suite
```

Top-level directories are deliberately *not* named `dbt/` or `dagster/`, as
that shadows the installed packages on `sys.path`.

## Getting Started

```bash
uv sync --extra dev                  # install
uv run pytest                        # run tests
```

Ingestion requires a free football-data.org API token in
`.dlt/secrets.toml` (gitignored):

```toml
[sources.football_data]
api_token = "your_token_here"
```

## Additional Documentation

Design notes, the validated behaviour of the upstream API, and the phased
roadmap are kept in local working documents (`CLAUDE.md`, `PLAN.md`) that are
intentionally not published to this repository.

## Status

Early development. Ingestion foundations are in place; transformation,
orchestration and the app layer are not yet built.
