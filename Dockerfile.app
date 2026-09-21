FROM node:22-slim AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv==0.12.0

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra backend

COPY warehouse/ ./warehouse/
COPY backend/ ./backend/
COPY --from=frontend-build /frontend/dist ./frontend/dist

# Closes a real silent-failure path: warehouse/queries.py's
# get_connection() falls back to a local DuckDB file when APP_DESTINATION
# isn't "bigquery" -- a file that doesn't exist in this container, and
# duckdb.connect() creates an empty one rather than erroring. Hard-coding
# this here means that fallback path can never be reached by accident,
# same reasoning as the pipeline Dockerfile's PIPELINE_DESTINATION.
ENV APP_DESTINATION=bigquery

# warehouse/ and backend/ aren't in the hatch wheel's `packages` list (see
# pyproject.toml), so `uv sync`'s install doesn't put them anywhere on
# site-packages. Pinning this explicitly means `backend.main`'s own
# imports (`from warehouse.queries import ...`) resolve regardless of how
# uvicorn is invoked or what its own working directory assumptions are.
ENV PYTHONPATH=/app

# uvicorn reads $PORT at container start (Cloud Run injects it,
# defaulting to 8080) -- shell form, not exec-form JSON array, so that
# $PORT actually expands. --host 0.0.0.0 is required for Cloud Run to
# reach the process at all; without it uvicorn binds to localhost only
# and every request from outside the container is refused.
CMD /app/.venv/bin/uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port $PORT
