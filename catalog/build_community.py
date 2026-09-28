#!/usr/bin/env python3
"""Build catalog/community.json from the awesome-daily-minigames list.

Source: https://github.com/guilyx/awesome-daily-minigames (data/games.yml),
licensed CC0-1.0 — public domain, no attribution or share-alike strings, so it
can feed a commercial app.

The result is a SEPARATE document from catalog.json: the app fetches it only
when "Community puzzles" is switched on in Settings → Experimental, and its
games are marked so they read as unvetted. Games already in the app (matched on
registrable domain) are skipped, as are Reddit-hosted ones, which don't work in
an embedded web view.

    python3 catalog/build_community.py --out catalog/community.json

Run it in CI weekly; review the diff before merging — the upstream list takes
community pull requests and nobody here has played most of these.
"""
import argparse
import datetime as dt
import json
import re
import sys
import urllib.request

SOURCE = "https://raw.githubusercontent.com/guilyx/awesome-daily-minigames/master/data/games.yml"

# awesome-daily-minigames category id -> Puzzlement category.
CATEGORY = {
    # awesome-daily-minigames category id -> Puzzlement PuzzleCategory raw value.
    "word-guessing": "Word",
    "word-connections": "Word",
    "word-grids": "Word",
    "crosswords": "Crossword",
    "numbers-math": "Numbers",
    "logic": "Logic",
    "geography": "Geography",
    "history": "Trivia",
    "music": "Music",
    "movies-tv": "Movie & TV",
    "sports": "Sports",
    "video-games": "Trivia",
    "trivia": "Trivia",
    "visual": "Visual",
    "science-nature": "Science",
    "arcade": "Logic",
    "board-card": "Logic",
    "hubs": "Word",
}

# Fallback emoji per Puzzlement category — matches PuzzleCategory.emoji in the
# app, so a community game without a usable favicon still looks like its genre
# rather than one of 175 identical puzzle pieces.
EMOJI = {
    "Word": "\U0001F524", "Spelling": "\U0001F41D", "Trivia": "\u2753",
    "Logic": "\U0001F914", "Numbers": "\U0001F522", "Sudoku": "9\uFE0F\u20E3",
    "Crossword": "\u25FB\uFE0F", "Cryptic": "\U0001F575\uFE0F",
    "Visual": "\U0001F5BC\uFE0F", "Music": "\U0001F3B5", "Sports": "\u26BD",
    "Geography": "\U0001F30D", "Science": "\U0001F52C", "Movie & TV": "\U0001F3AC",
}

FIELD_RE = {k: re.compile(rf"^\s*-?\s*{k}: (.*)$", re.M) for k in
            ("name", "url", "category", "platform", "description")}
TAGS_RE = re.compile(r"^\s*tags: \[(.*)\]", re.M)


def registrable(url: str) -> str:
    host = re.sub(r"^https?://", "", url).split("/")[0].lower()
    host = host[4:] if host.startswith("www.") else host
    return host


def parse(yaml_text: str) -> list[dict]:
    games = []
    for block in re.split(r"\n(?=- name:)", yaml_text):
        if not block.lstrip().startswith("- name:"):
            continue
        g = {}
        for key, rx in FIELD_RE.items():
            m = rx.search(block)
            if m:
                g[key] = m.group(1).strip().strip('"')
        m = TAGS_RE.search(block)
        g["tags"] = [t.strip() for t in m.group(1).split(",")] if m else []
        if g.get("name") and g.get("url"):
            games.append(g)
    return games


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"community-{s}"


def convert(games: list[dict], known_hosts: set[str]) -> list[dict]:
    out, seen = [], set()
    for g in games:
        if g.get("platform") != "web":
            continue                      # Reddit-hosted games need the Reddit app
        host = registrable(g["url"])
        if host in known_hosts or host.endswith("reddit.com"):
            continue
        if g.get("category") not in CATEGORY:
            print(f"skipped {g['name']}: unknown category {g.get('category')!r}", file=sys.stderr)
            continue
        gid = slug(g["name"])
        if gid in seen:
            continue
        seen.add(gid)
        tags = g.get("tags", [])
        access = "Paid sub required" if "paywalled" in tags else "Free"
        category = CATEGORY[g["category"]]
        out.append({
            "id": gid,
            "name": g["name"],
            "emoji": EMOJI.get(category, "\U0001F9E9"),
            "url": g["url"],
            "source": "Community",
            "description": g.get("description", "").rstrip("."),
            "category": category,
            "access": access,
            "classification": {
                "cadence": "unlimited" if "unlimited" in tags else "daily",
                "resetTime": "Midnight local",
                "popularityScore": 1,
                "scoreShare": "none",
            },
        })
    return sorted(out, key=lambda x: x["name"].lower())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="catalog/community.json")
    ap.add_argument("--source", default=SOURCE)
    ap.add_argument("--known-hosts", default="catalog/known_hosts.txt",
                    help="one registrable domain per line: games the app already has")
    args = ap.parse_args()

    with urllib.request.urlopen(args.source, timeout=60) as r:
        yaml_text = r.read().decode("utf-8")

    try:
        known = {l.strip().lower() for l in open(args.known_hosts) if l.strip() and not l.startswith("#")}
    except FileNotFoundError:
        known = set()

    games = convert(parse(yaml_text), known)
    doc = {
        "schemaVersion": 1,
        "warning": "Unvetted. Some of these games will not load, fit, reset or "
                   "score correctly in an embedded web view.",
        "updated": dt.date.today().isoformat(),
        "source": "https://github.com/guilyx/awesome-daily-minigames (CC0-1.0)",
        "note": "Community list, not vetted by Puzzlement. Shown only when "
                "Settings > Experimental > Community puzzles is on.",
        "added": games,
    }
    with open(args.out, "w") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"{len(games)} games -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
