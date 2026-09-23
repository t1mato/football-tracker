"""TTL cache for warehouse.queries-backed functions -- the FastAPI
equivalent of app/queries.py's @st.cache_data(ttl=600). See
backend/queries.py for where this actually gets applied.

A parameter whose name starts with `_` is excluded from the cache key,
mirroring Streamlit's own cache_data hashing rule and warehouse/queries.py's
existing `_con` convention: the connection differs on every request but
never changes the result, so keying on it would defeat the cache entirely.

Unlike st.cache_data, a cache hit here returns the exact cached object
rather than a defensive deep copy. backend/serialization.py's records()/
record() only ever call .to_dict(), never mutate in place, so a copy would
cost CPU for no corresponding safety win -- and it would eat into the very
latency improvement this cache exists to provide. Callers of a @cached
function must treat its return value as read-only.
"""

import functools
import inspect
import threading
import time
from collections.abc import Callable, Hashable
from typing import ParamSpec, TypeVar, cast

from cachetools import TTLCache

P = ParamSpec("P")
R = TypeVar("R")

_caches: list[TTLCache[tuple[Hashable, ...], object]] = []


def clear_all_caches() -> None:
    """Test-only escape hatch -- see tests/conftest.py's autouse fixture.
    Same reasoning as that fixture's st.cache_data.clear() counterpart:
    without it, two tests calling the same cached function with the same
    real arguments against different fixture databases would silently
    share a stale result.
    """
    for cache in _caches:
        cache.clear()


def cached(
    ttl: float = 600,
    maxsize: int = 512,
    timer: Callable[[], float] = time.monotonic,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        cache: TTLCache[tuple[Hashable, ...], R] = TTLCache(
            maxsize=maxsize, ttl=ttl, timer=timer
        )
        _caches.append(cast("TTLCache[tuple[Hashable, ...], object]", cache))
        lock = threading.Lock()
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            key = tuple(
                cast(Hashable, value)
                for name, value in bound.arguments.items()
                if not name.startswith("_")
            )
            with lock:
                if key in cache:
                    return cache[key]
            result = fn(*args, **kwargs)
            with lock:
                cache[key] = result
            return result

        return wrapper

    return decorator
