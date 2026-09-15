select
    competition_id,
    competition_code,
    competition_name,
    competition_type,
    area_id,
    area_name,
    emblem,
    area_flag
from {{ ref('stg_competitions') }}
