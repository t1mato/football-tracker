select
    competition_code,
    season_id,
    team_id,
    cast(snapshot_date as date) as snapshot_date,  -- VARCHAR upstream
    stage,
    type as table_type,
    -- See stg_matches: double quotes are a string literal on BigQuery.
    {{ adapter.quote('group') }} as group_name,
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
