with matches as (
    select * from {{ ref('fct_matches') }}
),

home_side as (
    select
        match_id,
        competition_code,
        season_id,
        kickoff_date_utc,
        status,
        venue_key,
        home_team_id as team_id,
        away_team_id as opponent_team_id,
        true as is_home,
        full_time_home as goals_for,
        full_time_away as goals_against
    from matches
),

away_side as (
    select
        match_id,
        competition_code,
        season_id,
        kickoff_date_utc,
        status,
        venue_key,
        away_team_id as team_id,
        home_team_id as opponent_team_id,
        false as is_home,
        full_time_away as goals_for,
        full_time_home as goals_against
    from matches
),

unioned as (
    select * from home_side
    union all
    select * from away_side
)

select
    match_id,
    competition_code,
    season_id,
    kickoff_date_utc,
    status,
    venue_key,
    team_id,
    opponent_team_id,
    is_home,
    goals_for,
    goals_against,
    -- Compared from this team's own perspective, not the match's home/away
    -- perspective -- that swap is the entire reason this model exists
    -- instead of every mart reading full_time_home/away off fct_matches
    -- directly.
    case
        when status <> 'FINISHED' then null
        when goals_for > goals_against then 'W'
        when goals_for < goals_against then 'L'
        else 'D'
    end as result
from unioned
