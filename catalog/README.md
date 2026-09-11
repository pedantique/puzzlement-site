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

`schemaVersion` must stay `1` until an app build that understands a newer one
ships — older builds ignore a document with a version they don't know.
