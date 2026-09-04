select
    id as player_id,
    team_id,
    name as player_name,
    position,
    date_of_birth,
    nationality
from {{ source('raw', 'players') }}
