"""DataFrame -> JSON-safe conversion, shared by every backend route.

Confirmed clean for DuckDB's .df() output: a real DuckDB DataFrame's
.to_dict(orient="records") already produces plain Python int/float/None
values -- no numpy scalars (which FastAPI's jsonable_encoder cannot
serialize at all, confirmed: it raises), no pandas.NA sentinels (which
jsonable_encoder silently mis-serializes into a garbage dict, confirmed:
{"__module__": "pandas"} for a bare pd.NA). Verified directly against a
real duckdb.connect(':memory:').execute(...).df() call, not assumed from
pandas' general behavior.

NOT yet verified against BigQuery's to_dataframe() output -- flagged
here rather than assumed safe, same "prove it before you build on it"
discipline this project applies to every other DuckDB-vs-BigQuery
boundary. If a numpy scalar or pd.NA ever surfaces from a BigQuery-backed
route in practice, it will need handling here, in the one place every
route already funnels through -- not as an 11-times-repeated fix.
"""

from typing import cast

import pandas as pd


def records(df: pd.DataFrame) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], df.to_dict(orient="records"))


def record(series: pd.Series) -> dict[str, object]:
    return cast(dict[str, object], series.to_dict())
