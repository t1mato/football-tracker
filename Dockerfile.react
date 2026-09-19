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

ENV APP_DESTINATION=bigquery
ENV PYTHONPATH=/app

CMD /app/.venv/bin/uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port $PORT
