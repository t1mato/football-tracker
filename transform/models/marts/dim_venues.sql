with venues as (
    select * from {{ ref('stg_venues') }}
),

canonical as (
    select * from {{ ref('venue_canonical') }}
),

-- Every raw venue_name that maps to this canonical venue, joined to its
-- geocoded attributes. Today this is always exactly one row per canonical
-- name (venue_canonical.csv is generated as an identity mapping), but the
-- day a rename is absorbed (two raw names -> one canonical value) this CTE
-- legitimately produces more than one row per canonical_venue_name, and the
-- next step must collapse it back to the dimension's actual grain.
joined as (
    select
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
),

-- dim_venues is one row per CANONICAL venue, not per raw name (see the
-- spec: "1/canonical venue"). Without this, two raw names sharing a
-- canonical value -- exactly the scenario venue_key's design exists for --
-- would emit two rows sharing one venue_key and fail the unique test the
-- day a real rename is absorbed. needs_review asc, venue_name asc is the
-- tiebreak: prefer an already-resolved raw name's coordinates over an
-- unresolved one's, then break ties deterministically by name.
deduped as (
    select *
    from joined
    qualify row_number() over (
        partition by canonical_venue_name
        order by needs_review asc, venue_name asc
    ) = 1
)

select
    {{ dbt_utils.generate_surrogate_key(['canonical_venue_name']) }} as venue_key,
    canonical_venue_name,
    -- The representative raw name, for display only. Do NOT join to this
    -- column to resolve a venue from a team's raw venue_name -- once a
    -- rename lands, an older raw name may no longer be the representative
    -- one here. Resolve through venue_canonical instead (see fct_matches).
    venue_name,
    area_code,
    country_code,
    latitude,
    longitude,
    capacity,
    needs_review,
    note,
    display_name
from deduped
