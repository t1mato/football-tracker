"""Tests for the football-data.org dlt source. No test opens a socket."""

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import responses

from football_pipeline.client import FootballDataClient, NotFoundError
from football_pipeline.football_data_source import (
    ResponseCache,
    football_data_source,
    iter_competitions,
    iter_matches,
    iter_players,
    iter_scorers,
    iter_seasons,
    iter_squad_observations,
    iter_standings,
    iter_teams,
)
from football_pipeline.rate_limiter import RateLimiter

BASE_URL = "https://api.football-data.org/v4"
FIXTURES = Path(__file__).parent / "fixtures"


def make_client() -> FootballDataClient:
    """A client whose limiter never makes a test wait."""
    return FootballDataClient(
        api_token="test-token",
        limiter=RateLimiter(capacity=10, per_seconds=60, clock=lambda: 0.0),
        sleep=lambda seconds: None,
    )


@responses.activate
def test_the_cache_fetches_each_url_once_however_many_resources_ask() -> None:
    """teams, players and squad_observations all read one teams payload.

    dlt does not guarantee resource order, so correctness cannot depend on
    which resource asks first -- only that the request happens once.
    """
    responses.get(f"{BASE_URL}/competitions/PL/teams", json={"teams": []}, status=200)

    cache = ResponseCache(make_client())
    first = cache.get("competitions/PL/teams")
    second = cache.get("competitions/PL/teams")

    assert first is second
    assert len(responses.calls) == 1


@responses.activate
def test_a_404_is_remembered_so_the_same_dead_url_is_not_refetched() -> None:
    """CL standings 404 all summer, and two resources both ask for them.

    Only NotFoundError is cached: a 404 is a fact about the URL, while a
    timeout or a 500 is transient and must be retried.
    """
    responses.get(f"{BASE_URL}/competitions/CL/standings", json={}, status=404)

    cache = ResponseCache(make_client())

    with pytest.raises(NotFoundError):
        cache.get("competitions/CL/standings")
    with pytest.raises(NotFoundError):
        cache.get("competitions/CL/standings")

    assert len(responses.calls) == 1


COMPETITIONS_PAYLOAD = {
    "count": 3,
    "competitions": [
        {
            "id": 2021, "code": "PL", "name": "Premier League", "type": "LEAGUE",
            "area": {"id": 2072, "name": "England", "code": "ENG"},
            "currentSeason": {
                "id": 2502, "startDate": "2026-08-21", "endDate": "2027-05-30",
                "currentMatchday": 3, "winner": None,
            },
            "numberOfAvailableSeasons": 128,
        },
        {
            "id": 2001, "code": "CL", "name": "UEFA Champions League", "type": "CUP",
            "area": {"id": 2077, "name": "Europe"},
            "currentSeason": {
                "id": 2557, "startDate": "2026-09-08", "endDate": "2027-01-27",
                "currentMatchday": 1, "winner": None,
            },
            "numberOfAvailableSeasons": 47,
        },
        {
            "id": 2013, "code": "BSA", "name": "Serie A Brazil", "type": "LEAGUE",
            "area": {"id": 2032, "name": "Brazil"},
            "currentSeason": {
                "id": 2000, "startDate": "2026-01-01", "endDate": "2026-12-01",
                "currentMatchday": 1, "winner": None,
            },
            "numberOfAvailableSeasons": 10,
        },
    ],
}


@responses.activate
def test_competitions_keeps_only_the_six_we_track() -> None:
    """The endpoint returns all 13 free-tier competitions; we want six."""
    responses.get(f"{BASE_URL}/competitions", json=COMPETITIONS_PAYLOAD, status=200)

    rows = list(iter_competitions(ResponseCache(make_client())))

    assert [r["code"] for r in rows] == ["PL", "CL"]
    assert rows[0]["id"] == 2021
    assert rows[0]["area_name"] == "England"


@responses.activate
def test_competitions_does_not_carry_number_of_available_seasons() -> None:
    """It advertises total history (PL claims 128), not free-tier access.

    Keeping it invites someone to build a backfill loop on it that would fire
    hundreds of requests returning 403.
    """
    responses.get(f"{BASE_URL}/competitions", json=COMPETITIONS_PAYLOAD, status=200)

    rows = list(iter_competitions(ResponseCache(make_client())))

    assert "numberOfAvailableSeasons" not in rows[0]
    assert "number_of_available_seasons" not in rows[0]


def teams_payload(*teams: dict[str, Any]) -> dict[str, Any]:
    return {"count": len(teams), "teams": list(teams)}


ARSENAL = {
    "id": 57, "name": "Arsenal FC", "shortName": "Arsenal", "tla": "ARS",
    "crest": "https://crests.football-data.org/57.png",
    "address": "75 Drayton Park London N5 1BU",
    "website": "http://www.arsenal.com", "founded": 1886,
    "clubColors": "Red / White", "venue": "Emirates Stadium",
    "area": {"id": 2072, "name": "England", "code": "ENG"},
    "coach": {"id": 11605, "name": "Mikel Arteta", "nationality": "Spain"},
    "runningCompetitions": [{"id": 2021, "code": "PL", "name": "Premier League"}],
    "staff": [],
    "squad": [
        {"id": 3189, "name": "Kepa Arrizabalaga", "position": "Goalkeeper",
         "dateOfBirth": "1994-10-03", "nationality": "Spain"},
        {"id": 3319, "name": "Bukayo Saka", "position": "Offence",
         "dateOfBirth": "2001-09-05", "nationality": "England"},
    ],
    "lastUpdated": "2026-09-02T00:20:34Z",
}

CHELSEA = {
    "id": 61, "name": "Chelsea FC", "shortName": "Chelsea", "tla": "CHE",
    "crest": "https://crests.football-data.org/61.png",
    "address": "Fulham Road London SW6 1HS",
    "website": "http://www.chelseafc.com", "founded": 1905,
    "clubColors": "Royal Blue / White", "venue": "Stamford Bridge",
    "area": {"id": 2072, "name": "England", "code": "ENG"},
    "coach": {"id": 12456, "name": "Enzo Maresca", "nationality": "Italy"},
    "runningCompetitions": [{"id": 2021, "code": "PL", "name": "Premier League"}],
    "staff": [],
    "squad": [
        {"id": 4321, "name": "Robert Sanchez", "position": "Goalkeeper",
         "dateOfBirth": "1997-11-18", "nationality": "Spain"},
        {"id": 5432, "name": "Cole Palmer", "position": "Offence",
         "dateOfBirth": "2002-05-06", "nationality": "England"},
    ],
    "lastUpdated": "2026-09-02T00:20:34Z",
}


@responses.activate
def test_teams_carries_venue_and_coach_but_not_nested_lists() -> None:
    """runningCompetitions and squad would become dlt child tables keyed on
    _dlt_root_id -- dlt internals leaking into every dbt model downstream.
    """
    for code in ("PL", "CL"):
        responses.get(f"{BASE_URL}/competitions/{code}/teams",
                      json=teams_payload(ARSENAL), status=200)

    rows = list(iter_teams(ResponseCache(make_client()), codes=("PL", "CL")))

    assert rows[0]["venue_name"] == "Emirates Stadium"
    assert rows[0]["area_code"] == "ENG"
    assert rows[0]["coach_name"] == "Mikel Arteta"
    assert "squad" not in rows[0]
    assert "runningCompetitions" not in rows[0]
    assert "staff" not in rows[0]


@responses.activate
def test_teams_in_two_competitions_yield_one_row_per_appearance() -> None:
    """Arsenal is in PL and CL. Merge on id collapses them; the resource does
    not deduplicate, because dlt's merge is what makes that idempotent.
    """
    for code in ("PL", "CL"):
        responses.get(f"{BASE_URL}/competitions/{code}/teams",
                      json=teams_payload(ARSENAL), status=200)

    rows = list(iter_teams(ResponseCache(make_client()), codes=("PL", "CL")))

    assert len(rows) == 2
    assert {r["id"] for r in rows} == {57}


@responses.activate
def test_a_404_outside_standings_propagates_as_an_error() -> None:
    """Only standings may read a 404 as "no data yet". A 404 on teams means a
    bad competition code -- a bug that must fail the run loudly rather than
    silently producing an empty table.
    """
    responses.get(f"{BASE_URL}/competitions/XX/teams", json={}, status=404)

    with pytest.raises(NotFoundError):
        list(iter_teams(ResponseCache(make_client()), codes=("XX",)))


@responses.activate
def test_players_carry_the_team_id_of_the_squad_that_embedded_them() -> None:
    """The squad payload has no team_id; without injecting it here, dbt would
    have to recover the link from dlt's _dlt_root_id.

    Two teams are used deliberately: a single-team fixture cannot distinguish
    "the enclosing team's id" from a hardcoded constant equal to that one
    team's id. Asserting on (team_id, player_id) pairs across two distinct
    squads is what actually proves team_id follows its own team.
    """
    responses.get(f"{BASE_URL}/competitions/PL/teams",
                  json=teams_payload(ARSENAL, CHELSEA), status=200)

    rows = list(iter_players(ResponseCache(make_client()), codes=("PL",)))

    assert {(r["team_id"], r["id"]) for r in rows} == {
        (57, 3189), (57, 3319), (61, 4321), (61, 5432),
    }
    assert rows[0]["position"] == "Goalkeeper"
    assert rows[0]["date_of_birth"] == "1994-10-03"


@responses.activate
def test_squad_observations_are_stamped_with_the_given_utc_date() -> None:
    """observed_date is injected, never read from the clock in here, so the
    UTC rule is testable rather than a matter of trust.

    Two teams, for the same reason as the players test: proving team_id
    tracks its own squad rather than a hardcoded single-team value.
    """
    responses.get(f"{BASE_URL}/competitions/PL/teams",
                  json=teams_payload(ARSENAL, CHELSEA), status=200)

    rows = list(iter_squad_observations(
        ResponseCache(make_client()), observed_on=date(2026, 9, 3), codes=("PL",)
    ))

    assert len(rows) == 4
    assert {r["observed_date"] for r in rows} == {"2026-09-03"}
    assert {(r["team_id"], r["player_id"]) for r in rows} == {
        (57, 3189), (57, 3319), (61, 4321), (61, 5432),
    }


@responses.activate
def test_players_and_observations_share_one_teams_request() -> None:
    """Both read the same payload; the run budget assumes one request."""
    responses.get(f"{BASE_URL}/competitions/PL/teams",
                  json=teams_payload(ARSENAL, CHELSEA), status=200)
    cache = ResponseCache(make_client())

    list(iter_players(cache, codes=("PL",)))
    list(iter_squad_observations(cache, observed_on=date(2026, 9, 3), codes=("PL",)))
    list(iter_teams(cache, codes=("PL",)))

    assert len(responses.calls) == 1


@pytest.fixture
def pl_matches() -> dict[str, Any]:
    """The committed fixture: 12 real matches including 4 defective statuses."""
    with open(FIXTURES / "pl_matches.json") as f:
        payload: dict[str, Any] = json.load(f)
    return payload


@responses.activate
def test_matches_flatten_teams_and_scores(pl_matches: dict[str, Any]) -> None:
    responses.get(f"{BASE_URL}/competitions/PL/matches",
                  json=pl_matches, status=200)

    rows = list(iter_matches(ResponseCache(make_client()),
                             seasons=(2026,), codes=("PL",)))

    assert len(rows) == 12
    finished = next(r for r in rows if r["status"] == "FINISHED")
    assert finished["home_team_id"] > 0
    assert finished["full_time_home"] is not None
    assert finished["competition_code"] == "PL"


@responses.activate
def test_matches_preserve_defective_status_strings_verbatim(
    pl_matches: dict[str, Any],
) -> None:
    """4 of 380 PL matches return a timestamp where the status enum belongs.

    Raw keeps the raw string. Coercing to UNKNOWN is dbt staging's job, and
    it cannot be tested there if ingestion has already sanitised it away.
    """
    responses.get(f"{BASE_URL}/competitions/PL/matches",
                  json=pl_matches, status=200)

    rows = list(iter_matches(ResponseCache(make_client()),
                             seasons=(2026,), codes=("PL",)))

    defective = [r for r in rows if r["id"] in {560585, 560590, 560612, 560628}]
    assert len(defective) == 4
    assert all(r["status"].endswith("Z") for r in defective)


@responses.activate
def test_matches_request_one_url_per_competition_season(
    pl_matches: dict[str, Any],
) -> None:
    for _season in (2024, 2025):
        responses.get(f"{BASE_URL}/competitions/PL/matches",
                      json=pl_matches, status=200)

    list(iter_matches(ResponseCache(make_client()),
                      seasons=(2024, 2025), codes=("PL",)))

    assert len(responses.calls) == 2
    assert {c.request.params["season"] for c in responses.calls} == {"2024", "2025"}


STANDINGS_PAYLOAD = {
    "filters": {"season": "2026"},
    "competition": {"id": 2021, "code": "PL", "name": "Premier League"},
    "season": {"id": 2502, "startDate": "2026-08-21", "endDate": "2027-05-30",
               "currentMatchday": 3, "winner": None},
    "standings": [{
        "stage": "REGULAR_SEASON", "type": "TOTAL", "group": None,
        "table": [{
            "position": 1, "team": {"id": 57, "name": "Arsenal FC"},
            "playedGames": 3, "form": "W,W,W", "won": 3, "draw": 0, "lost": 0,
            "points": 9, "goalsFor": 7, "goalsAgainst": 1, "goalDifference": 6,
        }],
    }],
}


@responses.activate
def test_standings_yield_nothing_when_the_league_phase_has_not_started() -> None:
    """CL standings 404 every summer. That means "no data yet", not failure --
    if this raised, the whole nightly run would die from June to September.
    """
    responses.get(f"{BASE_URL}/competitions/CL/standings", json={}, status=404)

    rows = list(iter_standings(ResponseCache(make_client()),
                               snapshot_on=date(2026, 9, 3), codes=("CL",)))

    assert rows == []


@responses.activate
def test_standings_stamp_every_row_with_the_snapshot_date() -> None:
    """football-data.org exposes only the current table, so this history exists
    only because we snapshot it ourselves.
    """
    responses.get(f"{BASE_URL}/competitions/PL/standings",
                  json=STANDINGS_PAYLOAD, status=200)

    rows = list(iter_standings(ResponseCache(make_client()),
                               snapshot_on=date(2026, 9, 3), codes=("PL",)))

    assert len(rows) == 1
    assert rows[0]["snapshot_date"] == "2026-09-03"
    assert rows[0]["team_id"] == 57
    assert rows[0]["position"] == 1
    assert rows[0]["points"] == 9
    assert rows[0]["season_id"] == 2502
    assert rows[0]["competition_code"] == "PL"


@responses.activate
def test_standings_rerun_on_the_same_day_produces_identical_rows() -> None:
    """The merge key is (competition, season, team, snapshot_date). Identical
    rows are what makes a retried run idempotent rather than duplicating.
    """
    responses.get(f"{BASE_URL}/competitions/PL/standings",
                  json=STANDINGS_PAYLOAD, status=200)
    cache = ResponseCache(make_client())

    first = list(iter_standings(cache, snapshot_on=date(2026, 9, 3), codes=("PL",)))
    second = list(iter_standings(cache, snapshot_on=date(2026, 9, 3), codes=("PL",)))

    assert first == second


SCORERS_PAYLOAD = {
    "count": 1,
    "filters": {"season": "2026", "limit": 100},
    "competition": {"id": 2021, "code": "PL", "name": "Premier League"},
    "season": {"id": 2502, "startDate": "2026-08-21", "endDate": "2027-05-30",
               "currentMatchday": 3, "winner": None},
    "scorers": [{
        "player": {"id": 3257, "name": "Bruno Fernandes", "position": "Midfield",
                   "dateOfBirth": "1994-09-08", "nationality": "Portugal"},
        "team": {"id": 66, "name": "Manchester United FC"},
        "playedMatches": 2, "goals": 3, "assists": 1, "penalties": 1,
    }],
}


@responses.activate
def test_scorers_always_request_an_explicit_limit() -> None:
    """The endpoint defaults to 10 rows and silently truncates. ?limit=100
    returned all 49 in the probe.
    """
    responses.get(f"{BASE_URL}/competitions/PL/scorers",
                  json=SCORERS_PAYLOAD, status=200)

    list(iter_scorers(ResponseCache(make_client()), seasons=(2026,), codes=("PL",)))

    assert responses.calls[0].request.params["limit"] == "100"


@responses.activate
def test_scorers_key_on_competition_season_and_player() -> None:
    """Merged, never replaced: a current-season run must not delete the
    backfilled seasons, which a full refresh would do nightly.
    """
    responses.get(f"{BASE_URL}/competitions/PL/scorers",
                  json=SCORERS_PAYLOAD, status=200)

    rows = list(iter_scorers(ResponseCache(make_client()),
                             seasons=(2026,), codes=("PL",)))

    assert len(rows) == 1
    assert rows[0]["competition_code"] == "PL"
    assert rows[0]["season_id"] == 2502
    assert rows[0]["player_id"] == 3257
    assert rows[0]["goals"] == 3
    assert rows[0]["team_id"] == 66


# Every season id in COMPETITIONS_PAYLOAD, SCORERS_PAYLOAD, STANDINGS_PAYLOAD
# and pl_matches.json happens to be 2502 -- the current season. A payload with
# a *different* embedded per-match season id is needed to prove seasons are
# actually harvested from individual matches, not just the /competitions
# envelope (which alone would satisfy a much weaker assertion).
HISTORICAL_PL_MATCHES = {
    "filters": {"season": "2024"},
    "resultSet": {"count": 1, "first": "2024-08-16", "last": "2024-08-16", "played": 1},
    "competition": {
        "id": 2021, "name": "Premier League", "code": "PL", "type": "LEAGUE",
        "emblem": "https://crests.football-data.org/PL.png",
    },
    "matches": [
        {
            "id": 460001,
            "utcDate": "2024-08-16T19:00:00Z",
            "status": "FINISHED",
            "matchday": 1,
            "stage": "REGULAR_SEASON",
            "group": None,
            "lastUpdated": "2024-08-17T00:20:34Z",
            "season": {
                "id": 2401, "startDate": "2024-08-16", "endDate": "2025-05-25",
                "currentMatchday": 38, "winner": None,
            },
            "homeTeam": {"id": 57, "name": "Arsenal FC"},
            "awayTeam": {"id": 61, "name": "Chelsea FC"},
            "score": {
                "winner": "HOME_TEAM", "duration": "REGULAR",
                "fullTime": {"home": 2, "away": 0},
                "halfTime": {"home": 1, "away": 0},
            },
        },
    ],
}


@responses.activate
def test_seasons_include_historical_ones_from_the_matches_payload() -> None:
    """Deriving seasons from /competitions alone yields only the current one.

    Every backfilled match would then join to a missing season and the Season
    Archive page would have nothing to browse. HISTORICAL_PL_MATCHES carries a
    season id (2401) that appears nowhere except the embedded per-match season
    object, so this fails unless that object is actually harvested.
    """
    responses.get(f"{BASE_URL}/competitions", json=COMPETITIONS_PAYLOAD, status=200)
    responses.get(f"{BASE_URL}/competitions/PL/matches",
                  json=HISTORICAL_PL_MATCHES, status=200)
    responses.get(f"{BASE_URL}/competitions/PL/scorers", json=SCORERS_PAYLOAD, status=200)
    responses.get(f"{BASE_URL}/competitions/PL/standings",
                  json=STANDINGS_PAYLOAD, status=200)

    rows = list(iter_seasons(ResponseCache(make_client()),
                             seasons=(2026,), codes=("PL",)))

    ids = {r["id"] for r in rows}
    assert 2502 in ids
    assert 2401 in ids
    assert all(r["start_date"] for r in rows)


@responses.activate
def test_seasons_are_deduplicated_by_id(pl_matches: dict[str, Any]) -> None:
    """The same season object appears in several envelopes; one row each."""
    responses.get(f"{BASE_URL}/competitions", json=COMPETITIONS_PAYLOAD, status=200)
    responses.get(f"{BASE_URL}/competitions/PL/matches", json=pl_matches, status=200)
    responses.get(f"{BASE_URL}/competitions/PL/scorers", json=SCORERS_PAYLOAD, status=200)
    responses.get(f"{BASE_URL}/competitions/PL/standings",
                  json=STANDINGS_PAYLOAD, status=200)

    rows = list(iter_seasons(ResponseCache(make_client()),
                             seasons=(2026,), codes=("PL",)))

    assert len(rows) == len({r["id"] for r in rows})


@responses.activate
def test_seasons_tolerate_a_competition_with_no_standings_yet(
    pl_matches: dict[str, Any],
) -> None:
    """CL standings 404 in the summer; harvesting must not die with it."""
    responses.get(f"{BASE_URL}/competitions", json=COMPETITIONS_PAYLOAD, status=200)
    responses.get(f"{BASE_URL}/competitions/CL/matches", json=pl_matches, status=200)
    responses.get(f"{BASE_URL}/competitions/CL/scorers", json=SCORERS_PAYLOAD, status=200)
    responses.get(f"{BASE_URL}/competitions/CL/standings", json={}, status=404)

    rows = list(iter_seasons(ResponseCache(make_client()),
                             seasons=(2026,), codes=("CL",)))

    assert rows


@responses.activate
def test_all_resources_route_through_one_client_and_limiter() -> None:
    """teams, players and squad_observations read the same teams payload.

    Three requests here would mean three caches, and in a real run three
    independent token buckets against one shared 10 req/min server cap --
    which is a guaranteed 429. Counting requests is the only way this is
    observable from outside.

    Also asserts the source's run_date wiring: only the bare iter_* functions
    are exercised with an injected date elsewhere, so replacing the source's
    `run_date` wiring into squad_observations with date.today() (local time,
    not UTC) would break no test without this.
    """
    responses.get(f"{BASE_URL}/competitions/PL/teams",
                  json=teams_payload(ARSENAL), status=200)

    source = football_data_source(client=make_client(), seasons=(2026,),
                                  run_date=date(2026, 9, 3), codes=("PL",))
    rows = {name: list(source.resources[name]) for name in
            ("teams", "players", "squad_observations")}

    assert len(responses.calls) == 1
    assert {r["observed_date"] for r in rows["squad_observations"]} == {"2026-09-03"}


@responses.activate
def test_the_source_exposes_all_eight_resources() -> None:
    source = football_data_source(client=make_client(), seasons=(2026,),
                                  run_date=date(2026, 9, 3))

    assert set(source.resources) == {
        "competitions", "seasons", "teams", "players",
        "squad_observations", "matches", "standings", "scorers",
    }


@responses.activate
def test_all_eight_resources_cost_five_requests_for_one_competition(
    pl_matches: dict[str, Any],
) -> None:
    """The server caps at 10 requests/minute. A recurring run for one
    competition and one season must fit five: competitions, teams, matches,
    standings, scorers.

    That budget only holds because every resource shares one ResponseCache
    keyed on (path, params) -- so, in particular, iter_scorers's `limit`
    parameter and iter_seasons's hardcoded scorers `limit` must build the
    identical URL, or the scorers request silently doubles. Every other test
    exercises one or two resources against its own private cache, so none of
    them would notice that divergence. This test is the one place all eight
    iter_* functions run over a single shared cache, the way the real
    pipeline runs them.
    """
    responses.get(f"{BASE_URL}/competitions", json=COMPETITIONS_PAYLOAD, status=200)
    responses.get(f"{BASE_URL}/competitions/PL/teams",
                  json=teams_payload(ARSENAL, CHELSEA), status=200)
    responses.get(f"{BASE_URL}/competitions/PL/matches", json=pl_matches, status=200)
    responses.get(f"{BASE_URL}/competitions/PL/standings",
                  json=STANDINGS_PAYLOAD, status=200)
    responses.get(f"{BASE_URL}/competitions/PL/scorers", json=SCORERS_PAYLOAD, status=200)

    cache = ResponseCache(make_client())
    codes = ("PL",)
    seasons = (2026,)
    observed_on = date(2026, 9, 3)

    list(iter_competitions(cache, codes=codes))
    list(iter_teams(cache, codes=codes))
    list(iter_players(cache, codes=codes))
    list(iter_squad_observations(cache, observed_on=observed_on, codes=codes))
    list(iter_matches(cache, seasons=seasons, codes=codes))
    list(iter_standings(cache, snapshot_on=observed_on, codes=codes))
    list(iter_scorers(cache, seasons=seasons, codes=codes))
    list(iter_seasons(cache, seasons=seasons, codes=codes))

    assert len(responses.calls) == 5


@responses.activate
def test_the_source_declares_the_agreed_write_dispositions() -> None:
    """competitions is the only replace. Any season-scoped replace would
    delete backfilled seasons on every current-season run.
    """
    source = football_data_source(client=make_client(), seasons=(2026,),
                                  run_date=date(2026, 9, 3))
    dispositions = {
        name: r.write_disposition for name, r in source.resources.items()
    }

    assert dispositions["competitions"] == "replace"
    assert all(
        d == "merge" for name, d in dispositions.items() if name != "competitions"
    )


@responses.activate
def test_standings_pins_form_as_text_so_an_all_null_load_keeps_the_column() -> None:
    """`form` is null for every team early in a season (confirmed against the
    live API and a 2026-09-02 matchday-2 probe). With no non-null value to
    infer a type from, dlt drops a column entirely rather than materializing
    it as all-NULL, so the destination table's shape would depend on how far
    into the season the first load happened. The standings resource must
    declare an explicit text type hint for `form` to prevent that.
    """
    source = football_data_source(client=make_client(), seasons=(2026,),
                                  run_date=date(2026, 9, 3))

    columns = source.resources["standings"].columns

    assert columns["form"]["data_type"] == "text"


@responses.activate
def test_matches_pins_group_and_winner_as_text_so_a_thin_season_keeps_the_columns() -> None:
    """`group` is null for every match in a group-less/barely-started season
    (confirmed against BigQuery: the real `raw.matches` table has no `group`
    column at all because dlt only materializes a column when at least one
    row in a load has a non-null value for it) and `winner` is null until a
    match finishes. Same failure mode as `standings.form` -- pin both
    explicitly so the destination table's shape doesn't depend on how far
    into the season the first load happened.
    """
    source = football_data_source(client=make_client(), seasons=(2026,),
                                  run_date=date(2026, 9, 3))

    columns = source.resources["matches"].columns

    assert columns["group"]["data_type"] == "text"
    assert columns["winner"]["data_type"] == "text"
