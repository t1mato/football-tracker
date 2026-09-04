select
    player_id,
    team_id,
    player_name,
    position,
    date_of_birth,
    nationality
from {{ ref('stg_players') }}
