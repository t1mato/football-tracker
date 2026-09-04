with matches as (
    select * from {{ ref('stg_matches') }}
),

-- Venue reaches a match through the HOME team, not the match payload itself
-- (football-data.org has no venue field on matches at all -- verified in
-- Phase 0's API probe). This carries two known limitations, not just one:
-- a neutral-venue fixture (a Champions League final) gets attributed to the
-- home side's ground, and -- more broadly -- ANY historical match is
-- attributed to the team's CURRENT ground, because stg_teams is a single
-- current-roster snapshot with no venue-at-match-time data anywhere in the
-- API. A team that moved grounds mid-history has every backfilled match
-- retroactively pointed at the new one. Not fixable with better SQL: the
-- source simply has no venue history to join to.
home_team_venue as (
    select team_id, venue_name from {{ ref('dim_teams') }}
),

-- Resolves through venue_canonical, not by matching dim_teams.venue_name
-- against dim_venues.venue_name directly. dim_venues is deduped to one row
-- per CANONICAL venue (see dim_venues.sql), so its venue_name is only ONE
-- representative raw name among possibly several -- matching against it
-- directly would silently drop any match whose team currently carries a
-- raw name that lost the "representative" slot. venue_canonical maps EVERY
-- raw name dim_teams could report to its canonical value, which is the one
-- lookup this project has for "what venue does this raw name mean."
venue_lookup as (
    select vc.venue_name, dv.venue_key
    from {{ ref('venue_canonical') }} vc
    inner join {{ ref('dim_venues') }} dv on vc.canonical_venue_name = dv.canonical_venue_name
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
    vl.venue_key,
    m.winner,
    m.duration,
    m.full_time_home,
    m.full_time_away,
    m.half_time_home,
    m.half_time_away
from matches m
left join home_team_venue htv on m.home_team_id = htv.team_id
left join venue_lookup vl on htv.venue_name = vl.venue_name
