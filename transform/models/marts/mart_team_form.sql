with results as (
    select
        team_id,
        competition_code,
        kickoff_date_utc,
        result,
        goals_for,
        goals_against,
        row_number() over (
            partition by team_id, competition_code
            order by kickoff_date_utc desc
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
    {{ dbt.listagg("result", "''", "order by kickoff_date_utc asc") }} as last_5_results,
    count(*) filter (where result = 'W') as wins,
    count(*) filter (where result = 'D') as draws,
    count(*) filter (where result = 'L') as losses,
    sum(goals_for) as goals_for,
    sum(goals_against) as goals_against
from last_five
group by team_id, competition_code
