"""Tests for backend/caching.py's cached() decorator -- the FastAPI
equivalent of app/queries.py's @st.cache_data(ttl=600), built on
cachetools.TTLCache instead of Streamlit's own cache primitive.
"""

from backend.caching import cached


class FakeClock:
    """A clock we control, so tests never actually sleep -- same
    convention as football_pipeline/rate_limiter.py's own tests.
    """

    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_a_second_call_with_the_same_args_does_not_recompute() -> None:
    calls: list[int] = []

    @cached(ttl=600)
    def fn(x: int) -> int:
        calls.append(x)
        return x * 2

    assert fn(3) == 6
    assert fn(3) == 6
    assert calls == [3]


def test_different_args_get_independent_cache_entries() -> None:
    calls: list[int] = []

    @cached(ttl=600)
    def fn(x: int) -> int:
        calls.append(x)
        return x * 2

    fn(3)
    fn(4)

    assert calls == [3, 4]


def test_a_leading_underscore_arg_is_excluded_from_the_cache_key() -> None:
    calls: list[int] = []

    @cached(ttl=600)
    def fn(_con: object, x: int) -> int:
        calls.append(x)
        return x * 2

    fn(object(), 3)
    fn(object(), 3)  # a different _con, same real arg -- must still hit cache

    assert calls == [3]


def test_ttl_expiry_triggers_a_real_recompute() -> None:
    clock = FakeClock()
    calls: list[int] = []

    @cached(ttl=600, timer=clock)
    def fn(x: int) -> int:
        calls.append(x)
        return x * 2

    fn(3)
    clock.advance(601)
    fn(3)

    assert calls == [3, 3]


def test_within_ttl_the_cache_still_hits() -> None:
    clock = FakeClock()
    calls: list[int] = []

    @cached(ttl=600, timer=clock)
    def fn(x: int) -> int:
        calls.append(x)
        return x * 2

    fn(3)
    clock.advance(599)
    fn(3)

    assert calls == [3]
