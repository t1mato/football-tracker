with source as (
    select * from {{ source('raw', 'match_weather') }}
)

select
    match_id,
    venue_key,
    -- dlt lands weather_date as VARCHAR; cast once here, not at the call
    -- site, same reasoning as every other date column in this project.
    cast(weather_date as date) as weather_date,
    weather_hour,
    temperature_2m,
    precipitation,
    wind_speed_10m,
    data_type
from source
