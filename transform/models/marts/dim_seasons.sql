select
    season_id,
    competition_code,
    start_date,
    end_date,
    current_matchday,
    winner_team_id
from {{ ref('stg_seasons') }}
