select
    competition_code,
    season_id,
    team_id,
    snapshot_date,
    stage,
    type as table_type,
    "group" as group_name,
    position,
    played_games,
    form,
    won,
    draw,
    lost,
    points,
    goals_for,
    goals_against,
    goal_difference
from {{ source('raw', 'standings') }}
