"""One-time venue geocoding backfill against OpenStreetMap Nominatim.

Venues do not move, so this runs once and its results are committed. The
warehouse joins weather to matches on venue coordinates, which makes a wrong
coordinate worse than a missing one: it produces confident, plausible, wrong
weather. So `choose` refuses to guess, and anything it cannot resolve is
flagged for a human rather than filled in.
"""

import csv
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any

import duckdb
import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Nominatim refuses stock library user-agents and requires one identifying the
# application. The repo URL is the contact channel -- deliberately not a
# personal email, which would end up in a public git history.
USER_AGENT = "football-tracker/0.1 (+https://github.com/t1mato/football-tracker)"

# Published hard limit, not a suggestion: 1 request per second.
MIN_INTERVAL_SECONDS = 1.0

EARTH_RADIUS_KM = 6371.0

# Two hits closer together than this are one ground recorded twice -- OSM
# commonly holds a stadium as both a way and a relation. Grounds that are
# genuinely different sit far further apart than this (the two St James'
# Parks are 500km apart), so collapsing at 1km cannot merge real rivals.
SAME_PLACE_KM = 1.0

# OSM types that plausibly denote a football ground. Everything else -- roads,
# suburbs and bus stops named after a stadium -- is discarded before
# candidates are counted, so one real stadium is never made to look ambiguous
# by the street running past it.
STADIUM_TYPES = frozenset({"stadium", "sports_centre", "pitch"})

# football-data.org area codes are FIFA/IOC style ("ENG"), not ISO -- England
# is not a country to ISO. Nominatim's `countrycodes` filter wants ISO 3166-1
# alpha-2, so the two have to be bridged by hand.
#
# Verified against the 17 area codes actually present in raw.teams on
# 2026-09-03. The source MIXES CONVENTIONS: mostly ISO 3166-1 alpha-3
# (DEU, GRC, NLD), but England is ENG and Portugal is POR, neither of which
# is ISO (those would be GBR and PRT). So this cannot be derived by rule and
# has to be a table. An unmapped code deliberately flags for review rather
# than geocoding unconstrained, so a wrong entry announces itself as a
# flagged row instead of a plausible coordinate in the wrong country.
COUNTRY_CODES: Mapping[str, str] = {
    "AUT": "at", "AZE": "az", "BEL": "be", "CZE": "cz", "DEU": "de",
    "ENG": "gb", "ESP": "es", "FRA": "fr", "GRC": "gr", "ITA": "it",
    "MCO": "mc", "NLD": "nl", "NOR": "no", "POR": "pt", "SVK": "sk",
    "TUR": "tr", "UKR": "ua",
}


@dataclass(frozen=True)
class Venue:
    """One geocoded venue, review-flagged when it could not be resolved."""

    venue_name: str
    area_code: str
    country_code: str
    latitude: float | None
    longitude: float | None
    display_name: str
    capacity: int | None
    needs_review: bool
    note: str
    query: str = ""


def _capacity(picked: Mapping[str, Any]) -> int | None:
    """OSM capacity tags are free text -- '~40000' and 'unknown' both occur."""
    raw = str((picked.get("extratags") or {}).get("capacity", "")).strip()
    return int(raw) if raw.isdigit() else None


def _coords(picked: Mapping[str, Any]) -> tuple[float, float] | None:
    try:
        return float(picked["lat"]), float(picked["lon"])
    except (KeyError, TypeError, ValueError):
        return None


def geocode(
    venue_name: str,
    area_code: str,
    search: Callable[[str, str], Sequence[Mapping[str, Any]]],
    overrides: Mapping[str, str] | None = None,
) -> Venue:
    """Resolve one venue name to a coordinate, or flag why it could not be.

    `venue_name` stays the warehouse key even when an override changes what
    is searched -- raw.teams still calls Napoli's ground Stadio San Paolo.
    """
    query = (overrides or {}).get(venue_name, venue_name)

    def flagged(country: str, note: str) -> Venue:
        return Venue(
            venue_name, area_code, country, None, None, "", None, True, note, query
        )

    iso = COUNTRY_CODES.get(area_code.upper(), "")
    if not iso:
        # Skip the request entirely: an unconstrained search would spend a
        # second of our 1 req/sec budget to return something we must reject.
        return flagged("", f"country not mapped: {area_code!r}")

    picked, note = choose(search(query, iso), iso)

    # OSM's name is often longer than the API's -- "Elland Road" matches only
    # the road, while "Elland Road stadium" finds the ground. Retry only a
    # no-match: a second request cannot un-ambiguate two real stadiums, and a
    # country mismatch means the name matched something real elsewhere.
    if (
        picked is None
        and note.startswith("no match")
        and not query.lower().endswith("stadium")
    ):
        picked, note = choose(search(f"{query} stadium", iso), iso)

    if picked is None:
        return flagged(iso, note)

    coords = _coords(picked)
    if coords is None:
        return flagged(iso, "unparseable coordinates in match")

    lat, lon = coords
    return Venue(
        venue_name=venue_name,
        area_code=area_code,
        country_code=iso,
        latitude=lat,
        longitude=lon,
        display_name=str(picked.get("display_name", "")),
        capacity=_capacity(picked),
        needs_review=False,
        note="",
        query=query,
    )


def choose(
    results: Sequence[Mapping[str, Any]], expected_country: str
) -> tuple[Mapping[str, Any] | None, str]:
    """Pick the one trustworthy stadium from Nominatim's candidates.

    Returns `(result, "")` on a confident match, or `(None, reason)` when the
    answer is not safe to ship. Nominatim returns *something* for almost any
    string, so "it returned a result" is not evidence of anything.
    """
    stadiums = [r for r in results if str(r.get("type", "")).lower() in STADIUM_TYPES]
    if not stadiums:
        return None, "no match: nothing stadium-like returned"

    in_country = [
        r
        for r in stadiums
        if str((r.get("address") or {}).get("country_code", "")).lower()
        == expected_country.lower()
    ]
    if not in_country:
        return None, f"country mismatch: no candidate in {expected_country}"

    distinct = _collapse_same_place(in_country)
    if len(distinct) > 1:
        names = "; ".join(str(r.get("display_name", "?"))[:60] for r in distinct)
        return None, f"ambiguous: {len(distinct)} candidates -- {names}"

    return distinct[0], ""


def _distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance, used only to tell one ground from two."""
    lat1, lon1 = a
    lat2, lon2 = b
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    h = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(h))


def _collapse_same_place(
    results: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Drop candidates that sit on top of one already kept."""
    kept: list[Mapping[str, Any]] = []
    for candidate in results:
        here = _coords(candidate)
        if here is not None and any(
            (there := _coords(k)) is not None and _distance_km(here, there) <= SAME_PLACE_KM
            for k in kept
        ):
            continue
        kept.append(candidate)
    return kept


class NominatimSearch:
    """Rate-limited Nominatim client.

    Unlike football-data.org's limiter, the wait lives inside the client
    rather than being reported to a caller. There is only one consumer here
    and only one correct pace, so making it impossible to call too fast beats
    making it configurable. `sleep` and `clock` are injected so tests spend no
    real seconds.
    """

    def __init__(
        self,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        min_interval: float = MIN_INTERVAL_SECONDS,
        timeout: float = 30.0,
    ) -> None:
        self._session = session or requests.Session()
        self._sleep = sleep
        self._clock = clock
        self._min_interval = min_interval
        self._timeout = timeout
        self._last_call: float | None = None

    def __call__(self, query: str, country: str) -> list[dict[str, Any]]:
        if self._last_call is not None:
            elapsed = self._clock() - self._last_call
            if elapsed < self._min_interval:
                self._sleep(self._min_interval - elapsed)

        response = self._session.get(
            NOMINATIM_URL,
            params={
                "q": query,
                "countrycodes": country,
                "format": "jsonv2",
                "addressdetails": "1",
                "extratags": "1",  # sometimes carries OSM's capacity tag
                "limit": "10",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=self._timeout,
        )
        self._last_call = self._clock()
        response.raise_for_status()
        results: list[dict[str, Any]] = response.json()
        return results


CSV_FIELDS = (
    "venue_name",
    "area_code",
    "country_code",
    "latitude",
    "longitude",
    "capacity",
    "needs_review",
    "note",
    "query",
    "display_name",
)


def write_csv(venues: Iterable[Venue], path: Path) -> None:
    """Write the geocoding cache, sorted so reruns produce stable diffs.

    This file is committed and reviewed by eye; an unordered rewrite would
    churn every line and hide the one row that actually changed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for venue in sorted(venues, key=lambda v: v.venue_name):
            writer.writerow(
                {
                    "venue_name": venue.venue_name,
                    "area_code": venue.area_code,
                    "country_code": venue.country_code,
                    "latitude": "" if venue.latitude is None else f"{venue.latitude:.6f}",
                    "longitude": "" if venue.longitude is None else f"{venue.longitude:.6f}",
                    "capacity": "" if venue.capacity is None else venue.capacity,
                    "needs_review": "true" if venue.needs_review else "false",
                    "note": venue.note,
                    "query": venue.query,
                    "display_name": venue.display_name,
                }
            )


DEFAULT_DB = Path("football_data.duckdb")
DEFAULT_OUT = Path("transform/seeds/venues.csv")
DEFAULT_OVERRIDES = Path("transform/seeds/venue_overrides.csv")


def load_overrides(path: Path = DEFAULT_OVERRIDES) -> dict[str, str]:
    """Map a raw venue name to a better search string.

    Overrides supply a *query*, never a coordinate. Every result they produce
    still goes through the same country and stadium-type validation, so a
    misremembered rename fails as a flagged row rather than quietly planting
    a stadium in the wrong city. Hand-written coordinates would bypass
    exactly the check that makes this safe.
    """
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            row["venue_name"]: row["search_query"]
            for row in csv.DictReader(handle)
            if row.get("venue_name") and row.get("search_query")
        }


def read_venue_names(db_path: Path = DEFAULT_DB) -> list[tuple[str, str]]:
    """Distinct (venue_name, area_code) pairs to geocode, in stable order.

    Deduplicated because grounds are shared -- San Siro serves Milan and
    Inter, Stadio Olimpico serves Roma and Lazio. Geocoding a shared ground
    once per tenant would burn our 1 req/sec budget on duplicates and could
    return two different coordinates for the same stadium.

    Teams with no venue are skipped: the API really does return venue null,
    and there is nothing to geocode.
    """
    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = connection.execute(
            """
            select distinct venue_name, area_code
            from raw.teams
            where venue_name is not null and area_code is not null
            order by venue_name
            """
        ).fetchall()
    finally:
        connection.close()
    return [(str(name), str(code)) for name, code in rows]


def backfill(
    db_path: Path = DEFAULT_DB,
    out_path: Path = DEFAULT_OUT,
    search: Callable[[str, str], Sequence[Mapping[str, Any]]] | None = None,
    overrides_path: Path = DEFAULT_OVERRIDES,
) -> list[Venue]:
    """Geocode every distinct venue once and write the committed cache."""
    resolve = search or NominatimSearch()
    overrides = load_overrides(overrides_path)
    venues = [
        geocode(name, code, resolve, overrides)
        for name, code in read_venue_names(db_path)
    ]
    write_csv(venues, out_path)
    return venues


if __name__ == "__main__":
    results = backfill()
    flagged = [v for v in results if v.needs_review]
    print(f"geocoded {len(results) - len(flagged)}/{len(results)} venues")
    print(f"wrote {DEFAULT_OUT}")
    if flagged:
        print(f"\n{len(flagged)} need review:")
        for venue in flagged:
            print(f"  {venue.venue_name} [{venue.area_code}] -- {venue.note}")
