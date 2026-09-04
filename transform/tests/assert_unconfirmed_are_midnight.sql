{#
  kickoff_time_confirmed is derived from status; the source also serialises
  an unconfirmed time as exactly 00:00:00Z. This asserts the two signals
  agree, catching a rescheduled fixture that keeps a stale midnight after
  moving to TIMED.

  THIS TEST WILL EVENTUALLY FIRE FOR A BENIGN REASON. The correlation holds
  because all six competitions are European and their kickoffs occupy
  10:00-20:00 UTC, leaving midnight free. Add a non-European competition and
  a real kickoff collides with the placeholder -- an MLS 00:00Z kickoff is an
  ordinary 19:00 ET evening game. If this fails after a competition was
  added, it is a scope change, not a data defect.
#}
select
    match_id,
    kickoff_utc,
    kickoff_time_confirmed,
    kickoff_hour_utc
from {{ ref('stg_matches') }}
where kickoff_time_confirmed = (extract(hour from {{ to_utc_naive('kickoff_utc') }}) = 0
                                and extract(minute from {{ to_utc_naive('kickoff_utc') }}) = 0)
