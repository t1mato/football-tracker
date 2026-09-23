"""FastAPI app: one connection created at startup, one route per page's
data need, wrapping warehouse.queries the same way app/queries.py's
Streamlit wrapper does -- just with HTTP instead of @st.cache_data as the
calling convention.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, cast

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.queries import (
    DEFAULT_DB_PATH,
    ConnectionLike,
    get_competitions,
    get_connection,
)


def get_con(request: Request) -> ConnectionLike:
    # .cursor() gives each request its own independently-usable handle
    # on the same underlying database/client rather than every
    # concurrent request racing on the one shared app.state.con.
    # DuckDBPyConnection.cursor() is DuckDB's own documented pattern
    # for multi-threaded use; BigQueryConnection.cursor() returns self
    # since the underlying bigquery.Client is already thread-safe for
    # query submission.
    con: ConnectionLike = request.app.state.con
    return con.cursor()


def create_app(
    db_path: Path = DEFAULT_DB_PATH, frontend_dist: Path | None = None
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # One connection for the process lifetime -- the FastAPI
        # equivalent of get_connection()'s @st.cache_resource in the
        # Streamlit wrapper. No per-request reconnect. Route handlers never
        # touch this directly, though -- see get_con() below. FastAPI/
        # anyio runs sync route handlers in a threadpool, so concurrent
        # requests would otherwise share this one connection/cursor
        # simultaneously (measured live: DuckDB .df() intermittently
        # returned None, and .fetchone()-based reads could return another
        # request's row).
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
    def competitions(
        con: Annotated[ConnectionLike, Depends(get_con)],
    ) -> list[dict[str, object]]:
        df = get_competitions(con)
        # pandas-stubs types to_dict(orient="records") as
        # list[dict[Hashable, Any]] -- accurate for an arbitrarily-indexed
        # DataFrame in general, but get_competitions' columns are always
        # str. cast to the shape the route actually returns (and that
        # FastAPI serializes to JSON), same convention as
        # warehouse/queries.py's own cast() usage.
        return cast(list[dict[str, object]], df.to_dict(orient="records"))

    # Import placed here, not at module top, to sidestep the circular
    # import shape this creates (main.py -> routers/leagues.py ->
    # back to main.py for get_con/ConnectionLike): by the time
    # create_app() runs, main.py's own module-level code -- including
    # get_con's definition above -- has already fully executed.
    from backend.routers.leagues import router as leagues_router

    app.include_router(leagues_router)

    from backend.routers.teams import router as teams_router

    app.include_router(teams_router)

    from backend.routers.players import router as players_router

    app.include_router(players_router)

    if frontend_dist is None:
        frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount(
            "/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets"
        )

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str) -> FileResponse:
            # A path under /api/ that reached here matched no route above
            # -- it's genuinely unknown and must 404, not fall through to
            # index.html as if it were a client-side route. Without this,
            # a typo'd or not-yet-registered endpoint silently returns
            # 200 text/html, the frontend's `if (!response.ok)` guard
            # never fires, and response.json() fails opaquely on the `<`
            # character (verified live: GET /api/teams returned 200 HTML
            # before this check existed).
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not Found")
            # Serves any real built file at the dist root directly (e.g.
            # /favicon.svg -- only /assets is mounted above, not the rest
            # of dist/), then falls back to index.html for everything else
            # -- real client-side routes like /teams that have no file on
            # disk at all.
            candidate = frontend_dist / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(frontend_dist / "index.html")

    return app


app = create_app()
