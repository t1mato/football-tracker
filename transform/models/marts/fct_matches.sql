with matches as (
    select * from {{ ref('stg_matches') }}
),

-- Venue reaches a match through the HOME team, not the match payload itself
-- (football-data.org has no venue field on matches at all -- verified in
-- Phase 0's API probe). This is the known neutral-venue limitation: a
-- Champions League final gets attributed to the home side's ground.
home_team_venue as (
    select team_id, venue_name from {{ ref('dim_teams') }}
),

venues as (
    select venue_key, venue_name from {{ ref('dim_venues') }}
)

select
    m.match_id,
    m.competition_code,
    m.season_id,
    m.kickoff_utc,
    m.kickoff_date_utc,
    m.kickoff_hour_utc,
    m.kickoff_time_confirmed,
    m.status,
    m.status_raw,
    m.matchday,
    m.stage,
    m.group_name,
    m.last_updated,
    m.home_team_id,
    m.away_team_id,
    v.venue_key,
    m.winner,
    m.duration,
    m.full_time_home,
    m.full_time_away,
    m.half_time_home,
    m.half_time_away
from matches m
left join home_team_venue htv on m.home_team_id = htv.team_id
left join venues v on htv.venue_name = v.venue_name
