import pytest

from backend.caching import clear_all_caches


@pytest.fixture(autouse=True)
def _clear_backend_query_cache() -> None:
    """Every backend/queries.py @cached function is keyed on its
    non-underscore arguments, so tests sharing arguments across different
    fixture databases would otherwise see each other's cached results -- e.g. test_leagues_router.py
    and test_teams_router.py both exercise get_standings(con, "PL", 2526)
    against their own per-test fixture database.
    """
    clear_all_caches()
