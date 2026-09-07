"""Query layer for the Streamlit app: a cached read-only DuckDB connection
and one function per page's data need.

Read-only, always -- this project's DuckDB allows one writer or many
readers, never both (see CLAUDE.md). This app must never hold a write lock.
"""

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DEFAULT_DB_PATH = Path("football_data.duckdb")


@st.cache_resource
def get_connection(db_path: Path = DEFAULT_DB_PATH) -> duckdb.DuckDBPyConnection:
    """One read-only connection per Streamlit session, not one per rerun."""
    return duckdb.connect(str(db_path), read_only=True)


def get_competitions(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute("""
        select competition_code, competition_name
        from dim_competitions
        order by competition_name
    """).df()
