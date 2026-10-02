# Note for the UI agent, from the simulation harness

From the harness session (`simharness/` at the repo root, see `METHOD.md`). Nothing in your
files was edited.

Everything below is **additive**: the page keeps working if it ignores all of
it. The endpoints, the fields and the meanings in `api.js` are unchanged.

## 1. What now exists

- **A 1920 bundle** in the contract's shape: `runs/1920-bcbd86b43f/published/1920.json`
  (0.43 MB).
  - Every combination of the year's what-ifs.
  - One person per group per what-if.
- **An Express router** for the auth server: `serve/simulacra.ts`.
  - It serves bundles under `/api/simulacra`.
  - Runs finish immediately: the first `GET /runs/:id` is already `done`.
  - Hand edits (`edits`) are applied and re-tallied on the server.
- **One behaviour change you'll see.** A year with no bundle answers
  `GET /elections/:year` with 200 `{ slices: [], whatIfs: [], simulated: false }`
  rather than 404. `api.js` reads a first 404 as "there is no simulation
  service", so a 404 would wrongly send the page to sample data. Suggested copy
  when `simulated === false`: "I haven't simulated 1896 yet. Try 1920."

## 2. New fields

### `GET /elections/:year`

| Field | Meaning | Suggested use |
|---|---|---|
| `whatIf.assumption` | The concrete rule, one sentence | Show it under the tapped suggestion's `detail`, in the same bubble, before "Press Rerun" |
| `slice.source` | Which census, and which estimate of turnout and choice | The group caption's ⓘ, or the About popover. Too long for the row. |
| `simulated` | `false` when the year has no bundle | See above |

### `result` (in `GET /runs/:id`)

| Field | Shape | Meaning |
|---|---|---|
| `range` | `{ A: [lo, hi], B: [lo, hi], O: [lo, hi] }` | Central 80% of each candidate's electoral votes across draws |
| `drawsWon` | `{ A, B, O, none, of }` | In how many of `of` draws each candidate wins; `none` means no majority |
| `popular`, `popularRange` | `{ A, B, O }` votes; `{ A: [lo, hi], … }` | The popular vote, and its 80% range |
| `states[].marginRange` | `[lo, hi]` points | The 80% range of the winner's margin in that state |
| `states[].pFlip` | 0–1 | The share of draws in which the state flips |
| `assumptions` | `string[]` | One per applied what-if |
| `howIGotThis` | `string[]`, 2–4 lines | The disclosure. See §3. |
| `sources` | `[{ title, url }]` | Data sources for the run |
| `validation` | `{ passed, failed: [ids], not_run: [ids] }` | The pre-registered checks. See §4. |
| `cohortEffects` | `[{ whatIf, cohort, n, bias, weight, exposed, dr, dt }]` | Issue what-ifs only: how much each group moved, and how far the model's control answers strayed from the calibrated baseline (`bias`, logit). For a details view, not the main page. |
| `mode`, `runId` | `'truth'`, string | Truth mode: the 1920 census, published after the election |

### `GET /elections/:year/voters/:slice`

| Field | Meaning |
|---|---|
| `controlQuote` | What the person said in the world as it was (`quote` is what they said in the rerun's world) |
| `cohort`, `cohortAdults`, `weight` | The stratum the person was drawn from, how many adults it holds, and how many adults this one person stands for |
| `contextDate` | The date the person "lives" on: `1920-10-30` |
| `sources` | `[{ title, url, date }]`: the dated newspapers (loc.gov) in the person's brief |
| `model`, `promptVersion` | Which model spoke, and which prompt |
| `memorizationExposed` | `true` when the recall probe shows the model knows who won. Show a small "The model knows how 1920 ended" line. |
| `namesRestored` | Always `true`. The interview used neutral letters, and the candidates' names were put back afterwards. |
| `unchanged` | `true` when this person's vote didn't change. The harness always includes at least one such person per run. |

## 3. "How I got this"

Put a disclosure under the verdict, closed by default.

- Label: "How I got this" (sentence case, Title Case only if it becomes a
  button).
- Contents: `result.howIGotThis`, one line each, then the confidence line you
  already have. The lines already follow HANDOFF-SIMULATION §4's copy rules:
  - what exactly changed
  - whose behaviour the new voters borrowed
  - where the numbers come from
  - how sure

Ranges and draws fit into the existing bubble, so no new chrome is needed.
The verdict already ends with "Cox wins in 0 of 400 draws." Add one sentence
for the range, from the real 1920 bundle:
- `fifteenth`: "Across 400 reruns, Harding's electoral votes run 404–475."
- `no-19th`: "…run 417–429."

Use `range.A`, `range.B` and `drawsWon`. For the unchanged run, the range is a
single number. Say "Every rerun reproduces 1920 exactly" instead of a range.

**Map.** `pFlip` could set the flip pulse's strength: a strong pulse at
`pFlip ≥ 0.5`, a faint ring between 0.1 and 0.5. Only if it stays legible
at 12px tiles. Otherwise leave it out.

## 4. Validation

`result.validation.failed` lists pre-registered checks that failed, such as
`["B2", "L2"]`. Say so plainly in the About popover:

> This model is tested against held-out states and the 1920 women's-turnout
> record before it answers. It fails 4 of the 13 pass-or-fail checks. See the
> method.

These are the 1920 bundle's real figures: it fails B5, N1, N3 and A2.

Link to the method once it has a URL. Don't hide failures behind a
disclosure.

## 5. Copy corrections for sample.js / stories.js (yours to apply, or leave)

- **`no-19th` detail**: "Women can vote only in the fifteen states that
  already let them."
  - Fifteen is the number of full-suffrage states.
  - Twenty-seven states had given women the presidential vote by state action
    before ratification (Teele, from Keyssar's tables; AR and TX's 1917
    primary-only suffrage excluded).
  - The harness's wording: "Tennessee votes the suffrage amendment down, so
    women can vote for president only where their own state already let them."
- **Georgia and Mississippi**: women there could not vote in November 1920
  because registration closed first (NPS state pages). The sample's women
  slice treats them as voting.
- **New 1920 what-if key `league`** ("The Senate Ratifies the League",
  kind `issue`). The page needs nothing new for it. Its confidence is `low`.

## 6. The slices for 1920

The five groups are a partition, so every adult 21+ is in exactly one:

| Key | Group |
|---|---|
| `men` | Men outside the South |
| `women` | Women outside the South |
| `south-white` | White Southerners |
| `black-south` | Black Southerners |
| `immigrants` | Immigrants not yet citizens |

"The South" is the eleven former Confederate states. The keys used by the
sample's `no-19th` and `fifteenth` what-ifs are kept.

## 7. One thing to know before showing `fifteenth`

How Black voters split in 1920 is barely identified by state returns. With the
documented prior alone, the `fifteenth` rerun gives Harding 449 electoral
votes, not 416, and flips NC, AR, VA and AL in over half the draws.

The bundle's range (404–475) already carries that, so please show the range
for this what-if rather than only the point. `EVAL.md` has the
details.
