select
    id as team_id,
    name as team_name,
    short_name,
    tla,
    crest,
    address,
    website,
    founded,
    club_colors,
    venue_name,
    area_id,
    area_name,
    area_code,
    coach_id,
    coach_name,
    last_updated
from {{ source('raw', 'teams') }}
