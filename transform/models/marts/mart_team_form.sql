with results as (
    select
        team_id,
        competition_code,
        match_id,
        kickoff_date_utc,
        result,
        goals_for,
        goals_against,
        row_number() over (
            partition by team_id, competition_code
            order by kickoff_date_utc desc, match_id desc
        ) as recency_rank
    from {{ ref('fct_team_matches') }}
    where result is not null
),

last_five as (
    select * from results where recency_rank <= 5
)

select
    team_id,
    competition_code,
    -- Oldest to newest, left to right -- the convention most football
    -- media form guides use (rightmost letter is the most recent match),
    -- not the recency-ranked order used above to pick the window.
    {{ dbt.listagg("result", "''", "order by kickoff_date_utc asc, match_id asc") }} as last_5_results,
    -- case-when, not filter(where ...): BigQuery has no aggregate FILTER
    -- clause and dbt ships no cross-database macro for it.
    sum(case when result = 'W' then 1 else 0 end) as wins,
    sum(case when result = 'D' then 1 else 0 end) as draws,
    sum(case when result = 'L' then 1 else 0 end) as losses,
    sum(goals_for) as goals_for,
    sum(goals_against) as goals_against
from last_five
group by team_id, competition_code
