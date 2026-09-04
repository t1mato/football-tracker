with source as (
    select * from {{ source('raw', 'matches') }}
),

normalised as (
    select
        id                              as match_id,
        competition_code,
        season_id,
        utc_date                        as kickoff_utc,
        {{ to_utc_naive('utc_date') }}  as kickoff_naive,
        status                          as status_raw,
        matchday,
        stage,
        -- adapter.quote, not "group": double quotes delimit an identifier in
        -- DuckDB but a STRING LITERAL in BigQuery, so the hand-quoted form
        -- compiles there without error and returns the constant 'group' for
        -- every row. Silent, and no test would catch it.
        {{ adapter.quote('group') }}        as group_name,
        last_updated,
        home_team_id,
        home_team_name,
        away_team_id,
        away_team_name,
        winner,
        duration,
        full_time_home,
        full_time_away,
        half_time_home,
        half_time_away
    from source
)

select
    match_id,
    competition_code,
    season_id,
    kickoff_utc,
    cast(kickoff_naive as date) as kickoff_date_utc,

    -- SCHEDULED means "date known, kickoff time not confirmed", and the
    -- source serialises that as exactly 00:00:00Z. Emitting 0 here would
    -- give 1,119 fixtures midnight weather for a 19:00 kickoff, and it
    -- would fail silently: every row joins and every row gets a number.
    case
        when status_raw = 'SCHEDULED' then null
        else extract(hour from kickoff_naive)
    end as kickoff_hour_utc,

    -- Derived from the status, not from the midnight value. "Time not
    -- confirmed" is the source's own contract; midnight is only how it
    -- serialises. assert_unconfirmed_are_midnight checks they agree.
    status_raw <> 'SCHEDULED' as kickoff_time_confirmed,

    case
        when status_raw in ('{{ var("match_statuses") | join("', '") }}')
        then status_raw
        else 'UNKNOWN'
    end as status,

    -- Always populated, never null-when-valid: null is already taken by
    -- "the source emitted null", and the two must stay distinguishable.
    status_raw,

    matchday,
    stage,
    group_name,
    last_updated,
    home_team_id,
    home_team_name,
    away_team_id,
    away_team_name,
    winner,
    duration,
    full_time_home,
    full_time_away,
    half_time_home,
    half_time_away
from normalised
