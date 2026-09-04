select
    team_id,
    player_id,
    cast(observed_date as date) as observed_date,  -- VARCHAR upstream
    position
from {{ source('raw', 'squad_observations') }}
