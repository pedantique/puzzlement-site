#!/usr/bin/env python3
"""Add a dated edition URL to a puzzle's manualArchiveURLs in catalog.json.

Used by the "Add Colorful Strands edition" GitHub Actions form, and runnable
locally:

    python3 catalog/add_edition.py 2026-09-16-1101
    python3 catalog/add_edition.py https://www.nytimes.com/games/bonus/strands/colorful/2026-09-16-1101
    python3 catalog/add_edition.py 1101 --date 2026-09-16
    python3 catalog/add_edition.py --puzzle some-other-id --date 2026-09-16 https://example.com/x

The edition may be a full URL, a slug ("2026-09-16-1101"), or just the trailing
number ("1101"). A date embedded in the slug/URL wins; otherwise --date; otherwise
the nearest Wednesday (today if it is one).
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

CATALOG = Path(__file__).with_name("catalog.json")

# Where a bare slug/number goes for each puzzle that uses manual editions.
BASE_URLS = {
    "strands-colorful": "https://www.nytimes.com/games/bonus/strands/colorful/",
}
# Weekday the puzzle publishes on (Mon=0 … Sun=6), for the default date.
PUBLISH_WEEKDAY = {
    "strands-colorful": 2,  # Wednesday
}

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def nearest_publish_day(today: dt.date, weekday: int) -> dt.date:
    delta = (weekday - today.weekday()) % 7
    if delta == 0:
        return today
    ahead = today + dt.timedelta(days=delta)
    behind = today - dt.timedelta(days=7 - delta)
    # Mon/Tue -> the coming Wednesday; Thu-Sun -> the one just gone.
    return ahead if delta <= 2 else behind


def resolve(puzzle, edition, date, today):
    edition = edition.strip()
    if not edition:
        raise SystemExit("edition is required")

    embedded = DATE_RE.search(edition)
    if date:
        dt.date.fromisoformat(date)  # validate
    elif embedded:
        date = embedded.group(1)
    elif puzzle in PUBLISH_WEEKDAY:
        date = nearest_publish_day(today, PUBLISH_WEEKDAY[puzzle]).isoformat()
    else:
        raise SystemExit(f"--date is required for {puzzle} (no date in edition, no default weekday)")

    if edition.startswith("http://") or edition.startswith("https://"):
        url = edition
    else:
        base = BASE_URLS.get(puzzle)
        if not base:
            raise SystemExit(f"{puzzle}: pass a full URL (no base URL known for a bare slug)")
        slug = edition
        if slug.isdigit():          # "1101" -> "2026-09-16-1101"
            slug = f"{date}-{slug}"
        url = base + slug.lstrip("/")

    return date, url


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edition", help="full URL, slug, or trailing number")
    ap.add_argument("--puzzle", default="strands-colorful", help="catalog id (default: strands-colorful)")
    ap.add_argument("--date", help="yyyy-MM-dd the edition belongs to")
    ap.add_argument("--today", help=argparse.SUPPRESS)  # for tests
    args = ap.parse_args()

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    date, url = resolve(args.puzzle, args.edition, args.date, today)

    doc = json.loads(CATALOG.read_text())
    entry = doc.setdefault("puzzles", {}).setdefault(args.puzzle, {})
    urls = entry.setdefault("classification", {}).setdefault("manualArchiveURLs", {})
    previous = urls.get(date)
    urls[date] = url
    entry["classification"]["manualArchiveURLs"] = dict(sorted(urls.items()))
    doc["updated"] = today.isoformat()
    CATALOG.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")

    verb = "Replaced" if previous else "Added"
    print(f"{verb} {args.puzzle} {date} -> {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
