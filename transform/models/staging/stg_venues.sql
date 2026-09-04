{#
  Reads the committed geocoding cache. needs_review is carried through
  deliberately: two venues (Griffin Park, St Andrew's) have no coordinates
  because football-data.org's venue data is stale for those clubs, not
  because geocoding failed. Downstream joins must be LEFT -- those matches
  will have no weather.
#}
select
    venue_name,
    area_code,
    country_code,
    latitude,
    longitude,
    capacity,
    needs_review,
    note,
    query as search_query,
    display_name
from {{ ref('venues') }}
