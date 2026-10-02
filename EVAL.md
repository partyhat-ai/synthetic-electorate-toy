# EVAL: the 1920 prototype

**Run.** Seed 1920, 400 draws, truth mode, the backbone alone (no agent
answers yet).

Every number below is copied from the run's `validation.json`.

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
- **The agent checks (N3, L1, L2, A1–A4) are not run:** there are no agent
  answers yet.
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

**Score:** 6 passed, 2 failed (B5, N1). N3, L1, L2 and A1–A4 wait for the
agent layer.

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

## The biggest uncertainty: how Black voters split

- **The data can't pin β_B.** Across the 37 states outside the South, a
  Goodman regression puts Black voters' shift toward Harding at −3.4 ± 1.9
  logit (region intercepts, 1916 lag). That runs against the documented
  history, and it is carried by six border states with larger Black shares
  and smaller swings.
- **What the backbone uses.** The pre-registered prior, N(1.5, 1), updated by
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
   shift relative to white Southerners.
   - Changed to the borrowed Northern split, with an accounting bound: their
     votes for either party are at most 80% of its certified vote.
   - The bound binds in South Carolina (70% of draws) and Mississippi (18%).
6. **Sex turnout cap.** R1 first failed in Utah in 4 of 400 draws: a drawn
   men/women ratio implied men's turnout above 100%. Each sex is now capped at
   98%, and the excess moves to the other sex, so state totals stay exact.
7. **Minor-party ledger.** R1 failed again after deviation 5: in NC and GA,
   whose certified minor-party vote is 0, the borrowed Black split carried a
   minor-party share. Fixed; R1 passes.

## What wasn't done

- **County-level ecological inference.** County returns are cached; county
  composition needs NHGIS registration.
- **Strict mode.** The 1910 census would be aged ten years.
- **Other holdouts.** The 26th Amendment, VRA and Amendment 4 holdouts are
  designed but not run.
- **Population what-ifs.** Huntington–Hill and Webster are implemented and
  unit-tested, but not exercised.
- **Alien declarant voting in 1920.** Not coded in any dataset found; treated
  as barred everywhere.
