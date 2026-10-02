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
3. **The harness robot** stands beside the what-if field and talks in a
   bubble. You tap a suggestion or type your own and press Rerun; the robot
   says what changed and how sure it is. Tapping a group makes it quote one
   person from that group.
4. **History / Rerun.** After a rerun, this switch in the toolbar flips the
   portraits, map and dots between history and the rerun. Flipped states
   carry a dot on the map.
5. **The time bar** along the bottom moves between all 60 elections.

Cameron's brief was one focused flow, ultra minimal. The version before this
one had tabs, KPI tiles, tables, an inspector, search and a scenario popover;
all of it was cut as "slop and chrome". Before adding anything, see whether it
could be a sentence in the robot's bubble instead.

## Run it

- **Dev:** `pnpm dev` serves the page; `pnpm serve` runs the local
  simulation server on port 8787, and Vite proxies `/api` to it
  (`vite.config.ts`).
- **URLs** (query parameters, on the page's route):
  - `?sample=1`: sample data (`sample.ts`), starting on a random story year.
  - `&year=1896`: a given year. The page keeps `year` in the URL as it moves.
  - No `sample=1`: the real server path, `/api/simulacra`. With no server it
    says there's no simulation service and offers Use Sample Data.
- **Gates:** `pnpm lint`, `pnpm check`, `pnpm size`, `pnpm test` (see
  `AGENTS.md`).

## Where things live

All under `src/lib/simulacra/` unless noted.

| What | File |
|---|---|
| Page state, loading, reruns, what the robot says (`say()`), keys, layout CSS | the page (being ported) |
| Portrait, winner ring and check, initials fallback, dark-mode photo fix | `Portrait.svelte` |
| Tile map and flip dots | `MiniMap.svelte` (grid in `geo.ts`) |
| A group's row of 50 dots, its caption and "was …" line | `SliceRow.svelte` |
| Robot slot, bubble, More / Less | `WhatIf.svelte` |
| The bubble's working: steps, interviews, sources | `WhatIfWorking.svelte` |
| Field, Rerun / Reset / Stop | `WhatIfComposer.svelte` |
| What-if chips | `KindChips.svelte` |
| The bubble's message type, kind labels, step splitting | `whatif.ts` |
| Time bar (slider, ‹ ›, shuffle) | `TimeBar.svelte` |
| ⓘ About popover | `InfoPopover.svelte` |
| Places in text that light the map | `Places.svelte`, `places.ts` |
| Colours (dark-mode authoring, each era's party hues, the "Other" grey) | `palette.ts` |
| Elections as they happened | `history.ts` (owned by the simulation side) |
| Server contract, schemas, sample stand-in, written stories | `api.ts`, `schemas.ts`, `sample.ts`, `sampleEras.ts`, `sampleData.ts`, `stories.ts` (owned by the simulation side) |
| Placing the robot in a page | `src/lib/robot/` (ported separately) |
| The robot's stills while the 3D robot loads | `static/simulacra/chatpro-history.png`, `chatpro-rerun.png` |

## The components' contract (Svelte 5, runes)

Components take callback props instead of dispatching events. What was
`on:toggle={(e) => toggle(e.detail)}` is now `ontoggle={toggle}`; the detail
is the callback's argument.

- `SliceRow`: `ontoggle()`, `onedit(d: SliceEdit)`.
- `TimeBar`: `onchange(year)`, `onscrub(on)`, `onshuffle()`.
- `WhatIf`: `ontoggle(key)`, `onrun()`, `onstop()`, `onreset()`,
  `onaction(key)`, `onfocus(on)`; `bind:slot`, `bind:value`, `bind:input`.
- `InfoPopover`: its content is the `children` snippet.

Every simulation call (`api.ts`, and `sample.ts` with the same shape)
returns an `Outcome`: `ok` with the parsed value, `error` (with a `reason`:
`offline`, `auth`, `missing`, `failed`, `malformed`), `indeterminate` (a
POST timed out after it may have landed: poll, don't resubmit), or
`unsupported` (no simulation service). Nothing throws.

## The layout contract: one screen at 1440×900

- **Vertical budget, top to bottom:**
  - Toolbar: 48px.
  - Header: about 200px. The portraits are 96×120 beside their facts; the
    middle column holds the year (44px) and the map (12px tiles).
  - Note and "Also ran": about 40px.
  - Who voted: a heading and five rows of 42px each.
  - Composer: the robot slot (168×220) beside the bubble, suggestions and
    field.
  - Time bar: 68px, fixed.
- **The busiest state to check:** `?sample=1&year=1912`, tap Taft Steps
  Aside, then Rerun. With a three-line verdict, Rerun's bottom edge sat at
  791px and the time bar's top at 832px. Anything you add above the composer
  comes out of those 41px.
- **Breakpoints:**
  - ≤760px: the header stacks, and the face stands in for the robot.
  - ≤700px: each row's dots drop under its label.
  - ≤560px: the time bar hides its 1850 and 1950 labels.
- **Scroll container:** the page scrolls inside `.sa`, a fixed layer.

## Look and feel

- **Dark mode is a filter.** In the original app `#invert-wrapper` applied
  `invert(1) hue-rotate(180deg) saturate(1.5)`; the page applies the same
  filter to its toolbar and content in the Rerun view (`.sa.dark`).
  - Author neutral colours once, in light values: `#fff` renders black.
  - Party colours come from `paint(hue, light)`, which is authored twice.
  - Photos need `filter: invert(1) hue-rotate(180deg) saturate(66.7%)` in dark
    mode, as the portraits and the robot's face already have.
  - The 3D robot is outside the filter, so it's always true colour.
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
  - Title Case for buttons ("Use Sample Data", "Another Election", "Rerun").
  - Sentence case everywhere else.
  - No exclamation marks; numbers as numerals.
- **Controls:**
  - Controls are 34–36px high, with a `#3876b7` focus ring.
  - `prefers-reduced-motion` turns off the dot, map and fade transitions.
  - The time bar's sizes are CSS custom properties at the top of
    `TimeBar.svelte`'s `.bar` (the tuned values; the old `?tuneTimeline`
    panel is gone).
- **Accessibility:** every control has a label; keep them meaningful.

## The robot

- **Browser tab:** the page measures the `WhatIf` slot (`bind:slot`) and
  places the robot over it. Once drawn, the robot's anchors nudge its box
  once, so its feet sit on the slot's floor.
- **Clickable:** the slot is a button, so pressing the robot focuses the
  field.
- **Draggable:** dragged across, the robot turns with the pointer (0.6° per
  px, held to ±180°) and, let go, eases back. A turn alone never restages
  the frame; only a moved box does (`boxMoved` in `src/lib/robot/stage.ts`).
- **Stills:** until the 3D robot draws, `WhatIf` shows a still (`still`
  prop: `{ src, dx, db, w }`) from `static/simulacra/`.
- **When the robot isn't drawn**, the harness's face stands in (`face`,
  `faceStyle`): windows ≤760px wide, and before WebGL loads.
- **If you move the slot:** keep `bind:slot` on `WhatIf`, and re-measure
  after anything that moves it.

## What the robot says

`say(...)` in the page picks the robot's line in this order:

1. Connecting.
2. No simulation service or unreachable, with Use Sample Data and Try Again.
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
  state; `SliceRow` keeps its dragged draft keyed to the slice it was drawn
  on rather than clearing it in an effect.
- **Svelte 5 trims whitespace at tag edges.** Put separators inside template
  literals, like ``{` · ${x}`}``, or they vanish.
- **SVG:** use `style:fill`, because CSS beats the `fill` attribute. CSS `r`
  sizes circles and animates.
- **Dynamic components:** `{@const Icon = …}<Icon />`, not
  `<svelte:component>`.

## Checking your work

- `pnpm lint && pnpm check && pnpm size && pnpm test`.
- The sample model's outcomes for every story what-if:
  `pnpm tsx scripts/model-check.ts`.
- **Look at it** with the dev server on `?sample=1&year=1896`.

## Rough edges (good first tasks)

- Long names wrap in the header ("William Jennings Bryan", "John C.
  Breckinridge").
- When many states flip (1912, Taft Steps Aside: 30 states), the map is busy.
- The suggestions don't look disabled while a rerun runs.
- The map doesn't fill in state by state during a rerun, although
  `run.done` / `run.total` are available.
- In the History view after a rerun, the run's suggestions still show as
  chosen.
- "Washington, D.C." in text lights Washington state, not D.C.
  (`places.ts`: the D.C. rule's trailing `\b` can't follow a period).
- Missouri (1820) and Michigan (1836) cast electoral votes in `history.ts`
  before `geo.ts`'s `first` year for them, so their map tiles are empty in
  those years.
