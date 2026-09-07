{#
  Proves the league-phase filter is actually applied to mart_standings_over_time,
  in two ways.

  1. EXISTENCE: every (team, competition, season, matchday) key the mart
     produces is backed by a real match in an allowed league-table-phase
     stage. Originally the only check here, but verified 2026-09-07 to be
     far weaker than its own description implied: of 238 knockout team-rows
     that leak in if the model's filter is removed, this check catches only
     6 of them. matchday numbering resets every knockout round, so 232 of
     the 238 share an identical (team, competition, season, matchday) key
     with a real league-phase match and pass the existence check by
     accident -- the 6 it does catch are caught only because two CL finals
     happen to have matchday 0/null rather than a small positive integer.

  2. CARDINALITY: the mart's total row count must exactly equal the number
     of distinct expected keys. This is what actually catches the 232
     shadowed rows above: a duplicated key produces an EXTRA physical row
     in the mart (the window functions in mart_standings_over_time.sql
     preserve row count; they do not deduplicate), so a row-count mismatch
     means either a missing or an extra row exists somewhere, even where
     the existence check alone cannot see it.

  Together these two checks are what the original comment claimed the
  existence check alone would do. Verified: both counts are 11,478 today.
#}
with expected_keys as (
    select distinct
        ftm.team_id, ftm.competition_code, ftm.season_id, fm.matchday
    from {{ ref('fct_team_matches') }} ftm
    inner join {{ ref('fct_matches') }} fm on ftm.match_id = fm.match_id
    where fm.stage in ('{{ var("standings_phase_stages") | join("', '") }}')
      and ftm.result is not null
),

missing_backing as (
    select mso.team_id, mso.competition_code, mso.season_id, mso.matchday
    from {{ ref('mart_standings_over_time') }} mso
    left join expected_keys ek
        on mso.team_id = ek.team_id
       and mso.competition_code = ek.competition_code
       and mso.season_id = ek.season_id
       and mso.matchday = ek.matchday
    where ek.team_id is null
),

row_count_mismatch as (
    select
        cast(null as {{ dbt.type_bigint() }}) as team_id,
        cast(null as {{ dbt.type_string() }}) as competition_code,
        cast(null as {{ dbt.type_bigint() }}) as season_id,
        cast(null as {{ dbt.type_bigint() }}) as matchday
    from (select count(*) as n from {{ ref('mart_standings_over_time') }}) mart_count
    cross join (select count(*) as n from expected_keys) key_count
    where mart_count.n <> key_count.n
)

select * from missing_backing
union all
select * from row_count_mismatch
