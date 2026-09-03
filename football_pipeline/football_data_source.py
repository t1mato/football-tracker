"""dlt source for football-data.org v4.

Resource bodies are plain generator functions so tests can call them without
dlt's runtime; the `@dlt.resource` wrappers at the bottom are the only dlt
surface.
"""

from collections.abc import Iterator, Mapping
from datetime import date
from typing import Any

from football_pipeline.client import FootballDataClient, NotFoundError

COMPETITIONS: tuple[str, ...] = ("PL", "PD", "BL1", "SA", "FL1", "CL")

# The scorers endpoint defaults to 10 rows and silently truncates -- an
# explicit limit is always sent. Shared so every URL built against it
# produces the same cache key.
SCORERS_LIMIT = 100

_CacheKey = tuple[str, tuple[tuple[str, str], ...]]


class ResponseCache:
    """Fetches each URL at most once per pipeline run.

    Several resources read the same payload -- teams feeds teams, players and
    squad_observations -- and dlt does not guarantee the order resources run
    in. Memoizing here means every resource can ask for what it needs without
    any of them needing to know who else asked.

    A 404 is memoized too: `competitions/CL/standings` 404s all summer before
    the Champions League league phase starts, and more than one resource
    asks for it. Only `NotFoundError` is treated as a durable fact about the
    URL -- every other exception (a timeout, a 500) is transient and must
    propagate uncached so the caller retries it.
    """

    def __init__(self, client: FootballDataClient) -> None:
        self._client = client
        self._responses: dict[_CacheKey, dict[str, Any]] = {}
        self._not_found: dict[_CacheKey, NotFoundError] = {}

    def get(
        self, path: str, params: Mapping[str, str | int] | None = None
    ) -> dict[str, Any]:
        key: _CacheKey = (
            path,
            tuple(sorted((k, str(v)) for k, v in (params or {}).items())),
        )
        if key in self._not_found:
            raise self._not_found[key]
        if key not in self._responses:
            try:
                self._responses[key] = self._client.get(path, params)
            except NotFoundError as exc:
                self._not_found[key] = exc
                raise
        return self._responses[key]


def iter_competitions(
    cache: ResponseCache, codes: tuple[str, ...] = COMPETITIONS
) -> Iterator[dict[str, Any]]:
    """One row per tracked competition. Costs one request for all six.

    `numberOfAvailableSeasons` is deliberately dropped: it reports each
    competition's total recorded history (Premier League claims 128
    seasons), not what the free tier actually serves -- which stops at
    roughly four seasons back, with older seasons returning 403. Carrying it
    forward would invite a backfill loop built on a number that lies.
    """
    payload = cache.get("competitions")
    for comp in payload["competitions"]:
        if comp["code"] not in codes:
            continue
        area = comp.get("area") or {}
        yield {
            "id": comp["id"],
            "code": comp["code"],
            "name": comp["name"],
            "type": comp.get("type"),
            "area_id": area.get("id"),
            "area_name": area.get("name"),
        }


def iter_teams(
    cache: ResponseCache, codes: tuple[str, ...] = COMPETITIONS
) -> Iterator[dict[str, Any]]:
    """One row per team per competition it appears in; merged on id downstream.

    Nested lists (squad, runningCompetitions, staff) are dropped. squad is
    emitted separately by iter_players and iter_squad_observations with a real
    team_id foreign key.
    """
    for code in codes:
        payload = cache.get(f"competitions/{code}/teams")
        for team in payload["teams"]:
            area = team.get("area") or {}
            coach = team.get("coach") or {}
            yield {
                "id": team["id"],
                "name": team["name"],
                "short_name": team.get("shortName"),
                "tla": team.get("tla"),
                "crest": team.get("crest"),
                "address": team.get("address"),
                "website": team.get("website"),
                "founded": team.get("founded"),
                "club_colors": team.get("clubColors"),
                "venue_name": team.get("venue"),
                "area_id": area.get("id"),
                "area_name": area.get("name"),
                "coach_id": coach.get("id"),
                "coach_name": coach.get("name"),
                "last_updated": team.get("lastUpdated"),
            }


def iter_players(
    cache: ResponseCache, codes: tuple[str, ...] = COMPETITIONS
) -> Iterator[dict[str, Any]]:
    """One row per player, merged on id. SCD type 1: the current club wins.

    The squad payload carries no team reference at all -- only id, name,
    position, dateOfBirth, nationality -- so team_id is injected here from
    the enclosing team. Without it the only way to recover which club a
    player belongs to would be joining on dlt's internal _dlt_root_id hash
    in dbt. History is not lost by the overwrite: iter_squad_observations
    appends it separately.
    """
    for code in codes:
        payload = cache.get(f"competitions/{code}/teams")
        for team in payload["teams"]:
            for player in team.get("squad") or []:
                yield {
                    "id": player["id"],
                    "team_id": team["id"],
                    "name": player.get("name"),
                    "position": player.get("position"),
                    "date_of_birth": player.get("dateOfBirth"),
                    "nationality": player.get("nationality"),
                }


def iter_matches(
    cache: ResponseCache,
    seasons: tuple[int, ...],
    codes: tuple[str, ...] = COMPETITIONS,
) -> Iterator[dict[str, Any]]:
    """One row per match, merged on id -- score and status change until FINISHED.

    No incremental cursor. Matches carry lastUpdated, but the API has no
    updatedSince parameter, so filtering on it would save warehouse writes and
    zero requests, while risking silently never reloading a correction that
    did not bump the field.

    `status` is passed through verbatim, defects included: a handful of
    matches return a timestamp string where the status enum belongs.
    Coercing that here would make it untestable in dbt staging, which is
    where cleaning belongs.
    """
    for code in codes:
        for season in seasons:
            payload = cache.get(f"competitions/{code}/matches", {"season": season})
            for match in payload.get("matches", []):
                score = match.get("score") or {}
                full_time = score.get("fullTime") or {}
                half_time = score.get("halfTime") or {}
                home = match.get("homeTeam") or {}
                away = match.get("awayTeam") or {}
                season_obj = match.get("season") or {}
                yield {
                    "id": match["id"],
                    "competition_code": code,
                    "season_id": season_obj.get("id"),
                    "utc_date": match.get("utcDate"),
                    "status": match.get("status"),
                    "matchday": match.get("matchday"),
                    "stage": match.get("stage"),
                    "group": match.get("group"),
                    "last_updated": match.get("lastUpdated"),
                    "home_team_id": home.get("id"),
                    "home_team_name": home.get("name"),
                    "away_team_id": away.get("id"),
                    "away_team_name": away.get("name"),
                    "winner": score.get("winner"),
                    "duration": score.get("duration"),
                    "full_time_home": full_time.get("home"),
                    "full_time_away": full_time.get("away"),
                    "half_time_home": half_time.get("home"),
                    "half_time_away": half_time.get("away"),
                }


def iter_squad_observations(
    cache: ResponseCache,
    observed_on: date,
    codes: tuple[str, ...] = COMPETITIONS,
) -> Iterator[dict[str, Any]]:
    """One row per player per team per UTC day. Costs no extra requests.

    football-data.org serves only the CURRENT squad -- there is no
    historical squad endpoint at any tier. iter_players merges on player id
    (SCD type 1), so every run overwrites a player's club, which would
    destroy transfer history permanently rather than deferring it. This
    resource appends one row per player per team per UTC day so that
    history is reconstructible later. Raw stays deliberately dumb --
    mostly-identical daily rows. The model that collapses consecutive
    identical days into validity intervals is deliberately not built here:
    it is capability, and can be added whenever a history question is
    actually asked.

    `observed_on` is injected by the caller rather than read from the clock
    in here, both because this project is UTC end-to-end and the caller
    owns that decision, and because injecting it is what makes the date
    assertable in a test instead of a matter of trust -- the same pattern
    used for the clock in rate_limiter.RateLimiter.
    """
    stamp = observed_on.isoformat()
    for code in codes:
        payload = cache.get(f"competitions/{code}/teams")
        for team in payload["teams"]:
            for player in team.get("squad") or []:
                yield {
                    "team_id": team["id"],
                    "player_id": player["id"],
                    "observed_date": stamp,
                    "position": player.get("position"),
                }
