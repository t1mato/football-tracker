select
    team_id,
    player_id,
    observed_date,
    position
from {{ source('raw', 'squad_observations') }}
