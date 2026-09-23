import pytest
import streamlit as st

from backend.caching import clear_all_caches


@pytest.fixture(autouse=True)
def _clear_streamlit_data_cache() -> None:
    """Every app/queries.py function is @st.cache_data-decorated, keyed on
    its non-underscore arguments -- and several tests below call the same
    function with the same (competition_code, season_id) etc. against
    different fixture databases (e.g. get_standings(con, "PL", 2502) in
    both test_a_normal_league_phase_returns_the_table_ordered_by_position
    and test_only_the_latest_snapshot_date_is_returned). Without clearing
    the cache between tests, the second test would silently get the
    first's cached result instead of querying its own fixture.
    """
    st.cache_data.clear()


@pytest.fixture(autouse=True)
def _clear_backend_query_cache() -> None:
    """Same reasoning as _clear_streamlit_data_cache above, for
    backend/queries.py's @cached functions -- e.g. test_leagues_router.py
    and test_teams_router.py both exercise get_standings(con, "PL", 2526)
    against their own per-test fixture database.
    """
    clear_all_caches()
