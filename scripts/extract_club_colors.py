"""One-time extraction of each club's dominant crest color, cached to a
committed file -- same "compute once, commit the result" discipline as
the venue geocoding backfill (CLAUDE.md). Crests come from
crests.football-data.org with no CORS headers (confirmed via curl), so
this has to run server-side in Python, not in the browser.

Re-run this (`.venv/bin/python scripts/extract_club_colors.py`) after a
new club with a crest shows up in dim_teams -- it's a full re-export,
not incremental, so it also picks up any crest URL that changed.
"""

import io
import json
import time
import urllib.request
from pathlib import Path

from PIL import Image

from warehouse.queries import get_connection

OUTPUT_PATH = Path("frontend/public/club-colors.json")

# Manual corrections for well-known clubs where automatic extraction
# (dominant non-near-white pixel cluster) picked an outline/background
# shade instead of the club's actual primary color -- verified against
# each club's real, widely-known primary color, not guessed. The
# algorithm also structurally can't recover a club whose real identity
# color IS white (e.g. Real Madrid), since near-white is deliberately
# excluded as background; left as the auto result there since a literal
# white line would be invisible on this chart's white background anyway.
OVERRIDES_BY_NAME = {
    "FC Barcelona": "#004d98",  # blaugrana blue, not the crest's gold trim
    "Manchester City FC": "#6cabdd",  # sky blue, not the crest's navy outline
    "Aston Villa FC": "#670e36",  # claret, not the crest's pale-blue trim
    "Villarreal CF": "#f7d117",  # "Yellow Submarine" yellow
    "AC Milan": "#fb090b",  # rossoneri red half of the identity
    "RB Leipzig": "#e4022d",  # RB red, not the crest's dark outline
    "RC Celta de Vigo": "#8ac6ef",  # celeste sky blue
    "Coventry City FC": "#78bfe6",  # Sky Blues
    "Le Mans FC": "#5b6480",  # extraction failed (bad crest asset); neutral fallback
}


def dominant_color(data: bytes, colors: int = 6) -> str | None:
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    im.thumbnail((80, 80))
    pixels = list(im.getdata())
    kept = [
        (r, g, b)
        for r, g, b, a in pixels
        if a >= 200 and not (r > 232 and g > 232 and b > 232)
    ]
    if not kept:
        return None
    small = Image.new("RGB", (len(kept), 1))
    small.putdata(kept)
    quantized = small.quantize(colors=min(colors, len(kept)), method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()
    counts = sorted(quantized.getcolors(), reverse=True)
    r, g, b = palette[counts[0][1] * 3 : counts[0][1] * 3 + 3]
    return f"#{r:02x}{g:02x}{b:02x}"


def main() -> None:
    con = get_connection()
    teams = con.execute(
        "select team_id, team_name, crest from dim_teams where crest is not null"
    ).df()

    result: dict[str, str] = {}
    for i, team in teams.iterrows():
        req = urllib.request.Request(
            team["crest"], headers={"User-Agent": "football-tracker-color-extract/1.0"}
        )
        try:
            data = urllib.request.urlopen(req, timeout=10).read()
            color = dominant_color(data)
        except Exception as exc:  # noqa: BLE001 -- best-effort backfill, log and move on
            print(f"  FAILED {team['team_name']}: {exc}")
            color = None
        override = OVERRIDES_BY_NAME.get(team["team_name"])
        final_color = override or color
        if final_color:
            result[str(team["team_id"])] = final_color
        note = " (overridden)" if override else ""
        print(f"[{i + 1}/{len(teams)}] {team['team_name']}: {final_color}{note}")
        time.sleep(0.05)  # polite pacing against a CDN we don't control

    OUTPUT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"\nWrote {len(result)} colors to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
