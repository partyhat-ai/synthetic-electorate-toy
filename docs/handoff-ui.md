# Simulacra Americana — UI handoff

For an agent making quick, careful adjustments to the page. The simulation
behind it is a separate job (the original repo's
`src/lib/simulacra/HANDOFF-SIMULATION.md`, not ported; the harness side is in
`docs/harness/`): don't change the data contract (`src/lib/simulacra/schemas.ts`,
`api.ts`) or the sample model from here. If the page needs a new field, ask
for it there.

## What it is

One page that opens on a real US presidential election and lets you rerun it
with one fact changed. In the original web app it was `/simulacra-americana`
(`src/routes/simulacra-americana/+page.svelte`); in this repo the page is
being ported next and its route may differ.

1. **The election as it happened.** Two portraits, a ring and check on the
   winner, electoral and popular vote, a small tile map of who carried each
   state, and a one-line note.
2. **Who voted.** Four or five groups, each a row of 50 dots. The winner's
   voters fill in from the left, the runner-up's from the right, and third
   parties, people who stayed home and people who couldn't vote sit in the
   middle.
3. **The harness** (its face, until the robot is ported) sits beside the
   what-if field and talks in a bubble. You tap a suggestion or type your own
   and press Rerun; it says what changed and how sure it is. Tapping a group
   makes it quote one person from that group.
4. **History / Rerun.** After a rerun, this switch in the toolbar flips the
   portraits, map and dots between history and the rerun. Flipped states
   pulse on the map.
5. **The time bar** along the bottom moves between all 60 elections.

Cameron's brief was one focused flow, ultra minimal. The version before this
one had tabs, KPI tiles, tables, an inspector, search and a scenario popover;
all of it was cut as "slop and chrome". Before adding anything, see whether it
could be a sentence in the robot's bubble instead.

## Run it

- **Dev:** `pnpm dev` serves the page.
- **URLs** (query parameters, on the page's route):
  - `?year=1896`: a given year, else a random story year. The page keeps
    `year` in the URL as it moves.
  - The page calls the real server path, `/api/simulacra`. With no server it
    says there's no simulation service.
- **Gates:** `pnpm lint`, `pnpm check`, `pnpm size`, `pnpm test` (see
  `AGENTS.md`).

## Where things live

All under `src/lib/simulacra/` unless noted.

| What | File |
|---|---|
| Page state, loading, reruns, what the robot says (`say()`), keys, layout CSS | the page (being ported) |
| Portrait, winner ring and check, initials fallback, dark-mode photo fix | `Portrait.svelte` |
| Tile map and flip marks | `MiniMap.svelte` (grid in `geo.ts`) |
| A group's row of 50 dots, its caption and "was …" line | `SliceRow.svelte` |
| The harness's face and bubble | `WhatIf.svelte` |
| Field, Rerun / Reset / Stop | `WhatIfComposer.svelte` |
| What-if chips | `KindChips.svelte` |
| The bubble's message type and kind labels | `whatif.ts` |
| Time bar (slider, ‹ ›, shuffle) | `TimeBar.svelte` |
| ⓘ About popover | `InfoPopover.svelte` |
| Colours (dark-mode authoring, each era's party hues, the "Other" grey) | `palette.ts` |
| Elections as they happened | `history.ts` (owned by the simulation side) |
| Server contract, schemas, sample model | `api.ts`, `schemas.ts`, `sample.ts` (owned by the simulation side) |

## The components' contract (Svelte 5, runes)

Components take callback props instead of dispatching events. What was
`on:toggle={(e) => toggle(e.detail)}` is now `ontoggle={toggle}`; the detail
is the callback's argument.

- `SliceRow`: `ontoggle()`.
- `TimeBar`: `onchange(year)`, `onshuffle()`.
- `WhatIf`: `ontoggle(key)`, `onrun()`, `onstop()`, `onreset()`,
  `onaction(key)`, `onfocus(on)`; `bind:value`, `bind:input`.
- `InfoPopover`: its content is the `children` snippet.

Every simulation call (`api.ts`) returns the parsed answer or throws a
`SimError` with a `reason`: `offline`, `auth`, `missing`, `unsupported` (no
simulation service), `failed` or `malformed`.

## The layout contract: one screen at 1440×900

- **Vertical budget, top to bottom:**
  - Toolbar: 48px.
  - Header: about 200px. The portraits are 96×120 beside their facts; the
    middle column holds the year (44px) and the map (12px tiles).
  - Note and "Also ran": about 40px.
  - Who voted: a heading and five rows of 42px each.
  - Composer: the harness's face beside the bubble, suggestions and field.
  - Time bar: 68px, fixed.
- **Breakpoints:**
  - ≤760px: the header stacks.
  - ≤700px: each row's dots drop under its label.
  - ≤560px: the time bar hides its 1850 and 1950 labels.
- **Scroll container:** the page scrolls inside `.sa`, a fixed layer.

## Look and feel

- **Dark mode is a filter.** In the original app `#invert-wrapper` applied
  `invert(1) hue-rotate(180deg) saturate(1.5)`; the page applies the same
  filter to all of itself in the system's dark mode (`.sa.dark`).
  - Author neutral colours once, in light values: `#fff` renders black.
  - Party colours come from `paint(hue, light)`, which is authored twice.
  - Photos need `filter: invert(1) hue-rotate(180deg) saturate(66.7%)` in dark
    mode, as the portraits and the harness's face already have.
- **The colours are validated.** The dataviz validator was run in both modes
  against the page's surfaces (`#e5e5e5` light, `#1a1a1a` dark).
  - The red/blue, blue/orange, aqua/violet and blue/green pairs pass.
  - The "Other" grey `#4d4c48` is authored once and inverts to a light grey.
    It passes colour-blind separation beside every hue.
  - Orange, aqua and that grey are under 3:1 against the light page, so the
    legend and the text values have to stay.
  - Only the winner and runner-up get hues; everyone else is "Other". Don't
    add a hue.
- **Text wears ink, never party colours.** The dots, rings and map carry the
  colour; the words beside them stay black or grey.
- **Copy (Apple HIG):**
  - Title Case for buttons ("Try Again", "Another Election", "Rerun").
  - Sentence case everywhere else.
  - No exclamation marks; numbers as numerals.
- **Controls:**
  - Controls are 34–36px high, with a `#3876b7` focus ring.
  - `prefers-reduced-motion` turns off the dot, map and fade transitions.
- **Accessibility:** every control has a label; keep them meaningful.

## What the robot says

`say(...)` in the page picks the robot's line in this order:

1. Connecting.
2. No simulation service or unreachable, with Try Again.
3. Sign in.
4. Unopposed, with Another Election.
5. Rerunning, "n of m states counted".
6. The rerun failed.
7. The year's groups didn't load.
8. A just-tapped suggestion: its detail, its kind and confidence, then
   "Press Rerun…".
9. A picked group: one person's quote, who they are, what they did in history
   and in the rerun, and what could change it.
10. A rerun's verdict: "I read '…' as …" for typed words, then the verdict and
    the confidence line.
11. "This is 1896 as it happened…" (the History view after a rerun).
12. The greeting.

The verdict sentence itself comes from the server as `result.summary`. The
page's own copy lives in `say()`, `CONFIDENCE`, `KIND_NOTE` and the About
popover; the chips' kind wording is `KIND_LABEL` in `whatif.ts`.

## Keys

- ← and → step between elections, except while typing or on the slider.
- ⌘↩ or Ctrl↩ reruns.
- Esc drops the picked group.
- On the slider: arrows step, Page Up/Down jump five elections, Home/End go to
  the ends.

## Svelte notes (Svelte 5, runes)

- **Derive, don't sync.** Prefer `$derived` over an `$effect` that copies
  state.
- **Svelte 5 trims whitespace at tag edges.** Put separators inside template
  literals, like ``{` · ${x}`}``, or they vanish.
- **SVG:** use `style:fill`, because CSS beats the `fill` attribute. CSS `r`
  sizes circles and animates.
- **Dynamic components:** `{@const Icon = …}<Icon />`, not
  `<svelte:component>`.

## Checking your work

- `pnpm lint && pnpm check && pnpm size && pnpm test`.
- **Look at it** with the dev server on `?year=1896`.

## Rough edges (good first tasks)

- Long names wrap in the header ("William Jennings Bryan", "John C.
  Breckinridge").
- The suggestions don't look disabled while a rerun runs.
- The map doesn't fill in state by state during a rerun, although
  `run.done` / `run.total` are available.
- In the History view after a rerun, the run's suggestions still show as
  chosen.
- Missouri (1820) and Michigan (1836) cast electoral votes in `history.ts`
  before `geo.ts`'s `first` year for them, so their map tiles are empty in
  those years.
