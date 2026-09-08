with matches as (
    select *
    from {{ ref('fct_matches') }}
    where status in ('FINISHED', 'AWARDED')
),

-- Canonical ordering (CLAUDE.md convention): team_a is always the lower
-- id, team_b the higher, so a fixture and its reverse fixture collapse to
-- one row instead of being counted as two different rivalries.
--
-- winner_side is derived from the API's own winner field for EVERY match,
-- not from comparing goals -- the same three-valued-logic trap fixed in
-- fct_team_matches during the Phase 2b review. AWARDED matches have no
-- goals at all, so comparing full_time_home/away for those would silently
-- evaluate to neither true nor false and vanish from every count.
normalised as (
    select
        least(home_team_id, away_team_id) as team_a_id,
        greatest(home_team_id, away_team_id) as team_b_id,
        case when home_team_id < away_team_id then full_time_home else full_time_away end as team_a_goals,
        case when home_team_id < away_team_id then full_time_away else full_time_home end as team_b_goals,
        case
            when winner = 'DRAW' then 'DRAW'
            when (home_team_id < away_team_id and winner = 'HOME_TEAM')
              or (home_team_id > away_team_id and winner = 'AWAY_TEAM') then 'TEAM_A'
            when (home_team_id < away_team_id and winner = 'AWAY_TEAM')
              or (home_team_id > away_team_id and winner = 'HOME_TEAM') then 'TEAM_B'
        end as winner_side
    from matches
)

select
    team_a_id,
    team_b_id,
    count(*) as matches_played,
    cast(sum(case when winner_side = 'TEAM_A' then 1 else 0 end) as {{ dbt.type_bigint() }}) as team_a_wins,
    cast(sum(case when winner_side = 'TEAM_B' then 1 else 0 end) as {{ dbt.type_bigint() }}) as team_b_wins,
    cast(sum(case when winner_side = 'DRAW' then 1 else 0 end) as {{ dbt.type_bigint() }}) as draws,
    cast(coalesce(sum(team_a_goals), 0) as {{ dbt.type_bigint() }}) as team_a_goals,
    cast(coalesce(sum(team_b_goals), 0) as {{ dbt.type_bigint() }}) as team_b_goals
from normalised
group by team_a_id, team_b_id
