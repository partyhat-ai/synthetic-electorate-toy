# EVAL: the 1920 prototype

**Run.** Seed 1920, 400 draws, truth mode, the backbone alone (no agent
answers yet).

Every number below is copied from the run's `validation.json`.

## Summary

- **R1 fails in Utah in 4 of 400 draws.** A drawn men/women ratio implies
  men's turnout above 100%. The pre-registration counts any R1 miss as a
  failure of the build, so no what-if result can be published until it
  passes.

## Pre-registered checks

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

## Deviations from the plan, in order

Each change was made after seeing the output it fixes. Each is listed with
its effect. None changes a threshold.

2. **N1 denominator.** Corder–Wolbrecht's "eligible" counts equal the census
   21+ totals, non-citizens included. The backbone had divided by citizens.
   - Citizen-denominator result: MAE 9.6, coverage 40%.
   - Like-for-like result: MAE 3.3, coverage 60%.
   - Fail either way.
3. **β_B specification.**
   - The first fit's Goodman regression (intercept, lag) gave β_B = −1.5
     after the prior, driven by region.
   - Changed to region intercepts.

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
