select
    id as season_id,
    competition_code,
    -- dlt landed these as VARCHAR. DuckDB implicitly casts VARCHAR to DATE
    -- in comparisons and BigQuery does not, so a mart that joins or
    -- datediffs on them would work locally and fail on the swap. Cast once
    -- here, the same way kickoff_date_utc is a real date.
    cast(start_date as date) as start_date,
    cast(end_date as date) as end_date,
    current_matchday,
    winner_team_id
from {{ source('raw', 'seasons') }}
