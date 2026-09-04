with venues as (
    select * from {{ ref('stg_venues') }}
),

canonical as (
    select * from {{ ref('venue_canonical') }}
)

select
    -- Hashes the canonical name, not venues.venue_name. A future rename
    -- changes venues.venue_name but not canonical.canonical_venue_name (once
    -- the seed is updated to point the new raw name at the old canonical
    -- value), so venue_key survives the rename and history does not split.
    {{ dbt_utils.generate_surrogate_key(['canonical.canonical_venue_name']) }} as venue_key,
    canonical.canonical_venue_name,
    venues.venue_name,
    venues.area_code,
    venues.country_code,
    venues.latitude,
    venues.longitude,
    venues.capacity,
    venues.needs_review,
    venues.note,
    venues.display_name
from venues
inner join canonical on venues.venue_name = canonical.venue_name
