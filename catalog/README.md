# Remote catalog

`catalog.json` is fetched by the Puzzlement app at launch (and hourly on
foreground) and merged over the catalog built into the app. It is an
**overlay**: the app works fully without it, and it can only change data —
URLs, dates, metadata, whole new games — never score parsers.

Served at <https://puzzlement.games/catalog/catalog.json>.

## The Wednesday job (Colorful Strands)

NYT's Colorful Strands has a URL that can't be predicted from the date, so each
week's edition has to be added by hand:

1. Open **Actions → Add Colorful Strands edition → Run workflow** on this repo.
2. Paste the week's URL, e.g. `https://www.nytimes.com/games/bonus/strands/colorful/2026-09-16-1101`
   — or just the slug `2026-09-16-1101`, or just the number `1101`.
3. Leave the date blank (it's read from the slug, else the nearest Wednesday).
4. Run. The commit lands on `main`, Pages redeploys in ~1 minute, the app
   picks it up next launch.

The same thing from a terminal:

    python3 catalog/add_edition.py 2026-09-16-1101 && git commit -am "Catalog: …" && git push

Anything else in the file can be edited directly in GitHub's web editor —
the app ignores a file that doesn't parse, so a typo can't break it, but
the workflow's "Validate JSON" step will tell you.

## Community catalog (experimental)

`community.json` is a second, opt-in document: ~175 daily games converted from
[awesome-daily-minigames](https://github.com/guilyx/awesome-daily-minigames),
which is CC0-1.0 (public domain, no attribution or share-alike conditions, so a
paid app can use it). The app fetches it **only** when Settings → Experimental →
Community puzzles is on, marks every game `Community`, and drops them all again
when the switch goes off.

Rebuild it with `python3 catalog/build_community.py`; `catalog/known_hosts.txt`
lists the domains Puzzlement already has, so its own games aren't duplicated.
The "Refresh community catalog" action does this weekly and opens a pull request
so new upstream entries get a look before they ship.

## Submitting a puzzle

Anyone with a GitHub account can open
[**Add a puzzle**](https://github.com/pedantique/puzzlement-site/issues/new?template=add-puzzle.yml)
— a form, not a file: dropdowns for the things the catalog is fussy about
(genre, access, cadence, metric), free text for the rest, and one box for a real
pasted result, which is worth more than everything else on the form because the
score parser is written against it.

A bot turns each submission into the catalog entry it would become and posts it
back as a comment, flagging anything under `_review`. Nothing reaches the app
until the **approved** label goes on; that commits the entry and closes the
issue, and it's live within the hour.

`catalog/from_issue.py` does the conversion and can be run by hand:

    python3 catalog/from_issue.py --body-file issue.md          # see the draft
    python3 catalog/from_issue.py --body-file issue.md --apply  # write it in

It is deliberately conservative: a blank field, or one holding something the
catalog doesn't accept, is left out rather than guessed at.

## Format

```json
{
  "schemaVersion": 1,
  "updated": "2026-09-11",
  "puzzles": {                       // overrides for puzzles the app already has, by id
    "strands-colorful": {
      "classification": { "manualArchiveURLs": { "2026-09-16": "https://…" } }
    },
    "guardian-sudoku": { "url": "https://www.theguardian.com/…" }
  },
  "added": [                         // brand-new games
    {
      "id": "somegame", "name": "Some Game", "emoji": "🧩",
      "url": "https://somegame.example/", "source": "Indie",
      "description": "One line", "category": "Word", "access": "Free",
      "classification": { "primaryMetric": "time", "lowerIsBetter": true, "resetTime": "Midnight local" }
    }
  ],
  "removed": ["dead-game-id"]        // hidden from the catalog
}
```

Override fields on a puzzle: `name`, `emoji`, `url`, `source`, `description`,
`category` (`Word`, `Spelling`, `Trivia`, `Logic`, `Numbers`, `Sudoku`,
`Crossword`, `Cryptic`, `Visual`, `Music`, `Sports`, `Geography`…), `access`
(`Free`, `Login required`, `Freemium`, `Paid sub required`), and a
`classification` block.

`classification` fields (all optional): `primaryMetric` (`time`, `guesses`,
`mistakes`, `hints`, `tier`, `points`, `par`, `passFail`), `lowerIsBetter`,
`canFail`, `scoreMax`, `failureAtMax`, `cadence` (`daily`, `monWed`, `thuFri`,
`monSat`, `weekly`, `sporadic`, `unlimited`, `sunday`…`saturday`),
`editionNameTiming`, `scoreShare` (`shareText`, `clipboardAuto`, `none`),
`archiveAccess` (`none`, `free`, `recentFree:7`, `subscriptionRequired`),
`estimatedMinutes`, `loginBenefit`, `loginPromptTiming`, `logoCode`,
`shareButtonLabel`, `popularityScore`, `launchDate` (`yyyy-MM-dd`),
`resetTime`, `disableSwipeBack`, `disableWebviewBack`,
`editionNumberRef` (`{"date": "yyyy-MM-dd", "number": 1}`), `dateURLPattern`,
`isArchiveOnlyDateURL`, `dateURLDayOffset`, `manualArchiveURLs` (merged with
the built-in entries), `sundayURL`,
`dateURLReset` (`{"hour": 22, "minute": 0, "timezone": "America/New_York", "isNextDayRelease": true}`),
`fitToScreen`, `editionNameJS`, `editionNameAPIURL`, `editionNameAPIField`,
`editionNameAPIFieldPost`.

`adBlockRules` (optional) replaces the app's built-in content-blocker list for
the puzzle web view — Safari's `WKContentRuleList` format,
`[{"trigger": {"url-filter": "…"}, "action": {"type": "block"}}]`. A malformed
rule makes the app reject the whole document and keep its cached copy, and a
list that fails to compile falls back to the built-in one. Use it to add a
tracker, or to loosen a rule that breaks a puzzle, without an App Store release.

## Fixing a score parser without a build

Score parsing normally lives in Swift. When a site rewords its share text — or
stops handing it over and leaves the app the page itself — the catalog can carry
a fix that takes effect on the next launch. Two forms, both under a puzzle's
`classification`, tried in order and both ahead of the built-in parser:

```json
"minute-cryptic": {
  "classification": {
    "scoreRules": [
      {
        "require": ["you got it"],
        "captures": {
          "par": "(on par|\\d+ (?:under|over) par)",
          "hints": "your hints\\s*(\\d+)"
        },
        "template": "{par} · {hints|hint|hints}"
      }
    ]
  }
}
```

- `require` / `reject` (optional): substrings that must, or must not, appear —
  case-insensitive. Use `require` to avoid claiming a score from an unfinished
  page.
- `captures`: name → regex. The first capture group is used, or the whole match
  if there isn't one.
- `template`: `{name}` substitutes a capture; `{name|singular|plural}` appends
  the right word for a count. **If any name in the template didn't match, the
  rule is abandoned** — a half-matched rule never produces half a score. The
  next rule is tried, then the built-in parser.

For anything a template can't express — arithmetic, conditionals — there's
`"scoreJS"`, a function of one string:

```json
"scoreJS": "function(t){ var m=t.match(/Your hints\\s*(\\d+)/i); return m ? m[1]+' hints' : null; }"
```

It runs in a bare JavaScriptCore context: **no DOM, no network, no cookies, no
access to the puzzle page**, and it is never injected into the web view — those
hold the user's signed-in publisher sessions and must stay out of reach of
anything served from here. It gets a string, returns a string or null, and is
abandoned if it runs longer than a moment. Prefer `scoreRules`; reach for
`scoreJS` only when a template genuinely can't do the job.

Genuinely complicated parsers (Puzzmo's share URLs, Twixtle's score-plus-time)
stay in Swift where they can be tested properly.

`iconURL` (optional, on a puzzle's `classification`) points at an icon we serve
— `img/icons/<id>.png` in this repo, so `https://puzzlement.games/img/icons/one-up.png`.
The app prefers it over anything it can scrape from the game's own site, which is
the point: some games publish nothing better than a 32px favicon and the app
would otherwise upscale that to a blur. 256×256 PNG with transparency; the app
draws it on a white card.

`schemaVersion` must stay `1` until an app build that understands a newer one
ships — older builds ignore a document with a version they don't know.
