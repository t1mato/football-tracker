with results as (
    select
        team_id,
        competition_code,
        match_id,
        kickoff_date_utc,
        result,
        (result = 'W') as is_win,
        (result in ('W', 'D')) as is_unbeaten
    from {{ ref('fct_team_matches') }}
    where result is not null
),

-- The "gaps and islands" pattern: rn_all - rn_<category> stays constant
-- for every consecutive run of the same category value, and changes the
-- moment the category flips. Verified against real data (2026-09-06): a
-- team's actual win/loss/draw sequence produces exactly the island
-- boundaries a manual read of the results confirms.
numbered as (
    select
        *,
        row_number() over (partition by team_id, competition_code order by kickoff_date_utc, match_id) as rn_all,
        row_number() over (partition by team_id, competition_code, is_win order by kickoff_date_utc, match_id) as rn_win,
        row_number() over (partition by team_id, competition_code, is_unbeaten order by kickoff_date_utc, match_id) as rn_unbeaten
    from results
),

islands as (
    select *,
        rn_all - rn_win as win_island,
        rn_all - rn_unbeaten as unbeaten_island
    from numbered
),

win_island_lengths as (
    select team_id, competition_code, win_island, is_win, count(*) as length, max(rn_all) as last_rn
    from islands
    group by team_id, competition_code, win_island, is_win
),

unbeaten_island_lengths as (
    select team_id, competition_code, unbeaten_island, is_unbeaten, count(*) as length, max(rn_all) as last_rn
    from islands
    group by team_id, competition_code, unbeaten_island, is_unbeaten
),

overall_last as (
    select team_id, competition_code, max(rn_all) as last_rn
    from numbered
    group by team_id, competition_code
),

-- current_win/current_unbeaten only produce a row when the LAST island of
-- that category ends exactly at the team's most recent match overall --
-- if the last match broke the streak, no matching row exists here and the
-- final coalesce(...) below reports 0, not the length of a streak that
-- already ended.
current_win as (
    select ol.team_id, ol.competition_code, wil.length as current_win_streak
    from overall_last ol
    inner join win_island_lengths wil
        on ol.team_id = wil.team_id and ol.competition_code = wil.competition_code
       and wil.is_win = true and wil.last_rn = ol.last_rn
),

current_unbeaten as (
    select ol.team_id, ol.competition_code, uil.length as current_unbeaten_streak
    from overall_last ol
    inner join unbeaten_island_lengths uil
        on ol.team_id = uil.team_id and ol.competition_code = uil.competition_code
       and uil.is_unbeaten = true and uil.last_rn = ol.last_rn
),

longest_win as (
    select team_id, competition_code, max(length) as longest_win_streak
    from win_island_lengths
    where is_win
    group by team_id, competition_code
),

longest_unbeaten as (
    select team_id, competition_code, max(length) as longest_unbeaten_streak
    from unbeaten_island_lengths
    where is_unbeaten
    group by team_id, competition_code
),

teams as (
    select distinct team_id, competition_code from results
)

select
    t.team_id,
    t.competition_code,
    coalesce(cw.current_win_streak, 0) as current_win_streak,
    coalesce(cu.current_unbeaten_streak, 0) as current_unbeaten_streak,
    coalesce(lw.longest_win_streak, 0) as longest_win_streak,
    coalesce(lu.longest_unbeaten_streak, 0) as longest_unbeaten_streak
from teams t
left join current_win cw on t.team_id = cw.team_id and t.competition_code = cw.competition_code
left join current_unbeaten cu on t.team_id = cu.team_id and t.competition_code = cu.competition_code
left join longest_win lw on t.team_id = lw.team_id and t.competition_code = lw.competition_code
left join longest_unbeaten lu on t.team_id = lu.team_id and t.competition_code = lu.competition_code
