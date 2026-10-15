with matches as (
    select * from {{ ref('stg_matches') }}
)

select
    m.match_id,
    m.competition_code,
    m.season_id,
    m.kickoff_utc,
    m.kickoff_date_utc,
    m.kickoff_time_confirmed,
    m.status,
    m.status_raw,
    m.matchday,
    m.stage,
    m.group_name,
    m.last_updated,
    m.home_team_id,
    m.away_team_id,
    m.winner,
    m.duration,
    m.full_time_home,
    m.full_time_away,
    m.half_time_home,
    m.half_time_away
from matches m
