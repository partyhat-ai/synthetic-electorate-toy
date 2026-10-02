# Validity: goals, contamination, leakage and historical bias

This document takes stock of the Simulacra Americana harness:
- what it is trying to do;
- what is currently claimed;
- what can and can't be known about whether those claims hold;
- what would make them stronger.

It was written after the work that made typed what-ifs, historical evidence and 1924 run end to end. It complements:
- `METHOD.md`: how the model works;
- `EVAL.md`: the 1920 prototype's scores;
- `DISCLOSURES.md`: the running log of every known flaw.

IDs in brackets (D21, C14, H4…) refer to `DISCLOSURES.md`.

---

## 1. The goal

A reader picks a past presidential election, changes one thing about it, and asks what would have happened. The harness should:

1. **Model any change a reader can type,** however far-fetched.
2. **Ground every answer in the record.** Use real populations, real voting rules and real certified results. Use evidence of how the same people behaved in the same or similar situations.
3. **Say how much to trust the answer.** "Extremely low confidence, and here is why" is an acceptable answer. A confident wrong one is not.

The third goal is the hard one. Everything below is about whether the harness can honestly meet it.

---

## 2. What the system is

Two layers, plus an evidence step.

### 2.1 The statistical layer (the backbone)

Each election is about 600 cells: state × sex × group (native-born white, naturalized, non-citizen immigrant, Black, American Indian and Asian). Each cell carries, for each of 100 posterior draws:

> adults × share who could vote × share who turned out × the split between candidates

It is built from four kinds of input:
- **Census counts:** 1920 from the census volumes; 1924 is the 1920 count aged along each cell's trend (C13).
- **Each state's voting rules:** Gray–Jenkins, Teele.
- **Certified returns:** Algara–Amlani, Clerk of the House, NARA.
- **A source of identification for group differences:** what lets the model tell how groups differed.
  - **1920:** the 1916 → 1920 natural experiment. Women could already vote for president in some states in 1916 and not in others.
  - **1924:** carries 1920's structure forward (C14).

**Exact reproduction.** Every draw is calibrated so that the unchanged world reproduces each state's certified votes, to within half a vote:
- 1920: worst error 0.32 votes, 404–127 in every draw;
- 1924: worst error 0.41 votes, 382–136–13 in every draw.

Everything a what-if changes is therefore measured from the real result. The draws differ only in how a state's known total breaks down by group. That breakdown is inferred, and the uncertainty lives there.

**What exact reproduction proves: very little.** It is enforced by construction. A model could match Ohio exactly with a badly wrong split between men and women. Only checks the model never sees can test the splits (§4).

### 2.2 The interview layer (the voters)

Invented people are drawn from documented groups, in proportion to real counts. Each gets a brief dated the day before the election. The brief contains:
- **Circumstances:** age, place, household economy, eligibility under their state's rules.
- **News:** two to four dated newspaper excerpts. This exists for 1920 only (C15).
- **A blinded ballot:** neutral letters in a random order, each with a neutral description and three platform planks paraphrased from the parties' own texts.

Each person answers twice:
- **in the world as it was;**
- **with the change written into their world as settled fact.**

The answer is never phrased as a hypothesis. The paired difference, per group, becomes a shift on that group's cells:
- shrunk toward the region's average when there are few people;
- shrunk further when the group's control answers stray from the calibrated record.

### 2.3 The evidence step (per typed what-if)

1. **Compile.** A model call turns typed words into a structured change of one of these kinds:
   - who can vote;
   - how many people;
   - an issue or event;
   - news about one nominee;
   - a new candidate;
   - a third candidate withdrawing.
2. **Research.** A second call searches the web for scholarship, official statistics and archives. It looks for how the same people behaved in the same or similar situations.
3. **Extract and grade.** A third call extracts findings. Each must cite a page the search returned. Each is graded by source tier × similarity, and mapped by role, not party label (D20, D22).
4. **Use the evidence:**
   - **Compare.** Set it against the interviews (corroborated, consistent, contradicted or untested).
   - **Prior.** Use it as a weak prior on the effect, for exploratory what-ifs only.
   - **Confidence.** Set a confidence tier (high, medium, low, very low) with reasons.

The evidence never enters a voter's brief.

---

## 3. What each year's data does

| Data | Election analysis | Interviews | What-ifs |
|---|---|---|---|
| **Certified returns** (state; county held for checks) | The calibration target; the baseline every change is measured from | None | Flips are crossings of real margins |
| **Population cells** | Denominators; how a state's total is composed | Who is drawn, from where, and how many people each stands for | Changes to who can vote act on specific cells |
| **Voting rules** | Who could vote; the barred share | The eligibility line in each brief | Franchise changes switch rules on or off |
| **Identification** (the natural experiment, or the base year) | How a state's total splits between groups | None | Decides how much a group change matters |
| **Profile** (names, descriptors, labels, day) | Names restored on output | The blinded ballot | Names masked in compiled facts |
| **Platforms** | None | Ballot planks | Planks dropped or added |
| **Dated newspaper corpus** | None | What each person has lately read | Contradicted items removed |
| **Benchmarks** (Corder–Wolbrecht, held-out states) | Scoring only, never fitting | Scoring only | None |
| **Historical evidence** (per what-if) | A weak prior; the confidence tier | Never shown | Agreement and reasons |

A year's data quality sets its confidence ceiling:
- **1920:** has a natural experiment, its own census, a newspaper corpus and held-out checks.
- **1924:** borrows its structure and has no newspapers.
- **1932 onward:** will start a tier lower again, until each has its own identification and checks.

---

## 4. Checks the model never sees (held-out validation)

### 4.1 Principles

1. **What is held out.** Real observations kept from everything used to build or tune the model.
2. **How it is kept out:**
   - **Fixed in config and code.** The held-out set (`configs/`), the metrics and the thresholds (`evaluate.py`, `benchmarks.py`) are set before a run reads them. For 1920 there is no verified record of when they were fixed.
   - **Kept apart in code.** The fit runs where it cannot read benchmark files. Today a unit test enforces that only `evaluate` reads `benchmarks/`.
   - **Inputs that encode the outcome are removed** by allowing known-good columns by name, not by blocking known-bad ones. Gray–Jenkins carries `turnout` and `gopresult`.
   - **A final test set** is opened once, at the end.
   - **Changes after looking are logged.** Every change made after looking is a deviation and goes in `DISCLOSURES.md`, and whatever was tuned on stops counting as unseen.
3. **How it is scored:**
   - **Score whole distributions,** not just point errors: a log score or CRPS for shares, a Brier score for state winners.
   - **Measure coverage:** do the stated 80% ranges contain the truth about 80% of the time?
   - **Compare with simple baselines:** "same as last time", uniform swing, a demographic regression. Report the gain over them, not raw error.
   - **Report every check, including failures.**

### 4.2 Inventory: what exists and what doesn't

| Check | Tests | Status |
|---|---|---|
| R1 exact reproduction | Calibration only | Built, any year (`run verify`) |
| Held-out states (B1–B5) | Model structure | Built for 1920; some fail (`EVAL.md`) |
| Corder–Wolbrecht women's turnout (N1) | The men/women split | 1920: MAE 3.2 points; 1924: 3.6 (held out) |
| Held-out counties | The group splits, about 3,000 tests | **Not built.** County returns are on disk; county census tables need one free NHGIS extract |
| Forecast mode for carried-forward years (1924 before calibration) | Whether the borrowed structure holds | **Not built** |
| Survey benchmarks (Gallup 1936+, ANES 1948+, CPS 1964+) | Group splits directly | **Not built.** Applies to later years only |
| Statistical-layer backtests (fit on 1916, predict 1920 group turnout) | The backbone's what-if machinery | **Not built.** Clean (§5.5) |
| Interview diagnostics | The interview layer's behaviour (not its accuracy) | Built: recall check L1, label swap L2, interview–record gap A1, sameness A2, wording stability A3, stereotype audit A4, Sonnet/Opus comparison D8 |
| Calibration of the confidence tiers | Whether "low" errs more than "high" | **Not built.** The tiers are hand-written rules (H4) |

---

## 5. Contamination: the language model knows how it ended

### 5.1 The problem

A brief dated "Monday, 1 November 1920" restricts what the model is told. It does not restrict what the model knows. A language model cannot unlearn; "you don't know the future" is a request, and it leaks.

"A world before the event" in this harness is therefore an information-restricted prompt. It is not a knowledge-restricted voter. **It has not been shown that the interviews behave like uncontaminated 1920 people. The evidence says they don't.**

### 5.2 Evidence of contamination we have seen

| Observation | Where | What it shows |
|---|---|---|
| The recall check named 1920, both candidates and the winner at 95% confidence from a blinded brief | D9, L1 | Blinding by letters and descriptors is defeated by context |
| A flu-scenario quote said "That fellow Cox" from a blinded brief | D18 | Names leak into answers |
| In the first Harding-disclosure run, most interviewed people blamed Cox for Harding's disclosure, a spurious 7.8-point move toward Harding | D21 | The outcome can shape reasoning: a disqualifying scandal "fits" the loser |
| Quotes say "the Republican" while the brief only gives letters | D19, D23 | The model maps labels to parties itself, sometimes wrongly |
| Every region's reaction to the Harding disclosure lands at about the same Harding share (0.31–0.33) | D23 | One model-level reaction stamped on everyone, not group behaviour (sameness, A2) |
| Interview answers for "No La Follette" send 80% of his voters to Davis; the record is mixed | D24 | Possibly the model's narrative of 1924, not voters' behaviour |

### 5.3 How contamination can bias results

- **Anchoring on the outcome:** control answers lean toward the real winner. This is measured as the interview–record gap (A1).
- **Outcome-shaped reactions:** a change is read through what the model knows came next. Unlike constant biases, this does not cancel in the paired difference.
- **Narrative substitution:** the model reproduces the textbook story ("return to normalcy", "the League hurt Cox") instead of reasoning from the person's circumstances.
- **Sameness:** one modern model voices every group, flattening differences between groups (A2, D23).
- **Modern values projected backwards:** reactions to sexuality, race, religion or women's roles may reflect current norms, or caricatured past ones, rather than period attitudes.

### 5.4 Compensating measures in place

They reduce or measure the bias; none removes it.

1. **Paired differences.** A bias common to both answers (leaning toward Harding because the model knows he won) largely cancels. Interactions between knowledge and the change do not.
2. **The statistical layer carries the counts.** Vote totals, turnout and exact reproduction use no model answers. Interviews only supply shifts.
3. **Shrinkage by interview–record gap.** A group whose control answers stray from the calibrated record has its shift pulled toward its region's average (pre-registered, `paired.py`).
4. **Blinding.** Letters instead of names, neutral descriptors, and corpus items that name a candidate excluded. Partial at best (D9).
5. **Manipulation check (p5).** For news about one nominee, each answer states which candidate the news concerns. Misreaders are dropped, counted and flagged; half or more forces "extremely low" (D21).
6. **Label swap (L2).** Platforms trade labels and the order flips; choices should follow the platform, not the label.
7. **Disclosure.** The page carries `memorizationExposed`, and every result carries its confidence tier and reasons.

### 5.5 What this means for backtests

- **Statistical-layer backtests are clean.** Fitting the population model on 1916 and predicting 1920 involves no language model. The remaining risk is choices made by people who know history, and pre-registration handles that.
- **Interview-layer backtests on events before the model's training cutoff are not clean.** Running "women can vote" through the 1916 world, the model already knows about a third of women voted in 1920. A good score could be memory, not modelling.

So the interview layer cannot be validated on most of American history with today's models. It can be tested in other ways (§7).

---

## 6. Leakage (beyond the model's memory)

| Kind | Where it enters | Status |
|---|---|---|
| **Data published after the election** | Truth mode uses later census tables and compilations; strict mode would use only what existed before election day | 1920 runs in truth mode. The research notes define strict mode (`toy_dataset_recipe.md` §5); not implemented |
| **Outcome-encoding input columns** | Gray–Jenkins `turnout` and `gopresult`; County Data Book election variables | The harness reads only named columns. Formalize as an allowlist test |
| **Evidence describing what happened** | Research for a what-if reads historians who know the outcome (e.g. "the League hurt Cox") | Evidence never enters briefs, but it does set priors and confidence. Acceptable for an evidence prior; it must not be mistaken for an independent check |
| **People choosing after looking** | Prompt versions (p1→p5), compiler versions (c1→c3), confidence rules and hand-edited specs were all changed after seeing results | Every one is logged (D11–D24, E5, H4). These choices can't also count as validation |
| **Shared answers across runs** | The answer cache reuses identical requests | By design (G4). Harmless for estimates; a test set must not be re-asked until it looks right |
| **Benchmarks used to tune** | Corder–Wolbrecht guided the N1 denominator fix in 1920 | Logged in `EVAL.md`. N1 for 1920 is no longer fully held out; 1924's comparison was made once, after the fit |

---

## 7. Historical bias (the record itself)

Clean statistics on a biased record give clean-looking bias.

1. **Who was counted:**
   - **Census undercount.** The census undercounted Black, immigrant and poor rural people. Population draws add noise by group (e.g. 5% for Black adults) but not a directional correction.
2. **Who could vote, and who is invisible:**
   - **Disenfranchised groups.** Black Southerners and non-citizens appear mostly as "couldn't vote". Their political preferences are borrowed from other groups ("split like Black voters outside the South").
   - **Borrowing is an assumption.** It is the harness's assumption, not something observed.
3. **What the newspapers say.** Chronicling America over-represents some papers, places and owners. Its selection, by topic and by keyword, was made by the harness.
4. **What historians emphasize.**
   - **Narratives.** Scholarship carries its own framings and emphasizes some groups, such as German and Irish defections over the League.
   - **Popular sites.** The research step weights sources by type, but much of what it finds is popular history or Wikipedia (H2), which repeats familiar stories.
5. **What the language model learned.**
   - **Popular retellings.** Its knowledge of 1920 comes mostly from modern retellings, not period sources. It is likely to reproduce the dominant narrative and modern framings.
   - **Stereotyped voice.** Period-voice quotes risk caricature. The stereotype audit (A4) flags reasoning from group labels, and the system prompt forbids it; neither guarantees period realism.
6. **Values.**
   - **Period attitudes are part of the history.** Hostility to homosexuality in 1920, for example, belongs in the model.
   - **The risk runs both ways.** Reproducing period prejudice as if it were the voters' own words, or erasing it with modern sensibilities. The pipeline doesn't distinguish these yet.
7. **Selection of what-ifs.** Readers ask about famous people and dramatic changes. The evidence base, and the model's fluency, are strongest exactly where the textbook narrative is strongest.

---

## 8. What's claimed, honestly

| Claim | Status |
|---|---|
| The unchanged rerun reproduces each election | **True by construction;** verified every run |
| The population, voting rules and returns are the documented record | **True, with sources.** Each file has its provenance; the 1920 tables match their printed totals (C5) |
| The split of each state's vote between groups is right | **Partly tested.** Women's turnout is within about 3–4 points in five states (1920 and 1924); other groups are mostly untested |
| Franchise and population what-ifs are reliable | **As reliable as their stated borrowing assumption** (e.g. "split like Black voters outside the South"). High confidence is about the arithmetic, not the assumption |
| Issue, event and candidate what-ifs reflect 1920 voters | **Not shown.** They reflect a knowledgeable model reasoning about documented circumstances, with contamination measured, partly cancelled and disclosed |
| The confidence tiers are calibrated | **No.** Hand-written rules (H4), not yet scored against outcomes |
| Historical evidence corroborates an answer | **Sometimes, for direction** (flu turnout: interviews −7.4 points, 1918 about −11 ± 5). Rarely for size; often untested |

---

## 9. Next steps

### 9.1 Prove what the interviews respond to (contamination)

1. **Planted-truth tests (synthetic worlds).**
   - **Setup.** Build an invented country with invented parties, history, newspapers and an electorate whose group behaviour we design and bury in their circumstances.
   - **Test.** Does the pipeline recover the planted behaviour, and the planted effect of a planted change?
   - **Why it works.** No model can remember a world that never existed, so this measures reasoning from the brief rather than recall.
   - **Cost.** A few dollars per round.
2. **Cue-shift tests.**
   - **Setup.** Give the same people briefs with the historical cues altered: dates shifted, fictional newspapers, planks swapped, a fictional state.
   - **Test.** If answers don't move when the brief does, they come from memory.
   - **Scale.** The label swap (L2) is a small version of this.
3. **Outcome-flip test.** Give one arm a brief whose fictional backdrop implies the opposite outcome, such as polls and newspapers favouring the real loser. Then measure how far answers follow the brief versus the known history.
4. **Recall check on every run, every year,** with results shown per group and fed into confidence as a standing reason, not an occasional flag.
5. **Score memory against reasoning per what-if.** Combine the above into a per-change index ("how much of this answer could be recall"). Make it an input to the confidence tier.

### 9.2 Test the statistical layer (clean)

1. **Held-out counties** for 1920 and 1924. This is the strongest available test of group splits. It needs an NHGIS county extract; the returns are on disk.
2. **Forecast mode for carried-forward years.** Score 1924's prediction from 1920's structure before calibration.
3. **Backbone backtests on real changes,** with no language model involved:
   - suffrage 1916 → 1920;
   - the VRA, 1964 → 1968/72;
   - the 26th Amendment, 1968 → 1972.
4. **Survey benchmarks for later years:** Gallup 1936+, ANES 1948+, CPS 1964+, as benchmarks only.
5. **Baselines and proper scoring.** Every check reports skill over "same as last time" and uniform swing, plus coverage of the 80% ranges.

### 9.3 Tests that can't be contaminated

1. **Prospective, pre-registered forecasts.** Before a future election, primary or known upcoming change, register a prediction made by the full pipeline, then score it afterwards. This is the gold standard.
2. **Elections after a model's training cutoff.** For 2024, run the interviews with a model whose training ended before November 2024 (the research notes cite some Llama models). It would be weaker, but clean.
3. **Period-only language models (research).** Train or fine-tune only on text dated before the event (e.g. Chronicling America to 1920).
   - **Limits.** Fine-tuning a modern model doesn't erase what it knows; training from scratch on period text gives a much weaker model.
   - **Status.** Worth tracking, not building now.

### 9.4 Reduce bias where it's known

1. **Less sameness.**
   - More people per group: the current 2 is far below the pre-registered 4–6.
   - Several models: Sonnet, Opus, Haiku and a non-Anthropic model.
   - Persona detail from IPUMS microdata (occupation, literacy, home ownership) instead of imputed economy.
   - Measure group spread (A2) on every run.
2. **Regional, evidence-anchored transfers** for candidate withdrawals and entries (D24). Use where La Follette's voters actually went (1928) as a prior.
3. **Period corpora for every year:** pull Chronicling America items for each year (C15), with balance across regions, parties and the Black and immigrant press.
4. **Separate period attitudes from model attitudes:**
   - give briefs explicit, sourced period context on contested issues;
   - audit quotes for both anachronistic modern framing and caricature.
5. **Correct for undercount:** apply published undercount estimates by group as a directional prior, not just noise.
6. **Strict mode:** implement before-election-only data (`toy_dataset_recipe.md` §5), at least for the population and the briefs.

### 9.5 Process

1. **Pre-register each new year** (starting with 1932) before its data is opened: held-out states, counties and benchmarks, metrics and thresholds.
2. **Calibrate the confidence tiers** against the backtests and planted-truth tests, then freeze the rules. Until then, keep calling them uncalibrated (H4).
3. **Keep the working modes separate.** Shipping fixes fast and validation runs are different activities. Validation is run deliberately, once, on locked sets, and is never re-run until it passes.
4. **Keep logging.** Every post-hoc change goes in `DISCLOSURES.md`.

### 9.6 Suggested order

| # | Step | Why first | Rough cost |
|---|---|---|---|
| 1 | Planted-truth test | The only direct answer to "is it reasoning or remembering?" | A few dollars; a day |
| 2 | Cue-shift test on the 1920 interviews | Cheap; quantifies memory against brief | Under $1 |
| 3 | Held-out counties, 1920 and 1924 | Strongest test of the statistical layer | Free (NHGIS); a day |
| 4 | Pre-registration template per year, then 1932 | Keeps every new year honest from the start | An hour |
| 5 | Backbone backtest 1916 → 1920 | Clean test of what-if machinery | Free |
| 6 | Confidence-tier calibration | Turns hand-written rules into measured ones | Follows 1, 3 and 5 |
| 7 | More people and models per group | Reduces sameness | Scales with budget |
| 8 | Period corpora for 1924+ | Fills C15 | A day per year |
| 9 | One prospective forecast | The only fully uncontaminated test | Waits for an event |

---

## 10. Bottom line

The harness is solid where it touches the documented record:
- exact reproduction;
- sourced populations, rules and returns;
- women's turnout within a few points on checks it never saw.

Its interview layer is useful but not shown to be clean:
- **What it is:** a knowledgeable model reasoning about documented circumstances.
- **What it is not:** an uncontaminated electorate.
- **Its contamination:** measured, partly cancelled and disclosed.
- **Its historical evidence:** often thin and narrative-shaped.

What it can claim today:
- the arithmetic of who could vote;
- the direction, but not yet the size, of how people reacted.

What would let it claim more:
- planted-truth and cue-shift tests;
- held-out counties;
- backtests that don't involve the language model;
- calibrated confidence;
- prospective forecasts.
