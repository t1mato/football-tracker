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

# Streamlit's console-script entry point does not get the sys.path[0]=''
# (CWD) treatment a `python -c`/`-m` invocation does, and Streamlit's own
# bootstrap only prepends the *page file's own directory*
# (/app/app/pages), never the project root -- so `from app.formatting
# import ...` (a package-relative import used throughout app/pages/*.py)
# has nothing on sys.path with an app/ subdirectory inside it. Confirmed
# live: reproduced with a real Playwright browser hit against the actual
# deployed Cloud Run service (ModuleNotFoundError: No module named
# 'app'), root-caused by reading streamlit's own bootstrap.py source
# inside this exact image, and fixed by explicitly pinning the one
# directory that's always correct regardless of how streamlit invokes
# each script.
ENV PYTHONPATH=/app

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
