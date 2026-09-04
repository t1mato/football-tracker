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
        winner,
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
        winner,
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
    --
    -- Two branches, not one, and neither trusts a value it hasn't checked
    -- for null first:
    --
    -- FINISHED matches must ALSO have non-null scores. Verified 0 such rows
    -- exist today, but goals_for > goals_against and goals_for < goals_against
    -- both evaluate to NULL under three-valued logic when either side is
    -- null, and the old CASE fell through to `else 'D'` -- fabricating a
    -- draw for a match with no recorded score, exactly the "confident,
    -- plausible, wrong" answer this project keeps designing against.
    --
    -- AWARDED matches (forfeited/technically-decided, 3 in the live
    -- warehouse today) have a real outcome but no goals at all -- the API
    -- decides these without a scoreline. Its winner field (HOME_TEAM /
    -- AWAY_TEAM / DRAW) is exactly for this case and was already carried
    -- through fct_matches unused until now. Reframed the same way goals
    -- are: from this team's own is_home perspective, not the match's.
    case
        when status = 'FINISHED' and goals_for is not null and goals_against is not null then
            case
                when goals_for > goals_against then 'W'
                when goals_for < goals_against then 'L'
                else 'D'
            end
        when status = 'AWARDED' and winner is not null then
            case
                when winner = 'DRAW' then 'D'
                when (is_home and winner = 'HOME_TEAM') or (not is_home and winner = 'AWAY_TEAM') then 'W'
                when (is_home and winner = 'AWAY_TEAM') or (not is_home and winner = 'HOME_TEAM') then 'L'
            end
    end as result
from unioned
