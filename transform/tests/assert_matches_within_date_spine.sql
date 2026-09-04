{#
  dim_date's range is a hardcoded, generous guess (2020-2030) rather than
  derived from the loaded data, which is the whole point -- a stable
  calendar dimension shouldn't reshape itself every time a new season loads.
  The cost of a static guess is that it can go stale silently: a match
  outside the range would just fail to join to dim_date and look like an
  ordinary missing dimension row. This makes that failure loud instead.
#}
select match_id, kickoff_date_utc
from {{ ref('stg_matches') }}
where kickoff_date_utc < cast('{{ var("date_spine_start") }}' as date)
   or kickoff_date_utc >= cast('{{ var("date_spine_end_exclusive") }}' as date)
