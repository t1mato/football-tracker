"""dlt source for football-data.org v4.

Resource bodies are plain generator functions so tests can call them without
dlt's runtime; the `@dlt.resource` wrappers at the bottom are the only dlt
surface.
"""

from collections.abc import Mapping
from typing import Any

from football_pipeline.client import FootballDataClient, NotFoundError

COMPETITIONS: tuple[str, ...] = ("PL", "PD", "BL1", "SA", "FL1", "CL")

# The scorers endpoint defaults to 10 rows and silently truncates -- an
# explicit limit is always sent. Shared so every URL built against it
# produces the same cache key.
SCORERS_LIMIT = 100

_CacheKey = tuple[str, tuple[tuple[str, str], ...]]


class ResponseCache:
    """Fetches each URL at most once per pipeline run.

    Several resources read the same payload -- teams feeds teams, players and
    squad_observations -- and dlt does not guarantee the order resources run
    in. Memoizing here means every resource can ask for what it needs without
    any of them needing to know who else asked.

    A 404 is memoized too: `competitions/CL/standings` 404s all summer before
    the Champions League league phase starts, and more than one resource
    asks for it. Only `NotFoundError` is treated as a durable fact about the
    URL -- every other exception (a timeout, a 500) is transient and must
    propagate uncached so the caller retries it.
    """

    def __init__(self, client: FootballDataClient) -> None:
        self._client = client
        self._responses: dict[_CacheKey, dict[str, Any]] = {}
        self._not_found: dict[_CacheKey, NotFoundError] = {}

    def get(
        self, path: str, params: Mapping[str, str | int] | None = None
    ) -> dict[str, Any]:
        key: _CacheKey = (
            path,
            tuple(sorted((k, str(v)) for k, v in (params or {}).items())),
        )
        if key in self._not_found:
            raise self._not_found[key]
        if key not in self._responses:
            try:
                self._responses[key] = self._client.get(path, params)
            except NotFoundError as exc:
                self._not_found[key] = exc
                raise
        return self._responses[key]
