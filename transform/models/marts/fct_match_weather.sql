with matches as (
    select * from {{ ref('fct_matches') }}
),

weather as (
    select * from {{ ref('stg_match_weather') }}
)

-- One row per match, same grain as fct_matches -- a match with no weather
-- yet (kickoff not confirmed, venue unresolved, or simply not ingested this
-- run) still gets a row with null weather columns, not a dropped row.
-- kickoff_time_confirmed is passed through so a consumer can tell "no
-- weather because the kickoff hour isn't confirmed" apart from the other
-- reasons a row might be missing.
select
    m.match_id,
    m.venue_key,
    m.kickoff_time_confirmed,
    w.weather_date,
    w.weather_hour,
    w.temperature_2m,
    w.precipitation,
    w.wind_speed_10m,
    w.data_type
from matches m
left join weather w on m.match_id = w.match_id
