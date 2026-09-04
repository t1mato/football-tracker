with teams as (
    select
        team_id,
        team_name,
        short_name,
        tla,
        crest,
        address,
        website,
        founded,
        club_colors,
        venue_name,
        area_id,
        area_name,
        area_code,
        coach_id,
        coach_name,
        last_updated,
        false as is_derived
    from {{ ref('stg_teams') }}
),

-- Every team id/name pair any fact table references. stg_standings needs no
-- entry here: verified 2026-09-04, every standings team_id already resolves
-- against stg_teams (0 missing), unlike matches (1,136 home + 1,136 away
-- slots) and scorers (256 rows).
observed_teams as (
    select home_team_id as team_id, home_team_name as team_name from {{ ref('stg_matches') }}
    union
    select away_team_id, away_team_name from {{ ref('stg_matches') }}
    union
    select team_id, team_name from {{ ref('stg_scorers') }}
),

-- stg_teams is a single current-roster snapshot per competition
-- (/competitions/{code}/teams). It never saw a team relegated in an earlier
-- backfilled season, or a Champions League club whose home league isn't one
-- of the six we track (Ajax, Celtic, Young Boys, Kobenhavn, ...). Verified
-- 2026-09-04: 50 distinct teams, every occurrence non-null-named, no team id
-- with two different names -- safe to synthesize a name-only row.
derived_teams as (
    select
        o.team_id,
        o.team_name,
        cast(null as varchar) as short_name,
        cast(null as varchar) as tla,
        cast(null as varchar) as crest,
        cast(null as varchar) as address,
        cast(null as varchar) as website,
        cast(null as bigint) as founded,
        cast(null as varchar) as club_colors,
        cast(null as varchar) as venue_name,
        cast(null as bigint) as area_id,
        cast(null as varchar) as area_name,
        cast(null as varchar) as area_code,
        cast(null as bigint) as coach_id,
        cast(null as varchar) as coach_name,
        cast(null as timestamptz) as last_updated,
        true as is_derived
    from observed_teams o
    left join teams t on o.team_id = t.team_id
    where t.team_id is null
)

select * from teams
union all
select * from derived_teams
