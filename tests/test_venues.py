"""Tests for the one-time Nominatim venue geocoding backfill.

`choose` holds all the judgement and no I/O, so these tests need no HTTP at
all. Nominatim will confidently return *something* for any string; the point
of `choose` is deciding when that something is trustworthy enough to ship a
coordinate that weather will later be joined on.
"""

import duckdb
import pytest
import responses

from football_pipeline.venues import (
    NOMINATIM_URL,
    NominatimSearch,
    Venue,
    choose,
    geocode,
    read_venue_names,
    write_csv,
)


def result(
    *,
    name: str = "Emirates Stadium",
    lat: str = "51.5549",
    lon: str = "-0.108436",
    category: str = "leisure",
    type_: str = "stadium",
    country: str = "gb",
    extratags: dict[str, str] | None = None,
) -> dict[str, object]:
    """A Nominatim jsonv2 result, shaped as the real API returns them."""
    return {
        "name": name,
        "display_name": f"{name}, London, United Kingdom",
        "lat": lat,
        "lon": lon,
        "category": category,
        "type": type_,
        "address": {"country_code": country},
        "extratags": extratags or {},
    }


def test_a_single_stadium_in_the_expected_country_is_accepted() -> None:
    picked, note = choose([result()], expected_country="gb")

    assert picked is not None
    assert picked["lat"] == "51.5549"
    assert note == ""


def test_no_results_at_all_is_flagged_rather_than_guessed() -> None:
    picked, note = choose([], expected_country="gb")

    assert picked is None
    assert "no match" in note


def test_a_result_in_the_wrong_country_is_rejected() -> None:
    """Nominatim happily returns a same-named place on another continent."""
    picked, note = choose([result(country="us")], expected_country="gb")

    assert picked is None
    assert "country" in note


def test_two_stadiums_in_the_same_country_are_too_ambiguous_to_pick() -> None:
    """'Stadio Olimpico' exists in Rome and in Turin, both in Italy.

    A country check cannot separate them, so guessing would silently attach
    every Lazio home match to the weather in Turin.
    """
    picked, note = choose(
        [
            result(name="Stadio Olimpico", country="it", lat="41.93", lon="12.45"),
            result(name="Stadio Olimpico", country="it", lat="45.04", lon="7.65"),
        ],
        expected_country="it",
    )

    assert picked is None
    assert "ambiguous" in note


def test_non_stadium_matches_are_discarded_before_counting_candidates() -> None:
    """A road called 'Stadium Way' must not count as a candidate.

    Without this filter it would either be picked outright or make a genuine
    single stadium look ambiguous.
    """
    picked, note = choose(
        [
            result(name="Stadium Way", category="highway", type_="residential"),
            result(name="Emirates Stadium"),
        ],
        expected_country="gb",
    )

    assert picked is not None
    assert picked["name"] == "Emirates Stadium"
    assert note == ""


def test_only_non_stadium_matches_is_treated_as_no_match() -> None:
    picked, note = choose(
        [result(name="Stadium Way", category="highway", type_="residential")],
        expected_country="gb",
    )

    assert picked is None
    assert "no match" in note


class FakeSearch:
    """Records queries and returns canned Nominatim results."""

    def __init__(self, *responses: list[dict[str, object]]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def __call__(self, query: str, country: str) -> list[dict[str, object]]:
        self.calls.append((query, country))
        return self._responses.pop(0) if self._responses else []


def test_a_confident_match_becomes_a_row_with_float_coordinates() -> None:
    search = FakeSearch([result(extratags={"capacity": "60704"})])

    venue = geocode("Emirates Stadium", area_code="ENG", search=search)

    assert venue.latitude == pytest.approx(51.5549)
    assert venue.longitude == pytest.approx(-0.108436)
    assert venue.country_code == "gb"
    assert venue.capacity == 60704
    assert venue.needs_review is False
    assert search.calls == [("Emirates Stadium", "gb")]


def test_an_unmapped_country_never_spends_a_request() -> None:
    """Nominatim allows 1 req/sec. A request we know will be unconstrained
    is worse than useless: it burns the budget AND returns a result we would
    have to reject anyway.
    """
    search = FakeSearch([result()])

    venue = geocode("Somewhere Arena", area_code="ZZZ", search=search)

    assert search.calls == []
    assert venue.needs_review is True
    assert venue.latitude is None
    assert "country" in venue.note


def test_an_unresolvable_venue_yields_no_coordinates_and_keeps_the_reason() -> None:
    """A flagged row with the reason attached is what makes manual review
    possible; a silently dropped row is not.
    """
    search = FakeSearch([])

    venue = geocode("Nowhere Ground", area_code="ENG", search=search)

    assert venue.latitude is None
    assert venue.longitude is None
    assert venue.needs_review is True
    assert "no match" in venue.note


def test_missing_or_unparseable_capacity_is_none_not_an_error() -> None:
    """OSM capacity tags are free text -- '~40000' and 'unknown' both occur."""
    assert geocode("A", area_code="ENG", search=FakeSearch([result()])).capacity is None
    junk = FakeSearch([result(extratags={"capacity": "about 40k"})])
    assert geocode("B", area_code="ENG", search=junk).capacity is None


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class FakeSleep:
    """Records waits and advances the clock, so tests never really block."""

    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)
        self.clock.now += seconds


@responses.activate
def test_search_sends_the_identifying_user_agent_and_country_filter() -> None:
    """Nominatim's policy requires a User-Agent identifying the application;
    stock library agents are explicitly refused.
    """
    responses.get(NOMINATIM_URL, json=[result()], status=200)
    clock = FakeClock()

    NominatimSearch(sleep=FakeSleep(clock), clock=clock)("Emirates Stadium", "gb")

    request = responses.calls[0].request
    assert "football-tracker" in request.headers["User-Agent"]
    assert "github.com" in request.headers["User-Agent"]
    assert request.params["countrycodes"] == "gb"
    assert request.params["q"] == "Emirates Stadium"
    assert request.params["extratags"] == "1"


@responses.activate
def test_back_to_back_searches_are_spaced_a_full_second_apart() -> None:
    """One request per second is Nominatim's hard limit, not a suggestion."""
    for _ in range(2):
        responses.get(NOMINATIM_URL, json=[result()], status=200)
    clock = FakeClock()
    sleep = FakeSleep(clock)
    search = NominatimSearch(sleep=sleep, clock=clock)

    search("A", "gb")
    search("B", "gb")

    assert sleep.calls == [pytest.approx(1.0)]


@responses.activate
def test_a_search_after_a_long_gap_does_not_wait() -> None:
    for _ in range(2):
        responses.get(NOMINATIM_URL, json=[result()], status=200)
    clock = FakeClock()
    sleep = FakeSleep(clock)
    search = NominatimSearch(sleep=sleep, clock=clock)

    search("A", "gb")
    clock.now += 5.0
    search("B", "gb")

    assert sleep.calls == []


def test_the_csv_is_written_sorted_so_reruns_produce_stable_diffs(tmp_path) -> None:
    """This file is committed. An unordered rewrite would churn the diff and
    make a real change impossible to spot in review.
    """
    venues = [
        Venue("Zenith Arena", "ENG", "gb", 1.0, 2.0, "Zenith", 100, False, ""),
        Venue("Alpha Park", "ITA", "it", None, None, "", None, True, "ambiguous: 2"),
    ]
    path = tmp_path / "venues.csv"

    write_csv(venues, path)

    lines = path.read_text().splitlines()
    assert lines[0].startswith("venue_name,")
    assert lines[1].startswith("Alpha Park,")
    assert lines[2].startswith("Zenith Arena,")
    assert "ambiguous: 2" in lines[1]


def build_teams_db(path, rows: list[tuple[str, str | None, str]]) -> None:
    con = duckdb.connect(str(path))
    con.execute("create schema raw")
    con.execute("create table raw.teams (name text, venue_name text, area_code text)")
    con.executemany("insert into raw.teams values (?, ?, ?)", rows)
    con.close()


def test_venue_names_are_deduplicated_so_a_shared_ground_is_geocoded_once(
    tmp_path,
) -> None:
    """San Siro is home to both Milan and Inter; Stadio Olimpico to Roma and
    Lazio. Geocoding each twice would waste half our 1 req/sec budget on
    duplicates and could yield two different coordinates for one ground.
    """
    db = tmp_path / "t.duckdb"
    build_teams_db(
        db,
        [
            ("AC Milan", "Stadio Giuseppe Meazza", "ITA"),
            ("FC Internazionale", "Stadio Giuseppe Meazza", "ITA"),
            ("Arsenal FC", "Emirates Stadium", "ENG"),
        ],
    )

    assert read_venue_names(db) == [
        ("Emirates Stadium", "ENG"),
        ("Stadio Giuseppe Meazza", "ITA"),
    ]


def test_a_team_with_no_venue_is_skipped_rather_than_geocoded_as_empty(
    tmp_path,
) -> None:
    """Sabah FK really does come back with venue null and the literal string
    'null null null' as its address.
    """
    db = tmp_path / "t.duckdb"
    build_teams_db(db, [("Sabah FK", None, "AZE"), ("Arsenal FC", "Emirates", "ENG")])

    assert read_venue_names(db) == [("Emirates", "ENG")]


def test_two_candidates_at_the_same_spot_are_one_stadium_not_an_ambiguity() -> None:
    """OSM often holds a ground twice -- once as a way, once as a relation.

    Aspmyra Stadion and PreZero Arena both came back as two candidates with
    byte-identical display names. Treating that as ambiguous throws away a
    perfectly good coordinate.
    """
    picked, note = choose(
        [
            result(name="Aspmyra stadion", lat="67.2800", lon="14.3960", country="no"),
            result(name="Aspmyra stadion", lat="67.2815", lon="14.3975", country="no"),
        ],
        expected_country="no",
    )

    assert picked is not None
    assert note == ""


def test_two_stadiums_in_different_cities_stay_ambiguous() -> None:
    """St James' Park is Newcastle's ground and also Exeter's, 500km apart.

    Collapsing these would have silently sourced Newcastle United's match
    weather from Devon.
    """
    picked, note = choose(
        [
            result(name="St. James' Park", lat="54.9756", lon="-1.6216"),
            result(name="St James' Park", lat="50.7236", lon="-3.5217"),
        ],
        expected_country="gb",
    )

    assert picked is None
    assert "ambiguous" in note


def test_a_no_match_is_retried_once_with_stadium_appended() -> None:
    """OSM's name is often longer than the API's: 'Elland Road' matches only
    roads, while 'Elland Road stadium' finds the ground immediately.
    """
    search = FakeSearch([], [result(name="Elland Road Stadium")])

    venue = geocode("Elland Road", area_code="ENG", search=search)

    assert [query for query, _ in search.calls] == [
        "Elland Road",
        "Elland Road stadium",
    ]
    assert venue.needs_review is False


def test_an_ambiguous_result_is_not_retried() -> None:
    """A second request cannot un-ambiguate two real stadiums; it would spend
    a second of budget to be told the same thing.
    """
    search = FakeSearch(
        [
            result(name="St. James' Park", lat="54.9756", lon="-1.6216"),
            result(name="St James' Park", lat="50.7236", lon="-3.5217"),
        ]
    )

    venue = geocode("St James' Park", area_code="ENG", search=search)

    assert len(search.calls) == 1
    assert venue.needs_review is True


def test_a_venue_already_ending_in_stadium_is_not_retried() -> None:
    """Appending 'stadium' to 'Wembley Stadium' just makes a worse query."""
    search = FakeSearch([], [result()])

    geocode("Wembley Stadium", area_code="ENG", search=search)

    assert len(search.calls) == 1
