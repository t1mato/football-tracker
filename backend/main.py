"""FastAPI app: one connection created at startup, one route per page's
data need, wrapping warehouse.queries the same way app/queries.py's
Streamlit wrapper does -- just with HTTP instead of @st.cache_data as the
calling convention.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from warehouse.queries import DEFAULT_DB_PATH, get_competitions, get_connection


def create_app(db_path: Path = DEFAULT_DB_PATH) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # One connection for the process lifetime -- the FastAPI
        # equivalent of get_connection()'s @st.cache_resource in the
        # Streamlit wrapper. No per-request reconnect.
        app.state.con = get_connection(db_path)
        yield

    app = FastAPI(lifespan=lifespan)

    # Vite's dev server runs on a different origin (localhost:5173) than
    # FastAPI's (localhost:8000) locally -- CORS is only needed for that
    # split-process dev setup. In production, FastAPI serves the built
    # frontend itself (Task 4), so there's no cross-origin request to
    # allow there at all; this stays permissive for local dev only.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/competitions")
    def competitions(request: Request) -> list[dict[str, object]]:
        df = get_competitions(request.app.state.con)
        # pandas-stubs types to_dict(orient="records") as
        # list[dict[Hashable, Any]] -- accurate for an arbitrarily-indexed
        # DataFrame in general, but get_competitions' columns are always
        # str. cast to the shape the route actually returns (and that
        # FastAPI serializes to JSON), same convention as
        # warehouse/queries.py's own cast() usage.
        return cast(list[dict[str, object]], df.to_dict(orient="records"))

    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount(
            "/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets"
        )

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str) -> FileResponse:
            return FileResponse(frontend_dist / "index.html")

    return app


app = create_app()
