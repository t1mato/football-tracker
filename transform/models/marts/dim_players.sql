with players as (
    select
        player_id,
        team_id,
        player_name,
        position,
        date_of_birth,
        nationality,
        false as is_derived
    from {{ ref('stg_players') }}
),

-- stg_players comes from the squad embedded in /competitions/{code}/teams --
-- a single CURRENT snapshot per team, same source and same limitation as
-- stg_teams. A scorer from an earlier backfilled season, a since-transferred
-- player, or anyone at a non-domestic Champions League club is absent from
-- it. Discovered the same way dim_teams' gap was: a relationships test on
-- fct_scorers.player_id failed with 526 unresolved rows, 371 distinct
-- players. Verified clean before widening: every occurrence has a non-null
-- name, and no player_id has two different names across scorer rows.
--
-- One player_id can appear at more than one team_id across scorer rows --
-- 172 players transferred during the backfilled window (Marco Asensio:
-- PSG in season 1595, Aston Villa in season 2350). Picking every stg_scorers
-- row verbatim produced duplicate player_ids and broke dim_players'
-- uniqueness. row_number, ordered by season_id desc, keeps one row per
-- player -- their most recent team -- mirroring how stg_players itself is
-- already a single current-snapshot dimension, not a history.
--
-- Twin of dim_teams.sql's observed_teams/derived_teams CTEs -- same shape,
-- not extracted to a shared macro (see the comment there for why).
missing_players as (
    select
        s.player_id,
        s.team_id,
        s.player_name,
        s.season_id,
        row_number() over (
            partition by s.player_id order by s.season_id desc
        ) as rn
    from {{ ref('stg_scorers') }} s
    left join players p on s.player_id = p.player_id
    where p.player_id is null
),

derived_players as (
    select
        player_id,
        team_id,
        player_name,
        -- varchar is a DuckDB spelling BigQuery doesn't have; dbt.type_string()
        -- is portable. date needs no such treatment -- it's an identical
        -- native type on both warehouses.
        cast(null as {{ dbt.type_string() }}) as position,
        cast(null as date) as date_of_birth,
        cast(null as {{ dbt.type_string() }}) as nationality,
        true as is_derived
    from missing_players
    where rn = 1
)

select * from players
union all
select * from derived_players
