FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv==0.12.0

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra app

COPY app/ ./app/

# Closes a real silent-failure path: app/queries.py's get_connection()
# falls back to a local DuckDB file when APP_DESTINATION isn't
# "bigquery" -- a file that doesn't exist in this container, and
# duckdb.connect() creates an empty one rather than erroring. Hard-coding
# this here means that fallback path can never be reached by accident,
# the same reasoning as the pipeline Dockerfile's PIPELINE_DESTINATION.
ENV APP_DESTINATION=bigquery

# Streamlit reads $PORT at container start (Cloud Run injects it,
# defaulting to 8080) -- shell form, not exec-form JSON array, so that
# $PORT actually expands. --server.address=0.0.0.0 is required for Cloud
# Run to reach the process at all; --server.headless=true skips
# Streamlit's own "open a browser" prompt, which has nothing to open in a
# container.
CMD /app/.venv/bin/streamlit run app/streamlit_app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true
