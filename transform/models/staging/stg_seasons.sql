select
    id as season_id,
    competition_code,
    start_date,
    end_date,
    current_matchday,
    winner_team_id
from {{ source('raw', 'seasons') }}
