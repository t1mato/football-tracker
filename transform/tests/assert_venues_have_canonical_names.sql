{#
  Catches two different ways a raw venue name can fall out of sync with
  venue_canonical.csv:

  1. A rename landing in the LIVE API before the canonical seed is updated
     to absorb it -- checked against stg_teams.venue_name.
  2. A SEED-MAINTENANCE drift: venues.csv and venue_canonical.csv are two
     independently-maintained files (the geocoding cache and the rename
     ledger), not structurally guaranteed to agree just because they started
     in sync. Someone resolving a needs_review row, or geocoding a newly
     added venue, could update venues.csv without remembering to add the
     matching row to venue_canonical.csv -- checked against
     stg_venues.venue_name.

  Either gap means dim_venues.sql's INNER JOIN to venue_canonical silently
  drops that venue, and any match or team referencing it gets a silent null
  venue_key with no test catching it -- unless this one does.

  dim_venues.venue_key is hashed from canonical_venue_name specifically so a
  rename does not silently split a venue's history in two, but that only
  works if every raw name this project has ever seen has a row in the seed.
  A raw venue_name with no seed row means either a genuine rename (add a row
  pointing it at the existing canonical value) or a brand new venue (add an
  identity row, same as the rest of venue_canonical.csv).
#}
with raw_names as (
    select venue_name from {{ ref('stg_teams') }} where venue_name is not null
    union distinct
    select venue_name from {{ ref('stg_venues') }}
)

select distinct r.venue_name
from raw_names r
left join {{ ref('venue_canonical') }} vc on r.venue_name = vc.venue_name
where vc.venue_name is null
