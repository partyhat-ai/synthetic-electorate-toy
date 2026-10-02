# Disclosures: inaccuracies and intellectual-honesty flags

This is a running log. Every known inaccuracy, weak spot and judgment call
behind Simulacra Americana's numbers and words goes here: our own mistakes,
the data's, and the model's. Each entry has a next step. When it's done, mark
it fixed; don't delete it.

**How to add an entry:**
- Add it at the end with the next ID in its series, a severity, a status and
  a location. Series: A process, B assumptions, C data, D the AI agents,
  E counterfactual fictions, F product and copy, G reproducibility,
  H historical evidence.
- Say what is wrong, why it matters, and what would fix it.
- Log it when it's found, not when it's convenient. An entry that makes us
  look bad is the point of this file.

**Severity:**
- **High:** it can change a headline number or mislead a reader.
- **Medium:** it biases a detail, or weakens a claim we make.
- **Low:** cosmetic, or already contained.

**Status:** open, mitigated, fixed or by design (a deliberate choice that must
stay disclosed).

---

## Entries

**A1 · Medium · by design · `evaluate.py`, `benchmarks.py`**
The 1920 checks aren't blind. Their author knew the standard 1920
literature: a Harding landslide, women voting below men, Black Southerners
excluded. The thresholds were set with that knowledge.

**B1 · High · open · `backbone.py` T1–T2**
Men's turnout is assumed to have changed from 1916 to 1920 by the same amount
everywhere as it did in the 12 Western states where women already voted.
Women's votes are whatever is left. This is the key identifying assumption,
and N1 shows it pushes women's turnout 4–6 points high in CT and MA.

**Next:** a regional κ from county returns.

**B2 · Medium · open · T3**
In the 12 old-suffrage states, women's turnout relative to men's is borrowed
from the newer-suffrage states. There is no within-state evidence for it.

**B3 · Medium · open · T4**
Within a state and sex, native-born, naturalized and Northern Black voters
are assumed to turn out at the same rate.

**B4 · Medium · open · C1 (δ)**
Women's partisan tilt (δ = −0.67, toward Cox) comes from a regression that is
identified mostly by the West-versus-East contrast. Region may confound it.
The `no-19th` result (helps Harding) depends on its sign.

**Next:** region intercepts, a sensitivity table, and the literature.

**B5 · Medium · by design · C3b**
The 80% accounting bound on Black Southern votes is a chosen number. Other
choices would change South Carolina and Mississippi.

**B6 · Medium · open · population noise**
The undercount CVs (2–8%) are assumptions, not estimates. The Black 1920
undercount is documented in demographic literature we didn't retrieve.

**C1 · High · open · Black voters' choice (β_B)**
State returns can't identify it. The regression says Black voters leaned
toward Cox (−3.4 ± 1.9 logit), which contradicts the documented history. The
published estimate leans on a subjective prior. The research agents found no
documented 1920 estimate; the only source was Du Bois (1928), with no
counts.

**C2 · Medium · by design · labels**
The Algara–Amlani county sums don't match official totals in 14 states for
1920:
- Maryland's Baltimore row double-counts, inflating the state 40–53%.
- In Vermont, the Republican vote sits in "other".
- New Mexico is missing a county.
- Maine's Cox vote is 17.6% high.

The House Clerk's 1921 table was used instead. **1916 has only one
cross-check source (Wikipedia)**, and 1916 anchors the whole natural
experiment.

**C3 · Medium · open · franchise conflict**
Gray–Jenkins codes women as able to vote in Georgia and Mississippi in 1920.
National Park Service pages say they couldn't. We follow NPS. A Smithsonian
snippet also names Arkansas and South Carolina; it's unverified and not
coded.

**C4 · Medium · open · Teele suffrage dates**
- Ohio is coded as presidential suffrage from 1917. We believe, **without
  verification**, that Ohio's 1917 law was overturned by referendum, which
  would make 1919 the real date. It doesn't affect 1920 eligibility.
- Arizona is coded 1910, before statehood in 1912.
- Arkansas and Texas's 1917 primary-only suffrage is excluded.

**C5 · Medium · by design · census transcription**
The 1920 voting-age tables were read by eye from scans, because OCR confused
3/8, 9/0 and 5/6. Thirteen ambiguous digits were resolved against the
tables' own sums. Every state matches its printed totals, but a
compensating pair of errors would pass that check.

**C6 · Medium · open · 1910 women**
Citizenship wasn't asked of women in 1910. The split is borrowed from men of
the same state (wives took their husbands' status before 1922).

**C7 · Low · open · census gaps**
- Delaware, New Hampshire and Vermont print no "all other races" row; those
  cells are 0.
- There is no age-band table.
- DC is excluded, since it had no electors in 1920.

**C8 · Medium · by design · Corder–Wolbrecht**
The state and pooled women's-turnout figures we compare against are **our
own aggregation** of their unit-level estimates, not numbers they published.
Their deposit covers only CT, IL, MA, MI and NY.

**A2 · High · open · `backbone.py`, `paired.py`, `evaluate.py`**
Nine modelling and analysis changes were made after seeing the output they
changed (EVAL.md, deviations 1–9). None moved a threshold, and each is
logged, but together they are a large garden of forking paths. Three of them
changed a result's direction or its pass/fail status:
- the B2 bug fix, fail → pass;
- β_B's region intercepts, which flipped its sign from −1.5 to +0.5;
- the Black Southern choice rule.

**Next:** freeze the model code by hash in the run manifest, and require a
pre-registered amendment before any backbone change.

**A3 · Medium · open · `EVAL.md` N1**
N1's denominator was realigned after the first result: citizens → all adults
21+, to match Corder–Wolbrecht. The realignment is correct, since the
benchmark's own counts prove its definition. But it was found because the
first result looked bad. It still fails, and both versions are reported.

**A4 · High · open · β_B, `EVAL.md`**
We chose the region-intercept specification partly because its answer looked
more plausible. It lands between the regression, which is implausible, and
the prior, which is documented history. It is the least-bad choice, not a
neutral one.

**Next:** publish both versions, or get a real estimate (see C1).

**B7 · Low · open · `agents.py`**
Personas carry imputed details:
- the household economy (farm, wage, trade or proprietor);
- a uniform age from 21 to 75, because no age table was built.

Neither drives any count, but both shape the quotes.

**Next:** OCC1950, FARM and AGE from the IPUMS full count.

**B8 · Medium · open · franchise**
Non-citizens who had declared their intent are treated as barred
everywhere. No dataset we found codes which states still let them vote in
1920. HANDOFF-SIMULATION says several did until 1926.

**Next:** Keyssar, Table A.12.

**B9 · Low · open · naturalized choice**
Naturalized voters share their state's partisan split. The model has no
separate estimate.

**C9 · Low · open · platforms**
- The American Presidency Project dates are convention start dates, not
  adoption dates.
- The Socialist text is a pre-adoption newspaper draft.
- The Farmer-Labor planks are an AP summary.

**C10 · Low · open · treaty facts**
Sources disagree on:
- the date of one November 1919 vote;
- whether the March 1920 vote carried the reservations. FRUS says yes, and
  one senate.gov page says no.

**C11 · Medium · by design · corpus**
- 87 of 89 excerpts have bracketed OCR fixes, so they aren't verbatim.
- 29 items were excluded for naming a candidate or party.
- Coverage is thin: 1 usable Kansas item for women already voting in the
  West; no Midwestern or Western items on Black registration.
- Some items quote officials stating white-supremacist aims. They are kept
  as documents of the barriers, and are period voices, not neutral fact.

**C12 · Low · open · leakage labelling**
1920 uses the 1920 census, published 1921–23, after the election. Results
are labelled `mode: truth`. Strict mode (1910 aged) isn't run.

**D1 · High · open · backend**
The prototype's answers came from 9 Claude Code subagents, not independent
API calls:
- 18–59 prompts shared one context;
- the Claude Code system prompt surrounded them;
- the model version behind "sonnet" and "opus" isn't recorded;
- one subagent **scripted 28 of 56 probe answers**;
- one built answers with a helper script;
- one says its later answers got generic.

**No agent-layer number should be cited until it is rerun on the API.**

**D2 · High · by design · memorization**
56 of 56 probes identified 1920, both candidates and Harding's win.
Blinding doesn't work for 1920. The control answers are exposed, and only
their paired changes are used.

**D3 · High · open · homogenization**
In 90% of cohorts with a mixed real split, every agent gave the same answer.
The agents compress variation, so they can't stand in for how a group split.

**D4 · Medium · open · turnout overstatement**
Agents say they'd vote about 12 points more often than the calibrated
backbone. For women in the benchmark states it is 15.5 points.

**D5 · Medium · open · self-de-blinding**
25% of answers name a party that the blinded briefs never named. Quotes are
published with names restored, so a reader can't tell which words the model
supplied from memory.

**Next:** flag quotes that contain inferred party names.

**D6 · Medium · open · sample size**
With 4–5 agents per cohort, the pre-registered shrinkage (pseudo-count 8)
pulls every cohort's effect 57–67% toward its region. Cohort differences
are mostly unmeasured.

**D7 · Low · fixed in p2 · prompt bugs**
Three bugs in the p1 prompts:
- **Non-citizen women's briefs contradicted themselves.** They were told
  "state law lets women vote". Subagents caught it; those pairs are
  excluded.
- **Dates didn't line up.** Briefs were dated 30 October but included items
  up to 1 November.
- **Surnames didn't fit their groups.** One agent is "Mary Lindqvist", a
  Black North Carolina woman.

The p1 answers stand as recorded.

**D8 · Medium · open · Opus disagreement**
On the League what-if, Sonnet's shift toward Cox is −0.18 logit and Opus's
is −0.03 on the same people. They agree on sign, not size. The published
effect pools them.

**E1 · by design · `whatifs.py` `fifteenth`**
The brief says the Supreme Court struck down Southern poll taxes and
registration tests in 1919, and federal registrars were sent. This mechanism
is invented to make the world internally consistent. It happened in no form
in 1919.

**E2 · by design · `league`**
"The United States took its seat in the League of Nations this spring" is
invented. The real Senate vote on 19 March 1920 failed, 49–35. We also
assume both parties would drop the League from their platforms.

**E3 · by design · `no-19th`**
"Tennessee voted it down" is invented. Tennessee ratified on 18 August 1920.
Women in 27 states keep the presidential vote under their own state laws.

**E4 · by design · the people**
Every person, name and quote is invented. Only their circumstances (census
cells, dated newspaper items) are documented. Quotes are voiced by a model
that knows the outcome (D2).

**G1 · Medium · open · `config.py`**
A run's id hashes its config and data, **not the code**. The
`1920-bcbd86b43f` bundle was produced by code changed after its requests
were planned and answered (p1 → p2, deviations 1–9). The same run id can't
be regenerated from today's code with identical results.

**Next:** hash `simharness/*.py` into the run id.

**G2 · Low · open · timing**
The backbone was refitted after the agent answers existed. The cohort bias
(A1) and shrinkage use the final backbone, not the one in place when the
requests were planned.

**G3 · Low · open · environment**
The installed Anthropic SDK is 0.46, which predates `output_config`. The API
backends need `anthropic>=1.0`. They are written but untested against the
live API.

**D9 · Medium · open · quick run: recall probe**
The quick run (Haiku, 2 agents): the recall probe named 1920, both
candidates and the winner at 95% confidence from the blinded brief. One
probe, but it matches L1's standing exposure.

**D10 · Low · open · quick run: state-law suffrage in `no-19th`**
In the `no-19th` counterfactual the Indiana woman still answered
able_to_vote=yes, reasoning from Indiana's 1919 presidential-suffrage law.
The Black North Carolina woman answered no in control, `no-19th` and
`league`, and yes only under `fifteenth`. Plausible, but the `no-19th` brief
should say explicitly whether state-law suffrage survives.

**D11 · Medium · fixed in p3 · a quote named a ballot label**
Rung 1 (run `1920-4502a6f977`): a quote named the blinded ballot label ("K
says the money got too loose…", south:M:native_white-0). The page would
show a meaningless letter to readers. p3 tells agents to name candidates by
description, never by label, in `quote`, and any label left is mapped back
to a name before a quote is used.

**D12 · Medium · open · wording moved results more than the what-if**
Rung 1: the League effect's sign flips by paraphrase (dr −0.61, +0.49, +0.03
for paraphrases 0/1/2, n = 12 agents). Two single-agent flips go in
opposite directions (a Midwest woman R→D; a Northeast man D→R). The national
dr interval [−0.19, +0.15] spans zero. At n = 12 the paraphrase spread (A3)
is larger than any effect.

**D13 · Low · open · quote length**
Prompt p3 (run `1920-423843d9ec`): no quote used a letter label (0 of 24,
fixes D11). Haiku ignored the 25-word cap (mean 30.5, max 40 words). A hard
limit needs a trim at publish or a schema maxLength, not prompt wording.

**A5 · Medium · open · `result.drawsWon`**
"Cox wins in 0 of 400 draws" sounds more certain than it is. The draws cover
parameter and population noise only. They don't cover model-structure
choices:
- the κ assumption
- the β_B prior
- the 80% accounting bound
- the smoothing

N1's failed coverage is direct evidence that the intervals are too narrow.

**Next:** add structural variants to the draws, or say "0 of 400 draws of
this model".

**A6 · Medium · open · A4 stereotype audit**
The "pass" (0 of 66 flagged) comes from a regex. No person read the 66
reasons. Don't cite it as an audit until someone has.

**A7 · Low · fixed · `NOTE-FOR-UI-FROM-HARNESS.md`**
The first draft of the UI note showed invented example numbers ("fails 2 of
17 checks", "318–352") that looked like results. They were replaced with the
real figures.

**A8 · Low · fixed · session summary**
The first research prompt pointed to a data folder that doesn't exist
(`resetion_sim_data`). The data used is in
`research_notes/historical_election_sim_data`.

**F1 · Medium · open · `sample.js` (the UI's file)**
The `no-19th` detail, "fifteen states that already let them", counts only
full-suffrage states. Twenty-seven states had given women the presidential
vote. Flagged in the UI note; not edited.

**F2 · Medium · open · `sample.js` women slice**
It treats Georgia and Mississippi women as voting in 1920.

**F3 · Medium · open · `stories.js` / `HANDOFF-SIMULATION.md`**
HANDOFF-SIMULATION lists story facts that are still unverified: 1800, 1860,
1876, 1896, 1912, 1948 ("bubbles in a bar of soap"), 1960, 1968, 2000 and
2016. This harness didn't check them.

**F4 · Low · open · `history.js`**
Its known approximations are listed in HANDOFF-SIMULATION: split
delegations, 1836, 1872, 1864, faithless electors. The totals aren't yet
checked against NARA for every year. For 1920, 404–127 matches NARA.

**F5 · Medium · open · page slices**
The five 1920 groups are a partition, but they carry small misfits:
- "White Southerners" includes the few American Indian and Asian adults in
  the South.
- "Men outside the South" includes Black Northern men.
- Poor white Southerners kept out by poll taxes show as "stayed home", not
  "couldn't vote".

**F6 · Low · open · verdict copy**
- A multi-what-if verdict concatenates single-what-if sentences, so a
  combination can say "3.1 million women" measured in a different world
  from the combined one.
- The League verdict's "2.7 points" is measured in the point draw only.

**E5 · by design · compiled what-ifs (`harness/whatifs/*.json`)**
A typed what-if's facts, ballot line and assumption are written by a model
(`scenario.py`, compiler c1/c2). They are checked for nominee and party
names, and are exploratory, never pre-registered. Post-hoc edits:
- **`charlie-chaplin-runs`**: the positions carried "(documented)" and
  "(inferred…)" notes, which voters saw in the brief. The notes were
  stripped, "Would likely speak for" became "Speaks for", and the
  interviews were re-asked.
- **`influenza-returns-in-october-1920`**: see D17.

**E6 · by design · `charlie-chaplin-runs`**
Chaplin was born in England and was not a citizen, so the Constitution
barred him. The ballot line is modelled anyway, flagged
`ineligible-candidate`. His positions are inferred, since nothing on record
predates 1920, and flagged `positions-inferred`.

**G4 · Low · by design · answer cache (`llm.AnswerCache`)**
Identical requests reuse earlier live answers across runs. A request is
identical when it has the same model, system, user text and schema; meta,
run id and prompt-version labels are ignored. So p4 requests whose text
equals p3's reuse p3 answers. Transcript and mock answers are never cached.
Each answer records `cached_from`.

**G5 · Medium · open · evidence reproducibility**
Web search results change over time. The saved
`whatifs/evidence/<key>.json` is the record: queries, every source, the
cited text and the notes. It is hashed into the run id. Re-researching
(`--refresh`) makes a new instrument.

**H1 · by design · evidence never enters a brief**
Research results are used only after the interviews:
- **Agreement:** do the interviews move votes or turnout the way the record
  does?
- **Blend:** a prior on cohort effects, for compiled, exploratory what-ifs
  only.
- **Confidence tier.**

Pre-registered what-ifs are never blended; their numbers follow
METHOD.md.

**H2 · Medium · open · source grading**
Tiers come from a domain list (`evidence.TIER_A`, `TIER_B`; everything else,
including Wikipedia, is C). A .edu course page counts as A. A finding's
grade is its tier × the extractor's match judgement (same-event …
distant). Neither is validated.

**H3 · Medium · open · blend weights**
Evidence sd grows as 1/√grade. The interview sd is floored at 0.2 logit,
because a bootstrap over two or three people understates model error. Weak
evidence barely moves numbers: Chaplin's evidence weight is under 1%.

**H4 · Medium · open · confidence tiers**
`evidence.confidence` is a rule set:
- a kind's base tier;
- plausibility and anachronism;
- evidence strength;
- agreement;
- interview stability, for agent-mode what-ifs only;
- the number of interviews.

"Extremely low" (very-low) reaches the page as `confidence: low`, plus
`confidenceTier` and a sentence in the summary. The rules were written
after seeing the first three results, and nothing calibrates them.

**D14 · Medium · open · paraphrase assignment**
An agent's question wording is `n % paraphrases`, where n is its place in the
run's sorted agent list. Adding a cohort renumbers everyone after it, so each
of them gets a different question. The live config
(`configs/live-1920.json`) keeps rung 1's six cohorts so answers stay
comparable and cached. Fix before widening: key the paraphrase on the
agent id.

**D15 · Medium · fixed · evidence extraction**
- **Haiku extracted nothing.** Given rich research notes (Christensen's
  19% in Washington, Roosevelt 1912, La Follette 1924), it returned zero
  findings. It judged every analogue unreliable itself.
- **Sonnet ran out of room.** At 4,000 tokens its JSON was truncated, and
  the crash lost the call's usage. About $0.052 is entered in the ledger as
  an estimate.

Now: Sonnet with 8,000 tokens, at most 12 findings, and an instruction not
to judge reliability, since the pipeline grades it. A truncated answer keeps
its usage.

**D16 · Medium · fixed · research without searching**
The first League research call ran no searches and answered from memory
($0.02). Grounding correctly dropped every claim, since none had a source.
The prompt now requires at least two searches, and a turn with none is
retried once.

**G6 · Low · open · spend ledger**
`sessions/spend.jsonl` started mid-day. The earlier sessions' $0.26 is
backfilled from runs' usage.

**D17 · Medium · fixed (c2), hand-edited · compiler dropped topics**
The flu what-if's compile dropped T2 (League) and T3 (prices) as "crowded
out". Its counterfactual brief then differed from the control by more than
the change. The spec was edited by hand to drop nothing, and its 12
interviews were re-asked. Compiler c2 drops only topics that the settled
facts make false.

**D18 · Medium · open · a quote named a nominee**
A flu counterfactual quote said "That fellow Cox" (south:M:native_white-1)
from a blinded brief. This is more evidence of D2 and L1: the model knows
1920. Quotes aren't scanned for real names before publishing.

**D19 · Low · open · choice and quote disagree**
Haiku sometimes picks one candidate and quotes for the other:
- Chaplin run, midwest man: choice Harding, quote "I'm going with the
  Democrat".
- Flu run, Arthur Hayes: choice Cox, quote praising "the Republican".

The counts use the choice and p_choice; the page shows the quote.

**D20 · Medium · fixed · evidence sign**
The extractor recorded the historical direction as the scenario's effect.
"The League hurt Cox" became toward-R for a scenario that removes the
League. Findings now carry a `relation` field (like-scenario,
reverses-scenario or context), and the code flips reversed findings. Context
findings (who won, overall turnout) inform the reader but not the numbers.

**D21 · High · fixed (p5, compiler c3) · voters misread whom the news was about**
In the first Harding-disclosure run, the brief identified the nominee only
by descriptor ("the candidate of the party that has held a majority in
Congress…"). Most of the 12 interviewed people blamed the other candidate.
The result was a spurious 7.8-point move *toward* Harding.

Now:
- **News on the line.** News about one nominee is printed on that
  nominee's own ballot line (`about`, `nominee_news`).
- **Manipulation check.** Each such counterfactual answers `news_about`.
  Misreaders are left out of the counts, kept in the interviews with
  `misread: true`, and flagged in confidence (`misread-change`). At least
  half misreading forces "extremely low".

The rerun: 0 of 12 misread. The spec was recompiled with c3 and its key,
label and words kept, a post-hoc edit.

**D22 · Medium · fixed · evidence read by party, not role**
Findings from other elections were signed by that year's party. Cleveland
in 1884, a scandal-hit *Democrat*, therefore counted as "toward D" for a
scenario about a scandal-hit *Republican*. Findings now carry
`role_direction` (toward or away from the candidate in the same role, plus
an `affected` measure), and the code maps them onto the scenario's
nominee.

**D23 · Medium · open · Harding-disclosure rerun: one uniform swing, quotes elsewhere**
- **The swing is uniform.** Midwestern men go from 0.70 to 0.32 (Harding's
  two-party share), Southern men from 0.68 to 0.31, and every region falls
  to about 0.31–0.33. That looks like one model reaction stamped on everyone
  (A2 homogenization), not differences between groups.
- **The quotes mostly talk about prices.** Several switchers' quotes never
  mention the news, even though their choice changed.
- **Some quotes back the candidate the person didn't choose.** Albert
  Jackson and Lillian Jones each chose Cox but quoted "the Republican" with
  approval. This is D19 again: "the Republican" in a blinded quote is the
  model guessing which label is which.

**C13 · Medium · by design · 1924 population**
There is no 1924 census. Each cell's 1920 count is aged to 4 November 1924
along its own 1910→1920 trend (`data.population(1924)`). Things this misses:
- the Cable Act (1922, married women's citizenship);
- naturalizations after 1920;
- the Indian Citizenship Act (June 1924).

**C14 · Medium · by design · 1924 backbone (`backbone.carry_forward`)**
1924 has no natural experiment of its own, so it carries 1920's structure
forward:
- the 1920 fit's per-cell turnout, women's tilt δ, Black voters' β_B and
  Black Southern exclusion;
- one turnout shift per state, across all groups;
- the same exact share calibration as 1920.

Checks:
- **Reproduction:** every 1924 state within 0.41 votes, 382–136–13 in
  every draw.
- **Held-out benchmark:** Corder–Wolbrecht 1924 women's turnout on their
  denominator gives MAE 3.6 points, against 3.2 for 1920. CT and MA women
  run high and men low, as in 1920.

Within a state, La Follette's share is spread evenly across groups. Who
his voters were inside a state isn't identified.

**C15 · Medium · open · 1924 briefs have no dated newspaper items**
There is no 1924 corpus yet, so 1924 people know only their circumstances
and the ballot. Pulling Chronicling America items for October 1924 is the
next step.

**C16 · Low · open · 1924 platforms (`context/platforms_1924.json`)**
- Quotes come from American Presidency Project pages and the paraphrases
  were written by the harness session.
- The Progressive platform's date is entered as 4 July 1924 (the
  Cleveland conference). APP files it under 4 November [I].
- The fetched Republican text had no Prohibition passage.

**D24 · Medium · open · 1924 withdrawal transfer**
"No La Follette" moves his voters by one national transfer, estimated from
12 people: 80% to Davis, 8% to Coolidge, 11% stay home. The same transfer
is applied in every state.

The record is mixed:
- In 1920 the upper-Midwest farm and labor vote was heavily Republican.
- In 1928 his former voters split between the parties.

So the Davis share is probably too high, and region matters. The evidence
check says "untested" because no source gives a number. Fix: regional
transfers, plus a prior from the 1928 split.
