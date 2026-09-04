{#
  Catches a stadium rename landing in the live API before the canonical seed
  is updated to absorb it. dim_venues.venue_key is hashed from
  canonical_venue_name specifically so a rename does not silently split a
  venue's history in two -- but that only works if every raw name football-
  data.org actually reports has a row in the seed. This is the trip wire:
  a raw venue_name with no seed row means either a genuine rename (add a row
  pointing it at the existing canonical value) or a brand new venue (add an
  identity row, same as the rest of venue_canonical.csv).

  Checked against stg_teams, not stg_venues: stg_venues already comes FROM
  the geocoding seed, so it can never disagree with venue_canonical (both
  are static files). stg_teams reflects what the live API reports today.
#}
select distinct t.venue_name
from {{ ref('stg_teams') }} t
left join {{ ref('venue_canonical') }} vc on t.venue_name = vc.venue_name
where t.venue_name is not null
  and vc.venue_name is null
