select
    competition_code,
    season_id,
    player_id,
    player_name,
    team_id,
    team_name,
    played_matches,
    goals,
    assists,
    penalties
from {{ ref('stg_scorers') }}
