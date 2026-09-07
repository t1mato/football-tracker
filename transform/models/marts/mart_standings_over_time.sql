with team_matches as (
    select
        ftm.team_id,
        ftm.competition_code,
        ftm.season_id,
        fm.group_name,
        fm.matchday,
        ftm.goals_for,
        ftm.goals_against,
        case ftm.result
            when 'W' then 3
            when 'D' then 1
            else 0
        end as points
    from {{ ref('fct_team_matches') }} ftm
    inner join {{ ref('fct_matches') }} fm on ftm.match_id = fm.match_id
    where fm.stage in ('{{ var("standings_phase_stages") | join("', '") }}')
      and ftm.result is not null
),

cumulative as (
    select
        team_id,
        competition_code,
        season_id,
        group_name,
        matchday,
        sum(points) over (
            partition by team_id, competition_code, season_id, group_name
            order by matchday
        ) as cumulative_points,
        sum(goals_for - goals_against) over (
            partition by team_id, competition_code, season_id, group_name
            order by matchday
        ) as cumulative_goal_difference,
        sum(goals_for) over (
            partition by team_id, competition_code, season_id, group_name
            order by matchday
        ) as cumulative_goals_for
    from team_matches
)

select
    team_id,
    competition_code,
    season_id,
    group_name,
    matchday,
    cumulative_points,
    cumulative_goal_difference,
    cumulative_goals_for,
    -- Standard football tiebreak order: points, then goal difference, then
    -- goals scored. This mart may legitimately drift from
    -- fct_standings_snapshot's ground truth -- real competitions have
    -- tiebreakers (head-to-head record, disciplinary points) a
    -- reconstruction from match results alone cannot know about.
    rank() over (
        partition by competition_code, season_id, group_name, matchday
        order by cumulative_points desc, cumulative_goal_difference desc, cumulative_goals_for desc
    ) as position
from cumulative
