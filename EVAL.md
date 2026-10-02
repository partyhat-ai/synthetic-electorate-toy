# EVAL: the 1920 prototype

**Run.** `runs/1920-bcbd86b43f`, seed 1920, 400 draws, truth mode, prompt p1.

Every number below is copied from `runs/1920-bcbd86b43f/validation.json` and
`analysis.json`.

## Summary

- **Reproduction is exact.** Every one of 400 draws reproduces each state's
  certified R, D and other vote to within 0.33 votes. Every draw gives 404–127.
- **The backbone beats its baselines on held-out states:**
  - two-party RMSE 7.6 points (uniform swing 8.7, persistence 17.4);
  - turnout RMSE 2.9 points (persistence 16.5);
  - Spearman 0.92;
  - Brier 0.052 (uniform swing 0.069).
- **It fails two pre-registered backbone checks:**
  - **B5.** It calls North Carolina for Harding.
  - **N1.** Its women's-turnout intervals are too narrow and run high in CT,
    MA and NY.
- **The 19th Amendment placebo passes.** In Georgia and Mississippi, where
  women couldn't register in time, the implied women's turnout is 2.1% and
  3.5%, near zero as it should be.
- **The agent layer:**
  - It is fully memorization-exposed: 56 of 56 probes named 1920, both
    candidates and the winner.
  - It follows platforms, not labels (label swap 0%).
  - It is **badly homogenized**: 90% of eligible cohorts answered unanimously.
  - It **overstates turnout** by about 12 points on average (15.5 points for
    women, N3).
  - Its paired effect for the League what-if has a stable sign across three
    paraphrases and two models.
- **The biggest uncertainty is β_B**, how Black voters split. The state
  returns can't identify it (see "The biggest uncertainty" below).

## Pre-registered checks

| ID | Check | Value | Threshold | Result |
|---|---|---|---|---|
| R1 | Unchanged rerun reproduces every state | max error 0.33 votes; EV 404–127 in 400/400 draws | ≤ 1 vote; exact EV | **Pass** |
| B1 | Holdout two-party RMSE | backbone 7.55; uniform swing 8.68; persistence 17.41; demographic 7.62 | ≤ uniform swing and persistence | **Pass** |
| B2 | Holdout turnout RMSE | backbone 2.92; persistence 16.46 | ≤ persistence | **Pass** (after a bug fix: see deviation 1) |
| B3 | Holdout Spearman | 0.923 | ≥ 0.8 | **Pass** |
| B4 | Holdout Brier | backbone 0.052; uniform swing 0.069 | ≤ uniform swing | **Pass** |
| B5 | Holdout EV error | 12 (predicted 160, actual 148; NC called for Harding: 55.1% predicted, 43.3% actual) | ≤ 0 (no holdout state was decided by < 5 points) | **Fail** |
| N1 | Women's turnout vs Corder–Wolbrecht | MAE 3.3 points; 3 of 5 inside the 90% interval | MAE ≤ 8 and ≥ 70% inside | **Fail** (coverage 60%) |
| N2 | Placebo, GA and MS | GA 2.1% (−1.8 to 5.5); MS 3.5% (−0.2 to 6.3) | within ±5 points of 0 | **Pass** |
| N3 | Agents' stated women's turnout vs Corder–Wolbrecht | MAE 15.5 points (11 women agents in 5 states) | ≤ 10 | **Fail** |
| L1 | Recall probe | year 100%; candidates 100%; winner 100% (n = 56) | reported | 1920 is **memorization-exposed**, as expected |
| L2 | Label swap | follows label 0%; follows platform 100% (n = 39) | < 20% | **Pass** |
| A1 | Cohort bias | median \|bias\| 0.41 logit; 0 cohorts over 1 logit (after smoothing); mean TVD 0.43 | reported | See below |
| A2 | Homogenization index | 0.90 (21 eligible cohorts) | ≤ 25% | **Fail** |
| A3 (`league`) | Paraphrase and model sensitivity | effect −0.091; paraphrase SD 0.054; Sonnet −0.18 vs Opus −0.03 (shared subsample) | SD < \|effect\|; signs agree | **Pass** (the models agree on sign, not size) |
| A3 (franchise) | same | no Opus arm for backbone-mode what-ifs | — | Not run (not applicable: these effects aren't applied) |
| A4 | Stereotype audit | 0 of 66 reasons flagged by the heuristic | ≤ 10% | **Pass** (heuristic only; not read by a person) |

**Score:** 9 passed, 4 failed (B5, N1, N3, A2); L1 and A1 are report-only.

### N1 detail

Women's turnout, as a share of all women 21+ (Corder–Wolbrecht's
denominator):

| State | Backbone (90% interval) | Corder–Wolbrecht (95% interval) | Method |
|---|---|---|---|
| CT | 36.7 (32.7–41.4) | 32.6 (28.1–35.9) | residual |
| IL | 46.3 (33.1–55.5) | 45.6 (44.3–46.8) | ratio (IL women voted in 1916) |
| MA | 39.3 (34.6–44.1) | 33.6 (32.2–34.9) | residual |
| MI | 37.2 (32.0–43.2) | 40.6 (38.5–42.4) | residual |
| NY | 37.7 (33.1–42.7) | 35.2 (33.8–36.3) | residual |

- **The residual method runs high in the East.** κ, the men's-turnout change
  from 1916 to 1920, comes from the western "old" states, where turnout per
  eligible adult fell 0.31 logit. If men's turnout fell further in the East,
  the residual hands too many votes to women.
- **This is the key identifying assumption, and N1 is where it shows.** The
  fix is to estimate κ with regional variation, with county returns: the
  Corder–Wolbrecht approach.

## Leakage

- **Probes (L1).** A separate instance, given the blinded brief, named 1920,
  Cox for the administration's party, Harding for the other, and Harding as
  the winner in 56 of 56 probes.
  - Blinding does not hide 1920 from a current model, and no current model
    will be clean for 1920.
  - Every quote is therefore flagged `memorizationExposed: true`, and cohort
    bias uses the national bias (pre-registered rule).
- **Label swap (L2).** In all 39 usable pairs, the agent followed the platform
  to its new label. Answers track positions, not letters.
- **De-blinding in the voice.** 98 of 386 voter answers (25%) name a party
  ("I'll vote Republican", "the Lincoln ticket") that no brief ever named.
  - None names a candidate.
  - None uses hindsight language ("landslide", "will win").
  - A party name in a quote is the model's own inference, now documented.
- **Dates.**
  - Every source item is dated 1920-06-01 to 1920-11-01.
  - p1 briefs were dated 30 October but could include items from 31 October
    and 1 November (deviation 11). A subagent noticed one and didn't use it.

## Agent layer, beyond the thresholds

- **Turnout overstatement.** Agents' stated turnout exceeds the backbone's
  calibrated turnout by 11.8 points on average.
  - Northeastern native men: 0.76 vs 0.60.
  - Southern white men: 0.61 vs 0.36.
  - Figures are half-count smoothed (deviation 8).

  This is the survey self-report bias in a new form. It's harmless here,
  because levels come from the backbone, but it's why agents must never set
  levels.
- **Cohort bias (A1).** Agents' Republican two-party share is within ±0.5
  logit of the backbone for most white cohorts.

  | Cohort | Bias (logit) |
  |---|---|
  | border:F:black | +0.92 |
  | south:F:black | −0.86 |
  | south:M:native_white | −0.76 |
  | south:M:black | −0.61 |

  - Before half-count smoothing (see deviation 8), Black cohorts outside the
    South ran +0.8 to +1.6. The agents say "strongly Republican", which fits
    the documented history better than the backbone's weakly identified β_B.
    See the next section.
  - Southern white men: agents 23% Republican (smoothed) vs backbone 39%. The agents
    voice the Solid South; the backbone averages in Tennessee and North
    Carolina, where Harding took about 43% or more.
- **Homogenization (A2).** In 19 of 21 cohorts whose backbone share lies
  between 0.2 and 0.8, every agent gave the same choice. With four agents at
  a 60/40 split, chance unanimity is about 15%, so this is strong variance
  compression. The Bisbee et al. failure is present. Persona diversity at
  four agents per cohort didn't fix it, and Sonnet 5.5 has no temperature
  lever.
  - Consequences for this design: the agents' choices are not usable as
    distributions. Their *paired changes* can still be. Production should
    ask for `p_choice` (done), weight by it rather than by the discrete
    choice (done), and raise agents per cohort to 12 or more to measure
    compression properly.
- **Paired effect, `league`.**
  - The national two-party effect is −0.091 logit, 80% interval −0.129 to
    −0.047, adult-weighted.
  - Cohort effects run from −0.24 (naturalized men in the Northeast) to +0.13
    (Southern white men).
  - The shrinkage weights are 0.33–0.43, because four or five agents per
    cohort is small against the pre-registered pseudo-count of 8. Every
    cohort's effect is therefore pulled strongly toward its region.
- **Cross-checks on the franchise what-ifs.** These are not applied.
  - In `fifteenth`, Black Southern agents who could now register raised their
    stated turnout sharply: +0.93 logit nationally for the reached cohorts.
    Their quotes back the borrowed assumption: "I'm registered. I'll vote
    Republican Tuesday, same as my people."
  - In `no-19th`, women who lost the vote said so. The men asked showed a
    small shift toward Cox (−0.12 logit), which the backbone ignores by
    design.

## The biggest uncertainty: how Black voters split

- **The data can't pin β_B.** Across the 37 states outside the South, a
  Goodman regression puts Black voters' shift toward Harding at −3.4 ± 1.9
  logit (region intercepts, 1916 lag). That runs against the documented
  history, and it is carried by six border states with larger Black shares
  and smaller swings.
- **What the run uses.** The pre-registered prior, N(1.5, 1), updated by
  that regression, gives a median of 0.50 (80% interval −0.70 to 1.68).
- **The sensitivity**, same seed:

| β_B from | Black voters outside the South, Harding share |
|---|---|
| Prior updated by Goodman (used) | 73% (48–88%) |
| Prior only, N(1.5, 1) | 88% (67–96%) |

- **Which is closer to history?** The prior-only row encodes the
  documented loyalty of Black voters to the Republican party before 1932. The
  used row lets the confounded regression pull it down.
- **What would settle it:** county returns against county composition (NHGIS,
  needs registration), or a documented estimate of Black voters' choice in
  1920 from the literature (not found by the research agents).

## Uncertainty budget

These are standard deviations across draws.

| What-if | National R two-party (points), full | Backbone parameters only (population noise off) | Agents only (one backbone draw) | Harding EV SD, full / params only |
|---|---|---|---|---|
| `no-19th` | 0.48 | 0.51 | — | 6.6 / 7.0 |
| `fifteenth` | 0.55 | 0.56 | — | 27.4 / 22.9 |
| `league` | 0.78 | 0.78 | 0.79 | 6.6 / 6.5 |

**How to read this:**
- **Population noise is a small part of every what-if.** Turning it off
  barely changes the spread, and the full-draw SD for `fifteenth`'s EV
  (27.4) exceeds the params-only SD (22.9) only by what the flip-prone
  Southern states add.
- **For `league`, almost all the spread comes from the agent layer.** The
  calibrated baseline has no national spread, so only the agent bootstrap
  varies.
- **For `fifteenth`, β_B dominates.**

## Deviations from the plan, in order

Each change was made after seeing the output it fixes. Each is listed with
its effect. None changes a threshold.

1. **B2 predictor bug.** The holdout turnout predictor counted old-suffrage
   states' 1916 votes, which included women's, as men's.
   - First value: 16.90 (fail).
   - Fixed to project turnout per eligible adult by κ, as the backbone does:
     2.92 (pass).
   - Both values are reported here.
2. **N1 denominator.** Corder–Wolbrecht's "eligible" counts equal the census
   21+ totals, non-citizens included. The backbone had divided by citizens.
   - Citizen-denominator result: MAE 9.6, coverage 40%.
   - Like-for-like result: MAE 3.3, coverage 60%.
   - Fail either way.
3. **β_B specification.**
   - The first fit's Goodman regression (intercept, lag) gave β_B = −1.5
     after the prior, driven by region.
   - Changed to region intercepts: 0.50 after the prior.
   - The sensitivity table above covers the choice.
4. **Black Southern turnout.** The first fit clipped a negative Goodman
   estimate to 0 in every draw. Changed to the regression posterior truncated
   to [0, white rate], which is Goodman with Duncan–Davis bounds: median 9%
   of the white rate (1–25%).
5. **Black Southern choice.** The first fit gave Black Southern voters a
   shift relative to white Southerners, which made them lean Cox, against the
   `fifteenth` assumption.
   - Changed to the borrowed Northern split, with an accounting bound: their
     votes for either party are at most 80% of its certified vote.
   - The bound binds in South Carolina (70% of draws) and Mississippi (18%).
6. **Sex turnout cap.** R1 first failed in Utah in 4 of 400 draws: a drawn
   men/women ratio implied men's turnout above 100%. Each sex is now capped at
   98%, and the excess moves to the other sex, so state totals stay exact.
7. **Minor-party ledger.** R1 failed again after deviation 5: in NC and GA,
   whose certified minor-party vote is 0, the borrowed Black split carried a
   minor-party share. Fixed; R1 passes.
8. **Paired smoothing.** Cohorts whose agents all said "won't vote" produced
   effects of −10 logit. A half-count (Jeffreys-style) smoothing was added,
   and the national effect is now adult-weighted.
9. **A1 denominator.** Backbone turnout for A1 is now per legally eligible
   adult (exclusion included), matching what an agent's `p_vote` means.
10. **The agents were answered by Claude Code subagents, not the Messages
    API.**
    - No `ANTHROPIC_API_KEY` was available. Credential exploration was
      declined, correctly.
    - The 442 requests went through the `transcript` backend to 9
      subagents: 7 Sonnet and 2 Opus, via the Agent tool's `model`
      setting. The exact model versions behind those settings aren't
      recorded by the tool.
    - Each subagent answered 18–59 requests in one context. No subagent saw
      both arms of the same person.
    - The subagents' own reports:
      - The probe subagent answered 28 of 56 probes by script, having read
        the first 28. All 56 name Harding.
      - The control-sonnet-2 subagent built answers with a helper script.
        All 56 reasons and quotes are distinct.
      - The control-sonnet-1 subagent says its later answers are shorter and
        more generic. Its quotes fall from 26 to 16 words.
    - This is a weaker instrument than independent API calls. The
      homogenization in A2 may be partly an artifact of batching.
    - **The production path is `anthropic-batch`**, and this pilot should be
      rerun on it before any agent-layer number is cited.
11. **p1 prompt bugs,** found after the answers came back and fixed in p2.
    The p1 requests that were answered are unchanged on disk.
    - Non-citizen women were given the `no-19th` counterfactual, and their
      brief contradicted itself. Two subagents flagged it. Those pairs are
      excluded from the analysis.
    - Briefs were dated 30 October while admitting items dated up to
      1 November.
    - Surnames were drawn from one mixed list ("Mary Lindqvist", a Black
      North Carolina woman).
    - Before any answer, the Ohio line "women have voted for president since
      1917" was corrected: no presidential election fell in 1917–19.

## What wasn't done

- **County-level ecological inference.** County returns are cached; county
  composition needs NHGIS registration.
- **Strict mode.** The 1910 census would be aged ten years.
- **Other holdouts.** The 26th Amendment, VRA and Amendment 4 holdouts are
  designed but not run.
- **Population what-ifs.** Huntington–Hill and Webster are implemented and
  unit-tested, but not exercised.
- **Reading the stereotype audit.** A4 used the regex pass only.
- **Alien declarant voting in 1920.** Not coded in any dataset found; treated
  as barred everywhere.
