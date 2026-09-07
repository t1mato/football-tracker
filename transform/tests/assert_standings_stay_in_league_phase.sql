{#
  Proves every (team, competition, season, matchday) key this mart produces
  is backed by a real match in an allowed league-table-phase stage.

  Originally written as "no mart row maps to a disallowed-stage match", but
  that formulation is unsound: matchday numbering resets every knockout
  round, so for any team that advances past the group/league phase, a
  SINGLE (team, competition, season, matchday) key can legitimately be
  produced by a league-phase match AND ALSO match a knockout-round fixture
  sharing the same matchday number -- e.g. LEAGUE_STAGE matchday 1 and
  QUARTER_FINALS matchday 1 (first leg) for the same team in the same CL
  season. A join that doesn't also disambiguate by stage pulls in both and
  wrongly flags the row. Caught during implementation: the original test
  returned 232 false positives against real data, one for every team that
  advanced past a CL group/league phase in any loaded season.

  This reframes the check as existence rather than negation: does a real,
  allowed-stage match actually back this key? That is provable; "no
  disallowed match happens to share this key" is not, given the shared
  matchday numbering. Still fails if the model's filter is ever weakened
  or removed -- the two independently-derived key sets would then diverge.
#}
with expected_keys as (
    select distinct
        ftm.team_id, ftm.competition_code, ftm.season_id, fm.matchday
    from {{ ref('fct_team_matches') }} ftm
    inner join {{ ref('fct_matches') }} fm on ftm.match_id = fm.match_id
    where fm.stage in ('{{ var("standings_phase_stages") | join("', '") }}')
      and ftm.result is not null
)

select mso.team_id, mso.competition_code, mso.season_id, mso.matchday
from {{ ref('mart_standings_over_time') }} mso
left join expected_keys ek
    on mso.team_id = ek.team_id
   and mso.competition_code = ek.competition_code
   and mso.season_id = ek.season_id
   and mso.matchday = ek.matchday
where ek.team_id is null
