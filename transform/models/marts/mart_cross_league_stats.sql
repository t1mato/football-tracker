with home_side as (
    -- is_home = true selects exactly one row per match out of
    -- fct_team_matches' two (home + away perspective), avoiding double
    -- counting -- margin and total goals are identical from either side,
    -- so which side is picked doesn't matter, only that exactly one is.
    select
        competition_code,
        season_id,
        status,
        result,
        goals_for,
        goals_against
    from {{ ref('fct_team_matches') }}
    where is_home = true
      and status in ('FINISHED', 'AWARDED')
)

select
    competition_code,
    season_id,
    -- case-when, not filter(where ...): BigQuery has no aggregate FILTER
    -- clause and dbt ships no cross-database macro for it.
    cast(sum(case when status = 'FINISHED' then 1 else 0 end) as {{ dbt.type_bigint() }}) as finished_matches,
    -- The true denominator of home_win_rate below (FINISHED + AWARDED,
    -- not FINISHED alone) -- exposed as its own column so a downstream
    -- re-aggregation across seasons can weight home_win_rate correctly.
    -- Verified live: BL1 season 2308 has finished_matches=305 but
    -- home_win_rate's real denominator is 306.
    count(*) as decided_matches,
    -- Goals and margin need a real score, so FINISHED only -- AWARDED
    -- matches have no goals recorded at all (the API decides these
    -- without a scoreline, same reasoning as fct_team_matches.result).
    avg(case when status = 'FINISHED' then goals_for + goals_against end) as avg_goals_per_match,
    -- The competitiveness metric (spec Q4): average absolute goal margin,
    -- not standard deviation of season points -- verified 2026-09-04 that
    -- the current season is 0-8% complete across all six competitions, so
    -- a completion-dependent metric would be blank for the season a
    -- cross-league dashboard most needs to show.
    avg(case when status = 'FINISHED' then abs(goals_for - goals_against) end) as avg_goal_margin,
    -- Outcome-based, not score-based, so AWARDED matches count here too --
    -- fct_team_matches.result already resolved them correctly via the
    -- winner field (fixed in the Phase 2b review).
    avg(case when result = 'W' then 1.0 else 0.0 end) as home_win_rate
from home_side
group by competition_code, season_id
