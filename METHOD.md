# Simulacra Americana: how the harness works

This covers the harness behind `/api/simulacra`.

- **This document:** every assumption, data source, equation and limitation.
- **`EVAL.md`:** what the 1920 prototype got right and wrong.

Tags follow the research package:
- **[V]** verified by download or fetched page
- **[S]** snippet or secondary
- **[I]** inference or assumption

## 0. The one design decision

**The counts come from a statistical model, and the language model is only the
voice.**

- **The backbone decides every number the page shows.** It is a calibrated
  statistical model of who could vote, who turned out and how they chose.
- **Every draw of the backbone reproduces each state's certified 1920 result
  exactly** (product promise 1).
- **The LLM agents do three jobs:**
  1. They supply the *response* to an issue what-if, as a within-agent paired
     difference.
  2. They supply the quotes.
  3. They cross-check the franchise what-ifs.

  They never supply a level: a count, a turnout rate or a vote share.

This matches what Aaru describes publicly: population and aggregate models
that are not language models, with LLMs as the reasoning and voice layer. It
goes further in three places:
- held-out tests with pass/fail thresholds
- error bars on every result

```
census tables ──► cells (state × sex × race/nativity/citizenship) ──► franchise rules ──► who can vote
                                   │
certified returns 1916, 1920 ──► backbone (turnout, choice; exact calibration; 400 posterior draws)
                                   │
                    ┌──────────────┼───────────────────────────┐
             franchise what-if   issue what-if             population what-if
             (backbone only:     (agents: control vs       (backbone + reapportion
              borrow a named      counterfactual, paired    from the counterfactual
              observed group)     difference, shrunk)       census)
                    └──────────────┼───────────────────────────┘
                                   ▼
                  draws → states, EV, ranges, "wins in n of D draws"
                                   ▼
                  api.js result shape (+ additive fields) ◄── quotes (selected, grounded, cited)
```

## A. Population

### A.1 Sources, 1920

**Adults 21+ by state × sex × race/nativity/citizenship.**
- The 1920 census (Fourteenth Census): the published "voting age" tables by
  colour, nativity and citizenship [V]. See the
  `harness_cache/population/PROVENANCE-population.md` for the pages and the
  checks.
- This is the published joint distribution of exactly the dimensions the 1920
  franchise turned on.
- The 1920 census was enumerated on 1 January 1920 and published in 1921–23,
  after the election. That makes it **truth mode**.
  - Strict mode would use the 1910 tables aged ten years (`extracts/`). It is
    designed but not run.

**1916 adults.**
- Geometric interpolation of each cell between the 1910 and 1920 counts, to
  7 November 1916.
- The 1920 counts are extrapolated to 2 November 1920 by the same rate.
- Interpolation between bracketing censuses is truth mode only; strict mode
  forbids it (toy_dataset_recipe §5.2).

**Urban share by state.** Used only for persona diversity.

### A.2 Cohorts

**Cells:** state (48) × sex × {native-born white, naturalized white, white
non-citizen (alien or first papers), Black, American Indian and Asian}.

**Why these dimensions in 1920:**
1. **Sex.** The 19th Amendment was the franchise shift of the year. Where women
   voted, they turned out at different rates from men, and possibly chose
   differently.
2. **Citizenship.** Non-citizens were barred almost everywhere. Naturalized
   voters were a distinct constituency.
3. **Race.** Black Southerners were kept from voting in practice, and Black
   voters elsewhere were a distinct, strongly Republican constituency.
4. **Region.** Region carried the parties' coalitions: the Solid South, the
   Republican North and the progressive West.

**Why not age or urban/rural.** Age, urban/rural and occupation vary within a
cohort's agents but don't define cohorts. No 1920 source identifies their
effect on turnout or choice, and a cohort nobody can calibrate adds cost and
no information.

**Agent cohorts** are region (5) × sex × group, merged to a cap of 36:
- **The merge rule** (`cohorts.py`): fold the smallest cohort into the same
  sex and group in the nearest region.
- The rule is deterministic, and the merged cohort's key names every region it
  holds.
- American Indian and Asian adults are too few per region to interview. They
  are counted by the backbone and have no agents.

### A.3 Eligibility

Every adult is a cell member. Nobody is dropped. Each cell has:
- a legally barred fraction, with a reason code;
- a practically excluded fraction, with a reason code.

| Reason | Rule, 1920 | Source |
|---|---|---|
| `noncitizen` | Aliens and first-paper declarants can't vote | Census citizenship tables [V]. Alien suffrage by state is **not coded** in the data. The harness assumes no state allowed declarant voting in November 1920 [I]. See the limitations. |
| `sex` | Only in the `no-19th` what-if, and only where the state had no presidential suffrage of its own | Teele (Keyssar tables) [V] |
| `registration_closed` | Georgia and Mississippi women couldn't register in time for November 1920 | NPS state pages, cited in `franchise/state_franchise_1920.csv` [V] |
| `native_status` | American Indian and Asian adults not counted as citizens | The census table where given; otherwise treated as eligible [I] |
| `extralegal_exclusion` (additive to the recipe's 13 codes) | Black Southerners kept from voting by poll taxes, literacy and "understanding" tests, white primaries and violence | Estimated. See B.1, T4. The legal devices by state come from Gray–Jenkins (`poll_tax`, `literacy_test`) [V]. |

Poll taxes also kept poor white Southerners from voting. The data can't
separate that from abstention, so for white Southerners it is counted as
"home", not "barred" (limitation 4).

### A.4 Uncertainty in the population

Each draw multiplies every cell by lognormal noise, standing in for census
undercount and interpolation error [I]. The coefficients of variation are
assumptions, not estimates:

| Group | CV |
|---|---|
| Native white | 2% |
| Naturalized | 4% |
| Non-citizen | 5% |
| Black | 5% |
| American Indian and Asian | 8% |
| 1916 interpolation (additional) | 2% |

The full-count path (`extracts/ipums-1920-fullcount.json`) replaces this with
bootstrap draws of the microdata tabulation.

## B. The backbone

### B.1 Turnout

For draw d, "adults" means legally eligible adults.

- **T1: the men's-turnout change, κ.** In the 12 "old" states (AZ CA CO ID IL
  KS MT NV OR UT WA WY), women could already vote for president in 1916 [V], so
  the legal electorate's makeup didn't change between 1916 and 1920. The
  change there is

  `k_s = logit(T20/E20) − logit(T16/E16)`

  κ is drawn from the predictive distribution: the mean across old states,
  plus the between-state spread.
- **T2: new states.** In the other 36, men's 1920 turnout is

  `m20 = expit(logit(T16 / M16) + κ)`

  Women's votes are the residual, `W = T20 − m20·M20`, and women's turnout is
  `w = W / F20`. This is the 1916 → 1920 natural experiment written as a
  model. Negative residuals are floored at zero and counted (diagnostic
  `women_negative_share`).
- **T3: old states.** Men and women are split with a ratio w/m drawn from the
  new states outside the South. There is no within-state evidence for it [I].
- **T4: Black Southerners.**
  - Run a Goodman regression of 1916 men's turnout on the Black share of
    eligible men across the eleven former Confederate states.
  - The implied Black rate is drawn from the regression posterior truncated
    to [0, white rate] (Goodman with Duncan–Davis bounds). The unbounded
    estimate is −0.18 ± 0.15.
  - The Black rate relative to the white rate is `t_rel`: median 0.09, 80%
    interval 0.01–0.25.
  - The fraction `1 − t_rel` of Black Southern adults is counted as excluded
    (`extralegal_exclusion`). The rest turn out at the white rate of their own
    state and sex.
- **T5: calibration.** A shift per state and sex makes the state's total votes
  match certified returns exactly.
  - Neither sex's turnout may exceed 98%; any excess moves to the other sex,
    so the state total holds.
  - Found when Utah failed R1 in 4 of 400 draws.

**Assumptions named here:**
1. Men's turnout changed from 1916 to 1920 by the same logit amount in new
   states as in old ones, give or take the old states' spread [I]. This is the
   key identifying assumption.
2. Within a state and sex, native-born, naturalized and Black voters outside
   the South turn out at the same rate [I].
3. Old states' women vote at the same ratio to men as women in new
   non-Southern states [I].

### B.2 Choice

- **C1: women's tilt, δ.** A regression across all 48 states of the change in
  logit Republican two-party share, 1916 → 1920, on f, the share of each
  state's 1920 votes cast by newly enfranchised women. It has South and
  non-South intercepts. It is re-fitted in every draw, because f depends on
  the turnout draw. δ is women's logit shift toward Harding relative to men of
  the same state (first-order).
- **C2: Black voters' shift, β_B.** This is the logit shift toward the
  Republicans relative to white voters of the same state.
  - Prior: N(1.5, 1.0) [I]. The literature documents Black voters' loyalty to
    the Republican party before 1932; the prior's size is an assumption.
  - The prior is updated by a Goodman regression across non-Southern states.
    The regression has **region intercepts** (Northeast, Midwest, West,
    Border) and the 1916 share.
  - The region intercepts were added after the first fit, whose single
    intercept let border-state swings stand in for race (β_B = −1.5; EVAL.md,
    deviation 3).
- **C3: calibration.** Per state, a Republican intercept and an "other"
  intercept are solved by iterative scaling. Each state's R, D and other votes
  then match the certified returns to within 1e-7 of the vote.
- **C3b: Black Southern voters.** They split like Black voters outside the
  South.
  - **Accounting bound.** Their votes for either party may not exceed 80% of
    that party's certified vote in the state.
  - Where the bound binds, their turnout is lowered, the difference is
    counted as exclusion, and the state's other voters of the same sex make up
    the total.
  - The rest of the state is then recalibrated.
  - The bound binds in South Carolina in 70% of draws (Harding got 2,610
    votes there) and in Mississippi in 18%.
- Naturalized voters' choice isn't separately identified in 1920. They share
  their state's intercept [I].

### B.3 Why these are the right tools for 1920

There is no survey before 1936, so MRP isn't available. The design follows the
recipe's rule for pre-survey elections: hierarchical ecological inference on
returns against census makeup, post-stratified exactly.

- **County EI (King's EI or a hierarchical model) is the next step.** It needs
  1920 county composition from NHGIS, which requires registration.
- **The state-level version here is honest about its identification:**
  - Every between-group difference is either identified by the 1916 → 1920
    change or labelled as an assumption.
  - Draws carry the uncertainty.

### B.4 Later eras (designed, not built)

- **1936–1947: MRP on Gallup and Roper.** The Berinsky–Schickler
  cleaned files are a benchmark only in strict mode.
- **1948 onward: MRP on ANES.** From 1964, CPS turnout by group. Always
  post-stratified exactly to certified state returns.
- **Before 1936: ecological inference** (this document).

## C. Uncertainty

A draw is:
1. a population draw (A.4);
2. a backbone parameter draw: κ, the old-state ratio, t_rel, δ, β_B and
   residual noise;

There are 400 draws per run. Reported:
- `result.range`: the central 80% of each candidate's EV.
- `result.drawsWon`: "Cox wins in 3 of 400 draws".
- `states[].marginRange` and `states[].pFlip`.
- popular vote point and range.

The unchanged run is exact in every draw. Its range is a point, by
construction.

## D. Validation

The metrics and thresholds are in `simharness/evaluate.py` and `benchmarks.py`;
`EVAL.md` has the results.

- **R1:** exact reproduction.
- **B1–B5:** 12 holdout states against persistence, uniform swing and a
  demographic regression.
- **N1–N3:** the 19th Amendment as a natural experiment, against
  Corder–Wolbrecht's hierarchical EI of women's turnout in CT, IL, MA, MI and
  NY. The benchmark is read only by `benchmarks.py`, and a test enforces that.
- **L1–L2:** leakage.
- **A1–A4:** agent-layer failure modes.

Failures are published in `result.validation` and in `EVAL.md`.

## E. Known limitations (read before citing)

1. **State-level only.**
   - There is no county composition without NHGIS registration.
   - Between-group differences in choice are weakly identified (δ, β_B), and
     their ranges are wide.
   - County returns are in the cache and unused, except as labels.
2. **Alien suffrage in 1920 isn't coded.** Declarant aliens are treated as
   barred everywhere. Keyssar's Table A.12 would settle it.
3. **Old states' women** (T3) borrow a ratio from new states; no within-state
   evidence.
4. **Poor white Southerners kept out by poll taxes** are counted as "home",
   not "barred".
5. **Truth mode.**
   - The 1920 census postdates the election.
   - Strict mode (1910 aged) is designed, not run.
