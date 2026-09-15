select
    id as competition_id,
    code as competition_code,
    name as competition_name,
    type as competition_type,
    area_id,
    area_name,
    emblem,
    area_flag
from {{ source('raw', 'competitions') }}
