"""dlt source for football-data.org v4.

Resource bodies are plain generator functions so tests can call them without
dlt's runtime; the `@dlt.resource` wrappers at the bottom are the only dlt
surface.
"""

import contextlib
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


def iter_scorers(
    cache: ResponseCache,
    seasons: tuple[int, ...],
    codes: tuple[str, ...] = COMPETITIONS,
    limit: int = SCORERS_LIMIT,
) -> Iterator[dict[str, Any]]:
    """One row per player per competition per season.

    Merged on (competition_code, season_id, player_id), never replaced.
    Recurring runs fetch only the current season, so a full refresh would
    delete every backfilled 2023-2025 season on every nightly run.

    The endpoint defaults to 10 rows and silently truncates -- `limit` is
    always sent explicitly. `?limit=100` returned all 49 scorers in the
    probe, so there is no top-N truncation to worry about, and goal counts
    only rise within a season, so merge (not replace) is also sufficient to
    keep them current.
    """
    for code in codes:
        for season in seasons:
            payload = cache.get(
                f"competitions/{code}/scorers",
                {"season": season, "limit": limit},
            )
            season_id = (payload.get("season") or {}).get("id")
            for entry in payload.get("scorers", []):
                player = entry.get("player") or {}
                team = entry.get("team") or {}
                yield {
                    "competition_code": code,
                    "season_id": season_id,
                    "player_id": player.get("id"),
                    "player_name": player.get("name"),
                    "team_id": team.get("id"),
                    "team_name": team.get("name"),
                    "played_matches": entry.get("playedMatches"),
                    "goals": entry.get("goals"),
                    "assists": entry.get("assists"),
                    "penalties": entry.get("penalties"),
                }


def _season_row(season: Mapping[str, Any], code: str) -> dict[str, Any] | None:
    """Build a season row, or None if the object is empty/idless.

    Not every envelope carries a season -- a competition mid-registration or
    an edge-case payload can omit it -- so the caller must be able to skip
    the candidate rather than yield a row with a null id.
    """
    if not season.get("id"):
        return None
    winner = season.get("winner") or {}
    return {
        "id": season["id"],
        "competition_code": code,
        "start_date": season.get("startDate"),
        "end_date": season.get("endDate"),
        "current_matchday": season.get("currentMatchday"),
        "winner_team_id": winner.get("id") if isinstance(winner, dict) else None,
    }


def iter_seasons(
    cache: ResponseCache,
    seasons: tuple[int, ...],
    codes: tuple[str, ...] = COMPETITIONS,
) -> Iterator[dict[str, Any]]:
    """One row per season, harvested from every envelope that carries one.

    /competitions only exposes each competition's *current* season, so
    deriving dim_seasons from it alone would leave every backfilled season
    missing -- historical matches would then join to a season row that does
    not exist, and the Season Archive page would have nothing to browse.
    matches, scorers and standings envelopes all carry a full season object,
    and all three are already being fetched by other resources, so reading
    them here through the ResponseCache costs no extra requests, whichever
    order dlt happens to run resources in.

    The standings call is wrapped in NotFoundError, same as iter_standings:
    /competitions/CL/standings 404s all summer, and that must not stop
    harvesting for every other competition.

    Season ids are globally unique across competitions, so deduplication is
    a single `seen` set keyed on id alone.
    """
    seen: set[int] = set()

    competitions = cache.get("competitions")
    for comp in competitions["competitions"]:
        if comp["code"] not in codes:
            continue
        row = _season_row(comp.get("currentSeason") or {}, comp["code"])
        if row and row["id"] not in seen:
            seen.add(row["id"])
            yield row

    for code in codes:
        envelopes: list[Mapping[str, Any]] = []
        for season in seasons:
            envelopes.append(cache.get(f"competitions/{code}/matches", {"season": season}))
            envelopes.append(
                cache.get(
                    f"competitions/{code}/scorers",
                    {"season": season, "limit": SCORERS_LIMIT},
                )
            )
        with contextlib.suppress(NotFoundError):
            envelopes.append(cache.get(f"competitions/{code}/standings"))

        for envelope in envelopes:
            candidates = [envelope.get("season") or {}]
            candidates += [m.get("season") or {} for m in envelope.get("matches", [])]
            for candidate in candidates:
                row = _season_row(candidate, code)
                if row and row["id"] not in seen:
                    seen.add(row["id"])
                    yield row


def iter_standings(
    cache: ResponseCache,
    snapshot_on: date,
    codes: tuple[str, ...] = COMPETITIONS,
) -> Iterator[dict[str, Any]]:
    """One row per team per competition per UTC day.

    This is the only resource that swallows a 404. /competitions/CL/standings
    404s all summer because the league phase has not started, and that means
    "no data yet". Everywhere else a 404 is a malformed path or a bad
    competition code and must surface.

    `snapshot_on` is injected for the same reason as `observed_on` in
    iter_squad_observations: this project is UTC end-to-end, the caller owns
    that decision, and injecting it makes the date assertable rather than a
    matter of trust. football-data.org exposes only the CURRENT table -- this
    snapshot history exists only because we record it ourselves, merged on
    (competition_code, season_id, team_id, snapshot_date) so a rerun on the
    same day produces identical rows instead of duplicates.
    """
    stamp = snapshot_on.isoformat()
    for code in codes:
        try:
            payload = cache.get(f"competitions/{code}/standings")
        except NotFoundError:
            continue
        season_id = (payload.get("season") or {}).get("id")
        for table in payload.get("standings", []):
            for row in table.get("table", []):
                team = row.get("team") or {}
                yield {
                    "competition_code": code,
                    "season_id": season_id,
                    "team_id": team.get("id"),
                    "snapshot_date": stamp,
                    "stage": table.get("stage"),
                    "type": table.get("type"),
                    "group": table.get("group"),
                    "position": row.get("position"),
                    "played_games": row.get("playedGames"),
                    "form": row.get("form"),
                    "won": row.get("won"),
                    "draw": row.get("draw"),
                    "lost": row.get("lost"),
                    "points": row.get("points"),
                    "goals_for": row.get("goalsFor"),
                    "goals_against": row.get("goalsAgainst"),
                    "goal_difference": row.get("goalDifference"),
                }
