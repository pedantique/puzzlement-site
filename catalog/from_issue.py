#!/usr/bin/env python3
"""Turn an "Add a puzzle" issue into a catalog entry.

Reads the issue body that GitHub's issue form produces ("### Label\\n\\nvalue"),
maps it onto the catalog's shape and prints the JSON. With --apply it inserts
the entry into catalog.json's `added` list.

    python3 catalog/from_issue.py --body-file issue.md
    python3 catalog/from_issue.py --body-file issue.md --apply

Deliberately conservative: a field the form left blank, or filled with something
the catalog doesn't accept, is left out rather than guessed at. `_review` in the
output lists anything a human should look at before publishing.
"""
import argparse
import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CATALOG = Path(__file__).with_name("catalog.json")

CATEGORIES = {"Word", "Spelling", "Trivia", "Logic", "Numbers", "Sudoku", "Crossword",
              "Cryptic", "Visual", "Music", "Sports", "Geography", "Science", "Movie & TV"}
ACCESS = {"Free", "Login required", "Freemium", "Paid sub required"}
CADENCE = {"daily", "weekly", "sporadic", "unlimited", "monday", "tuesday", "wednesday",
           "thursday", "friday", "saturday", "sunday", "monWed", "thuFri", "monSat"}
METRICS = {"passFail", "time", "guesses", "mistakes", "hints", "points", "par", "tier"}

# Issue-form label -> our key. The labels are the form's, verbatim.
FIELDS = {
    "Name": "name",
    "URL": "url",
    "One line about it": "description",
    "Publisher": "publisher",
    "Genre": "category",
    "Access": "access",
    "How often": "cadence",
    "Emoji": "emoji",
    "Reset time": "reset_time",
    "Typical minutes": "estimated_minutes",
    "What the result is measured in": "primary_metric",
    "How a result can be captured": "score_share",
    "A real result, pasted": "sample_share",
    "Today's edition number": "edition_number",
    "Anything true of this one": "extras",
    "Anything else": "notes",
}

BLANK = {"", "_no response_", "none", "n/a"}


def parse_issue(body):
    """GitHub writes each answer as '### Label' then the value."""
    out, label = {}, None
    buffer = []
    for line in body.splitlines():
        if line.startswith("### "):
            if label:
                out[label] = "\n".join(buffer).strip()
            label, buffer = line[4:].strip(), []
        elif label:
            buffer.append(line)
    if label:
        out[label] = "\n".join(buffer).strip()
    return {FIELDS[k]: v for k, v in out.items() if k in FIELDS}


def slug(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def value(fields, key):
    v = (fields.get(key) or "").strip()
    return None if v.lower() in BLANK else v


def convert(fields):
    review = []

    name = value(fields, "name") or ""
    url = value(fields, "url") or ""
    if not name or not url:
        raise SystemExit("the form needs at least a name and a URL")
    if not url.startswith("https://"):
        review.append(f"URL isn't https: {url}")

    category = value(fields, "category")
    if category not in CATEGORIES:
        review.append(f"genre {category!r} isn't one of ours; defaulting to Logic")
        category = "Logic"
    access = value(fields, "access")
    if access not in ACCESS:
        review.append(f"access {access!r} isn't one of ours; defaulting to Free")
        access = "Free"

    entry = {
        "id": slug(name),
        "name": name,
        "emoji": value(fields, "emoji") or "\U0001F9E9",
        "url": url,
        "source": value(fields, "publisher") or "Indie",
        "description": (value(fields, "description") or "").rstrip("."),
        "category": category,
        "access": access,
        "classification": {},
    }
    c = entry["classification"]

    cadence = value(fields, "cadence")
    if cadence in CADENCE:
        c["cadence"] = cadence
    elif cadence:
        review.append(f"cadence {cadence!r} isn't one of ours; left out")

    metric = value(fields, "primary_metric")
    if metric in METRICS:
        c["primaryMetric"] = metric
    elif metric:
        review.append(f"metric {metric!r} isn't one of ours; left out")

    share = value(fields, "score_share")
    if share:
        c["scoreShare"] = share.split()[0]          # "none — nothing to copy" -> "none"

    if reset := value(fields, "reset_time"):
        c["resetTime"] = reset
    if minutes := value(fields, "estimated_minutes"):
        digits = re.sub(r"\D", "", minutes)
        if digits:
            c["estimatedMinutes"] = int(digits)

    if edition := value(fields, "edition_number"):
        m = re.search(r"(\d{4}-\d{2}-\d{2}).*?(\d+)", edition)
        if m:
            c["editionNumberRef"] = {"date": m.group(1), "number": int(m.group(2))}
        else:
            review.append(f"couldn't read an edition number from {edition!r}")

    for line in (fields.get("extras") or "").splitlines():
        ticked = line.strip().startswith("- [X]") or line.strip().startswith("- [x]")
        if not ticked:
            continue
        low = line.lower()
        if "signing in" in low:
            c["loginBenefit"] = True
        elif "past puzzles" in low:
            c["archiveAccess"] = "free"
            review.append("archive marked playable — check whether it's free or needs a subscription")
        elif "failed outright" in low:
            c["canFail"] = True
        elif "fit the screen" in low:
            c["fitToScreen"] = True

    if sample := value(fields, "sample_share"):
        review.append("a sample result was supplied — a score parser needs writing in Swift for it")
        entry["_sampleShareText"] = sample
    elif c.get("scoreShare", "none") != "none":
        review.append("says a result can be shared, but no sample was pasted")

    if notes := value(fields, "notes"):
        entry["_notes"] = notes

    return entry, review


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--body-file", required=True, help="the issue body, as markdown")
    ap.add_argument("--apply", action="store_true", help="write it into catalog.json")
    args = ap.parse_args()

    entry, review = convert(parse_issue(Path(args.body_file).read_text()))
    draft = dict(entry)
    draft["_review"] = review or ["nothing flagged"]
    print(json.dumps(draft, indent=2, ensure_ascii=False))

    if args.apply:
        # The _ keys are notes for a human, not catalog fields.
        clean = {k: v for k, v in entry.items() if not k.startswith("_")}
        doc = json.loads(CATALOG.read_text())
        doc.setdefault("added", [])
        doc["added"] = [a for a in doc["added"] if a["id"] != clean["id"]] + [clean]
        doc["updated"] = dt.date.today().isoformat()
        CATALOG.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
        print(f"\nadded {clean['id']} to {CATALOG.name}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
