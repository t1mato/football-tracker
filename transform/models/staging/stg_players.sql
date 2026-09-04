select
    id as player_id,
    team_id,
    name as player_name,
    position,
    cast(date_of_birth as date) as date_of_birth,  -- VARCHAR upstream; 4 are null
    nationality
from {{ source('raw', 'players') }}
