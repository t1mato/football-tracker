FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv==0.12.0

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY football_pipeline/ ./football_pipeline/
COPY transform/ ./transform/

RUN cd transform && /app/.venv/bin/dbt deps

ENTRYPOINT ["/app/.venv/bin/python", "-m", "football_pipeline.pipeline"]
