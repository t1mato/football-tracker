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
--
-- row_number, not a plain union-dedup: verified 2026-09-04 that no team_id
-- currently carries two different names, but that is a fact about today's
-- data, not a guarantee. A future name drift (rebrand, accent
-- normalisation) would otherwise produce two rows sharing one team_id and
-- break dim_teams' uniqueness -- the same shape of bug dim_players hit from
-- player transfers, fixed the same way: pick one name deterministically
-- rather than let ambiguity become a build failure discovered downstream.
observed_teams as (
    select
        team_id,
        team_name,
        row_number() over (partition by team_id order by team_name) as rn
    from (
        select home_team_id as team_id, home_team_name as team_name from {{ ref('stg_matches') }}
        union
        select away_team_id, away_team_name from {{ ref('stg_matches') }}
        union
        select team_id, team_name from {{ ref('stg_scorers') }}
    )
),

-- stg_teams is a single current-roster snapshot per competition
-- (/competitions/{code}/teams). It never saw a team relegated in an earlier
-- backfilled season, or a Champions League club whose home league isn't one
-- of the six we track (Ajax, Celtic, Young Boys, Kobenhavn, ...). Verified
-- 2026-09-04: 50 distinct teams, every occurrence non-null-named.
--
-- Twin of dim_players.sql's missing_players/derived_players CTEs -- same
-- "left join to find rows the current-snapshot dimension never saw, null
-- out every other column, flag is_derived" shape. Not extracted to a shared
-- macro: this unions two sources with a plain dedup, dim_players unions one
-- source with a transfer-history tiebreak, and forcing one parameterised
-- macro over two genuinely different shapes was judged not worth it for two
-- call sites. If a third one appears, revisit.
--
-- Cross-database types: varchar/bigint/timestamptz are DuckDB spellings.
-- BigQuery has no VARCHAR or TIMESTAMPTZ type name at all, so this used
-- dbt's cross-database type macros instead -- the same discipline CLAUDE.md
-- already requires for date functions.
derived_teams as (
    select
        o.team_id,
        o.team_name,
        cast(null as {{ dbt.type_string() }}) as short_name,
        cast(null as {{ dbt.type_string() }}) as tla,
        cast(null as {{ dbt.type_string() }}) as crest,
        cast(null as {{ dbt.type_string() }}) as address,
        cast(null as {{ dbt.type_string() }}) as website,
        cast(null as {{ dbt.type_bigint() }}) as founded,
        cast(null as {{ dbt.type_string() }}) as club_colors,
        cast(null as {{ dbt.type_string() }}) as venue_name,
        cast(null as {{ dbt.type_bigint() }}) as area_id,
        cast(null as {{ dbt.type_string() }}) as area_name,
        cast(null as {{ dbt.type_string() }}) as area_code,
        cast(null as {{ dbt.type_bigint() }}) as coach_id,
        cast(null as {{ dbt.type_string() }}) as coach_name,
        cast(null as {{ dbt.type_timestamp() }}) as last_updated,
        true as is_derived
    from observed_teams o
    left join teams t on o.team_id = t.team_id
    where t.team_id is null
      and o.rn = 1
)

select * from teams
union all
select * from derived_teams
