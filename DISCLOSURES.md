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

Neither drives any count, but both shape the quotes. Since the all-years
build, economy wording and weights are set per era [I] and ages run 18–80
from 1972. First names come from 1920-era lists in every year: they carry no
information, but they read as period names.

**Next:** OCC1950, FARM and AGE from the IPUMS full count.

**B8 · Medium · open · franchise**
Non-citizens who had declared their intent are treated as barred
everywhere. No dataset we found codes which states still let them vote in
1920. HANDOFF-SIMULATION says several did until 1926. The all-years
franchise file now codes IN, MO, TX and AR as still letting declarant
aliens vote in 1920, from unchecked memory of Keyssar A.12 (C25). The legacy
1916–1924 files are left blank to keep those years byte-identical (G9), so
they still run with no alien voting.

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

**G1 · Medium · fixed · `config.py`**
A run's id used to hash its config and data, **not the code**. The
`1920-bcbd86b43f` bundle was produced by code changed after its requests
were planned and answered (p1 → p2, deviations 1–9), so that run id can't be
regenerated from today's code with identical results.

**Fixed:** `run_id` now also hashes `simharness/*.py`, so a code change gives a
new run id. Runs recorded before the change keep their old ids.

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
backfilled from runs' usage, and D15's $0.052 is estimated.

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
next step. The all-years corpus build stopped before 1924 was done (C30).

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

**A9 · High · fixed (requests already sent) · data-fetch scripts**
During the all-years build, three agents (G, C and E) put the user's email
address in the HTTP User-Agent of requests to Wikipedia and loc.gov, as a
"contact" string. E also sent it in two manual curl probes. The user's
address must never go to an unrelated service. It was removed from every
script, which now send a generic User-Agent, and E's running 1932 corpus
build was restarted from its HTTP cache. The requests already sent can't be
recalled.

**Next:** no contact address in any fetcher; check the User-Agent whenever a
fetch script is reviewed.

**A10 · Medium · fixed · `pipeline.py` verify, `benchmarks.py`**
`Run.verify` read the Corder–Wolbrecht held-out benchmark file directly,
outside the evaluate stage, so `test_benchmarks_isolated` failed. Found while
porting to the clean repo. The read now goes through
`benchmarks.corder_wolbrecht_any_year()`, and `check.json` is byte-identical.
The isolation test allows benchmark imports in exactly two places in
`pipeline.py`: verify and evaluate.

**Next:** decide whether verify should see the benchmark at all, or move that
check into evaluate.

**B10 · High · by design · `backbone.general_fit`**
Every year outside 1916–1924 is fitted by `general_fit`, which has no
natural experiment. Nothing is identified within the year. Each group's
turnout gap and partisan tilt is a literature prior, a (year, mean, sd) knot
table interpolated between knots, and exact calibration to the state returns
does the rest. The priors are not updated from the data. A fit's values are
in `fit.diagnostics['priors']`, and all are [I]:
- **Women's turnout:** Corder–Wolbrecht to 1936, ANES 1952, CPS P20 and CAWP
  from 1964. Before 1920, the 1920 gap with a wider sd.
- **Naturalized turnout:** Merriam–Gosnell and CPS. Declarant aliens and
  `other` have no source.
- **Black Southern exclusion:** Foner and Kousser for 1868–1900, the 1920
  posterior for 1904–44, registration ratios for 1948–76.
- **Black turnout:** CPS national gaps, which partly double-count the
  Southern exclusion in 1964–76.
- **β_B:** Fox, Foner, Weiss, Gallup, ANES and exit polls. Before 1856 it
  assumes slot R is the anti-Democratic party.
- **Naturalized tilt:** Kleppner, Lubell and Pew. `other` has none.

A what-if's shift lands on groups in proportion to these priors, so they
shape every what-if outside 1916–1924.

**Next:** in-year updating where county returns exist (`bayes_ols`), and a
sensitivity table per prior.

**B11 · Medium · open · women's tilt δ, 1936–1940**
As briefed, `general_fit` uses the 1920 posterior δ (−0.66 ± 0.27, toward
D) for every year to 1940. Gallup's 1936 and 1940 vote-by-sex tables show
women slightly *more* Republican than men. The prior contradicts the only
direct evidence for those two years. From 1944 it follows Gallup, then exit
polls.

**Next:** use Gallup for 1936–40, or publish both.

**B12 · Medium · open · `general_fit` repairs (`fit_flags`)**
When the data and the rules disagree, the fit repairs the inputs instead of
failing:
- If a state's votes exceed 97% of its eligible adults, its adults are
  scaled up for that draw (`adults_scaled_share`; e.g. 1876 SC).
- If returns exist where the coded rules bar every adult, the rules lose and
  the state's men are opened (`legal_rules_contradicted`).
- A state with votes but no population cells gets synthetic native-white
  cells at votes ÷ 0.6 (`cells.synthetic`).

Each one signals an undercount or a coding error, and each makes
reproduction exact by construction. They are reported per fit, not on the
page.

**Next:** list each year's repaired states here and in the page's sources.

**B13 · Medium · by design · 60-election reproduction (`aggregate.outcome`)**
The unchanged rerun of every one of the 60 elections, 1789–2024, now
reproduces every state's certified R/D/O exactly and matches history's
electoral votes. Four kinds of fix were needed:
- **Legislature-chosen states** keep their history's electors (`ev_fixed`).
- **Split or slate states** keep their historical division while the
  recorded plurality winner holds (`ev_split`).
- **A lumped "other"** can carry a state only if its largest single
  candidate would. This fixes 1860 (Bell and Breckinridge together beat
  Douglas in MO), 1892 and 1912.
- **Before 1868**, electoral votes count the electors who actually voted,
  not those appointed.

These are rules, not estimates. A what-if can't move a legislature's
electors, a split state's division changes only when its plurality winner
does, and O's candidates remain one slot, so a what-if can't say which of
them gains.

**C17 · Medium · by design · NHGIS populations (`scripts/harness/build_population.py`)**
State tables for 1870–1970 come from NHGIS extract 1 (cache:
`population/nhgis/`; not redistributable).

- **The 1920 conversion reproduces the hand-keyed 1920 table exactly:**
  60,886,520 adults, 0 of 588 cells off.
- **1930's race/nativity-by-sex table (NT10) is mislabelled.** Its codebook
  labels interleave the sexes, but the values run all male groups first.
  Taking the labels at face value gave New York 15,184 foreign-born men.
  The mapping now follows the values, and the build asserts it against two
  independent 1930 tables (race by sex; white nativity by sex).
- **1930's "Other race" includes Mexican Americans.** The 1930 census
  counted "Mexican" as a race, so 1930's `other` group is 1.01 million
  adults, against 0.25 million in 1920. Most were citizens.
  `Inputs.other_citizen` must not treat them as 1920's American Indian and
  Asian adults.

**C18 · Medium · open · 1870–1910 women (`scripts/harness/build_population_early.py`)**
The 1870–1900 tables have no women 21+ by group. Women are each group's men
× its whole-population F/M ratio [I]. 1870 has no table by sex at all, so it
borrows 1880's ratios. Checked against the hand-keyed 1910 table, the method
runs **2.0% high** (25.05M against 24.56M):
- native white −0.6%, Negro +2.1%, foreign white +10.4%, other +21%;
- per-state errors are wide (foreign white: mean |error| 12%).

Whole-population ratios overstate foreign-born adult women.

**Next:** a per-group 1910 factor (hand ÷ estimate), applied to 1870–1900.

**C19 · Medium · by design · other 1870–1910 estimates**
- **1900's NT7 is mislabelled.** "Other colored" holds all colored people,
  Negro included. Other races = AZ3001 − AZ3003, asserted in the build.
- **1890 has no citizenship table** in extract 1, so 1880 and 1890
  citizenship are interpolated 1870 → 1900 [I].
- **1870 men 21+** come only as separate race and nativity margins, raked
  with IPF [I]. 1870 naturalized = citizens − native-born, clipped to
  [0, foreign-born white]. That gives 61% nationally, but AR and NC clip to
  0, and VT (14%), ME (16%), IN (84%) and AL (81%) are implausible.
- **1880 and 1890 "colored" includes Chinese and Indians.** It is split with
  fixed weights (0.420; 0.95 for Chinese and Japanese, a guess), and for 1890
  with the mean of 1880's and 1900's Negro shares [I].
- **Territories** are kept as their later states. Consumers must filter to
  the states that voted.

**C20 · Medium · by design · 1940 race break**
The 1940 census counted Mexican Americans as white; 1930 counted them as a
race (C17). `other_races` 21+ falls from 1.01M to 0.33M, and `native_white`
rises by the same people. That is a change of classification, not of
population. 1932 and 1936 interpolate across it, and their profiles say the
1930 "Mexican" count is folded into white; the population build must match.

**C21 · Medium · open · 1960 and 1970 nativity (`build_population_mid.py`)**
The extract has no 1960 or 1970 nativity table, so both carry 1950's
foreign-born share of whites forward [I]. Foreign-born white adults then rise
from 9.9M (1950) to 10.8M (1960) and 11.9M (1970), while the real
foreign-born population (all ages) fell from 10.3M to 9.6M. 1970's
foreign-born whites are probably about 3M too high, and native whites 3M too
low. White totals are unaffected.

**Next:** NHGIS 1960 and 1970 nativity and citizenship tables (requests
drafted in `notes/A2.md`, not submitted).

**C22 · Low · open · other 1940–1970 estimates**
- 1950 and 1960 have only white/nonwhite. The Negro share of nonwhite adults
  is interpolated 1940 → 1970 by state and sex [I].
- 1950 foreign-born whites by sex use 1940's ratios, and citizenship is
  raked to 1950's all-foreign-born split. 1950 has no "first papers"
  category.
- The 18–20 add-on for 1950–60 uses the 21+ nativity shares, which
  overstates the foreign-born among 18–20s.
- Hawaii is blank in every 1950 table and omitted (it first voted in 1960).
  Its 1960–70 nativity uses national 1950 shares.
- There is no 1940 age-band table, so Georgia's 18–20s in 1944 and 1948 are
  21+ × the 1950 18+/21+ ratio [I].

**C23 · Medium · by design · returns 1868–2024 (`scripts/harness/build_returns.py`)**
Algara–Amlani county sums are used only where both party shares are within
0.5 points of the state file. 153 state-years fail and fall back to
Wikipedia. The failures extend C2 to every year:
- Missouri's county total is about 1.2× too high in nearly every year.
  Alaska has no county data.
- Fusion tickets (1884 and 1892 Weaver/Butler, 1896 Bryan), and unpledged or
  Dixiecrat lines counted as Democratic (1948 AL, 1952 SC, 1964 AL).
- Garbage rows: 1872 MI and IL, 1896 MI, 1900 WA, 1912 ID.
- Algara–Amlani's state file has the wrong electoral votes for 1968 NC and
  2020 NE (539 in total).

In 10 state-years Wikipedia also differs from the state file by more than
1.5 points (fusion allocation); Wikipedia is kept and flagged in `source`.
1872 GA's 3 rejected Greeley votes stay in `ev_dem` (352 nationally, not the
349 counted). 1868 MO's total is set to R + D.

**C24 · Medium · by design · pre-1868 adults (`build_population_republic.py`, `data.population`)**
No census before 1870 tabulates age 21, so every adult count for 1789–1864
is an estimate [I]:
- **Age bands** are split on a stationary 3%-growth profile. 46% of 16–25s,
  69% of 19–25s, 89% of 20–29s, 37% of 14–25s and 18% of 10–23s count as
  21+.
- **1790** counts only white males 16+, converted with the state's 1800
  ratio.
- **1790–1810 free colored and enslaved people** have totals only, split by
  1820's adult shares.
- **Nativity.** None before 1850. In 1850–60, foreign-born white adults are
  72% (men) and 70% (women) of all foreign-born whites, and citizenship
  isn't split.
- **Dates.** Before 1848 election day is taken as 1 November, and 1790–1820
  census days as 2 August. A cell found in only one bracketing census takes
  that count, which double-counts some native whites in 1844 and 1848.

**C25 · High · open · franchise rules from memory (`build_republic.py`, `build_franchise.py`)**
Gray–Jenkins starts in 1870 and has no alien-voting field. The rules it
doesn't cover were coded from the agents' memory of Keyssar (Tables A.1–A.4,
A.12) and Hayduk, **not checked against the books** [I]:
- **Alien voting, 1789–1968:** e.g. NJ 1789–1804, IL 1820–48, MI from 1836,
  IN from 1852, MN and OR from 1860; IN, MO, TX and AR still in 1920 (B8).
- **Property and taxpaying tests, 1789–1864,** as the share who could vote:
  0.95 under manhood suffrage, 0.88 under a taxpaying test, 0.55–0.75 under a
  freehold (VA 0.55 before 1830; RI down to 0.40). Georgia 1840 then turns
  out 102% of its eligible men, so 0.88 is too strict there.
- **Free Black men:** the free share × 0.95, 0.6, 0.25 or 0.08 (NY's $250
  rule), by regime.
- **New Jersey women, 1792–1804:** about 10% of adult women.
- **1868:** each state's 1870 Gray–Jenkins row. Ex-Confederate test oaths
  as MO 0.80, TN 0.70, WV 0.85, AR 0.85. NY's Black men 0.1.
- **American Indians** (`other_citizen`): 0.2 before 1888, 0.6 for
  1888–1920, then 1 (AZ and NM 0.2 to 1944).

Before 1868, `poll_tax=1` marks any taxpaying test, not only a capitation
tax.

**Next:** check every rule against Keyssar's printed tables.

**C26 · Medium · open · felony disenfranchisement (`franchise/state_franchise_1972_2024.csv`)**
State rates exist only for 1980 (map bins) and from 2010 (Sentencing
Project, Uggen). 1972–2008 is interpolated between the 1980 bin midpoints
and the 2010 table, then scaled to the national series [I]. That smooths
over law changes: TX 1997, NM and CT 2001, NE 2005, IA 2005–11, RI 2006, MD
2007, WA 2009. Also:
- The 2022 and 2024 reports use VEP denominators; earlier ones use VAP.
- `white_can` is 1 − the non-Black rate. No white-specific rate exists.
- DC is a hand estimate (incarcerated only), 0 from 2020.
- Before 1972 the share is blank, and 1789–1864 uses a flat 0.0005.
- Where a year has no state table, agents' eligibility lines use national
  rates (`FELONY_SHARE`), with Black adults at 3.5× and women at 0.25× [I].

**C27 · Low · open · 1980–2024 adults 18+ (`build_population_modern.py`, NHGIS extract 3)**
- 1980 and 1990 foreign-born adults by race are all-ages counts × the
  foreign-born adult share. 1980's share comes from 1990, and both years'
  sex split from 2000 [I].
- 1990 totals come from MARS, because STF1's table covered Hispanics only.
  They aren't raked (−0.17% nationally).
- 2020 is ACS 2016–20 raked to the PL count, a −1.96% gap (ID −4.8%).
- Suppressed ACS cells use a fallback in a few small states (MT and WY in
  most years).
- Black non-Hispanic native adults = Black native × the all-ages
  non-Hispanic share [I].
- Years without their own file borrow [I]: 1972 and 1976 from 1980; 1984
  from 1980/1990; 1988 and 1992 from 1990; 1996 from 2000; 2004 from
  2000/2008.

**C28 · Medium · by design · 1789–1824 popular votes (`labels/state_pres_1789_1864.csv`)**
Every number is parsed from Wikipedia's results tables (Tufts' *A New Nation
Votes* to 1824; Dubin, CQ or Leip after). None was re-keyed from the
sources. The early record is fragmentary:
- About 20 rows in 1792–1824 are partial ("do not use for turnout") or not
  extant.
- 1789's slates were for or against the Constitution. 1792's ~7,800 votes
  were on uncontested slates. 1820's ~109,000 were effectively uncontested,
  20,660 of them for unpledged or Federalist-leaning slates.
- How electors were chosen is hand-keyed, and some methods are ambiguous (MA
  1789–96, KY 1792/96, TN 1796/1800).
- There are no county returns before 1868.

A share model of these years measures turnout and dissent, not a contest.

**C29 · Low · open · platforms 1789–2024 (`context/platforms_<year>.json`)**
Quotes are substring-checked against fetched pages, except:
- Founders Online refused bulk fetches. Its 1789–1816 quotes were copied by
  hand from a browser and not compared by script.
- archive.org OCR sources (1808, 1816, 1824, 1831–32, Harrison) were
  normalised for hyphens and spacing.

Weak or odd sources:
- Before 1840 there were no platforms. Those files hold documented
  positions, some from private letters or diaries (1796, 1824). 1812 R rests
  on the Federalist House minority's address.
- APP dates the 1912 Progressive platform 5 November; it was adopted 7
  August [I].
- APP typos are kept verbatim (1968 D, 1972 R).
- 2020 R adopted no platform: the RNC resolution, plus four 2016 planks
  marked as carried.
- 2024 D was drafted while Biden was the presumptive nominee and says "his
  second term".
- Some quotes start mid-sentence, and some paraphrases summarise
  neighbouring passages.

**C30 · Medium · open · newspaper corpora beyond 1920 (`scripts/harness/build_corpus.py`)**
The per-year corpus build was stopped by the user before it finished. Other
years' people know their circumstances and the ballot, and a corpus with
non-1920 topic codes falls back to the items nearest the person. For
whatever was written:
- **The schema is inferred.** The permission classifier refused agent E's
  reads of the 1920 corpus and the corpus code, and E didn't work around
  it. The field names come from `PROVENANCE-sources.md`, and nobody has
  diffed them against a 1920 line.
- **Topics are per year** (`topic`, plus `topic_code` T1–T8 in 1920's slot
  order). Code keyed on 1920's fixed topic list would mislabel them.

**Next:** diff the keys against 1920 (the rerun is offline, from the HTTP
cache), then finish the years.

**C31 · Low · open · first election years (`history.ts`, `geo.ts`)**
`history.ts` gives Missouri electoral votes in 1820 and Michigan in 1836, but
`geo.ts` dates their first elections 1824 and 1840. The mini map leaves their
tiles empty in those years. Pinned by `history.test.ts`.

**Next:** check the sources for each state's first counted electoral votes and
make the two files agree.

**C32 · Low · open · state electoral votes vs. totals (`history.ts`)**
In 8 years (1789, 1792, 1808, 1812, 1816, 1820, 1832, 1864) the state
electoral votes don't sum to the year's total: the table lists electors
allotted, not electors who voted. Pinned by `history.test.ts`.

**Next:** add the number who voted per state, or label the column as allotted.

**C33 · Low · open · faithless and abstaining electors (`history.ts`)**
In 1956, 1972, 1976, 1988, 2000, 2004 and 2016, minor faithless or abstaining
electors aren't listed as candidates, so the candidates' electoral votes fall
short of the total. See also F8 (2000's abstaining DC elector).

**Next:** list them under Other, or note the shortfall wherever totals appear.

**D25 · High · by design · modern descriptors name offices (`profiles/1988–2024`)**
From 1988 the descriptors give the nominee's office where voters plainly
knew it: "the sitting President", "the sitting Vice President", "a former
President seeking a second, non-consecutive term". That blinds the name, not
the identity. With the year in the brief, any current model identifies every
nominee, so **contamination is total for 1988–2020**. 2024 has holdout value
only for a model whose training ends early in 2024.

Earlier years leak the same way through the record itself: "former
commander-in-chief of the Continental Army" (1789), "the general … at New
Orleans" (1824, 1828), "a former President" (1848, 1856), "the sitting
Vice-President" (1860), "a longtime newspaper editor" (1872). This is D2
for every year.

**D26 · Medium · open · 1928 and 1952 descriptors leave out what drove votes**
Descriptors are party-role only, as in 1920/1924:
- 1928's leave out Smith's Catholicism and his wet stance. Both 1928
  platforms pledge Prohibition enforcement, so the brief hides the wet/dry
  split Smith ran on.
- 1952's leave out Eisenhower's war record.

Agents who recognise the year (D25) may supply these from memory. Agents who
don't can't.

**D27 · Medium · open · 1948 Wallace voters**
Thurmond is 1948's labelled third line. Wallace has none: `others_line`
names his party, his voters can only answer "other", and his planks sit
under party "O2", which `party_planks` never selects. In the counts, Wallace
and Thurmond share the O slot.

**D28 · Medium · open · ballot access**
One ballot for the whole country can't show a nominee missing from some
states:
- 1860: the Republican was on no ballot in 10 Southern states.
- 1948: Truman wasn't on Alabama's ballot, and Thurmond held the Democratic
  line in AL, LA, MS and SC.
- 1964: Johnson wasn't on Alabama's ballot. `others_line` says so, but the
  ballot still shows a D line. The `ballot_notes` key exists and isn't set.

Some candidates reach agents only through `others_line` or a shared
descriptor: Bell (1860), Crawford and Clay (1824), the four Whigs (1836).

**D29 · Low · open · planks that aren't platforms**
Some text that agents see as planks is something else:
- **1980 Anderson:** his answers in the 21 September Baltimore debate (APP).
- **1992 Perot:** the 15 October Richmond debate transcript (APP).
- **1996 Perot:** the Reform Party's "Principles of Reform" from janda.org,
  not APP. Re-spaced and undated.
- **1840 Whigs:** campaign positions from secondary sources
  (`verbatim: false`).
- **1844 Whig Texas plank:** Clay's Raleigh letter. The platform says
  nothing on Texas.
- **Before 1840:** documented positions, not platforms (C29).

**D30 · Medium · by design · unopposed years**
1789 and 1792 have no D side, and 1820 has no R side. Those years get one
ballot line and no swap arm, and their verdicts omit the runner-up. Their
interviews measure turnout and dissent, not a contest (C28).

**D31 · Low · open · masks and label letters**
- Common-word surnames (Clay, King, White, Grant, Bell, Smith and others)
  are matched case-sensitively, or only with a first name or title, so
  ordinary words don't count as leaks. A lower-case mention isn't caught.
- Generic modern surnames (Dean, Clark, Harris, Stein, Ryan) cause false
  naming violations in compiled specs. A false hit forces a recompile, not a
  leak.
- Masks run in sequence and produced "the the administration party". The
  doubled "the" now collapses.
- Label pools leave out initials of candidates, parties and prominent
  figures. Questionable picks: P in 1936 and 1940 (Perkins; it may read as
  "President"), E in 1932.

**D32 · Low · fixed · 1920 wording in other years**
Found while building profiles, and fixed in the pipeline generalisation:
- Every brief said "Election Day is Tuesday", which is wrong for 1789–1844,
  when states chose on their own days.
- `compile_system` called any third candidate "the independent Progressive
  candidate" (Wirt, Van Buren, Fillmore, Breckinridge, Wallace, Anderson,
  Perot).
- `run._lead` always named R as the winner, which is wrong in every D year.

**E7 · by design · what-ifs in other years (`whatifs.py` `years`, `text_for`)**
The 1920 what-ifs now run in other years: `everyone` in all of them,
`fifteenth` in 1892–1964, `no-19th` from 1920, and `league` in 1920 only.
Their invented facts (E1–E3) were written for 1920. Other years get them by
rewriting "1920" in the assumption and borrowed text; 1924 is kept as it
was. Nobody has read the rewritten text year by year.

**E8 · fixed · the 31 example what-ifs**
Thirty-one example what-ifs were run as chips across 28 years (about $7.80 in all). Four compiled specs were wrong and were fixed by hand or rebuilt. Each fix is recorded in the spec's `hand_edited`:
- **1972, no voting under 21:** the spec barred every adult. The cells have no age split, so `franchise.share` now bars a uniform 8.1% slice of every cell (the 18–20 share of 18+ in 1970 [I]). That slice votes like the rest of its cell, which understates the change, because young voters turned out less and leaned toward the challenger.
- **2000, Florida restores felons' rights:** the spec enfranchised every Southern adult. The spec now reaches Florida only (new `reach.state`), and the action lifts only the felony bar (new `franchise.reason: felony`). Newly eligible voters vote like their cell. Uggen & Manza assume lower turnout but a strong lean toward the administration party, so the cell assumption understates the change.
- **2000, Nader doesn't run:** with no named third in 2000, the compiler invented a candidate whose positions came from Perot's 1992 run. Nader is now 2000's named third: his per-state votes come from Wikipedia (2,882,955 nationally), and the profile has a blinded descriptor. The 2000 returns changed only in the `third` column, and every other year is byte-identical.
- **1932, no crash:** an earlier batch was killed mid-run, which left the key in the config but not in the bundle. The bundle was republished.

Four what-ifs (1844, 1856, 1860, 1916 Hughes) stopped at the research cost check: about $0.27–0.28 against a $0.175 estimate, because 19th-century searches return longer pages. The saved evidence was reused, so no search was repeated. The research estimate is probably low for pre-1900 topics.

Two code fixes:
- Parallel what-if runs collided on `sessions/intake-status.tmp`. The temporary file now carries the process id.
- When the winner changes, the headline now puts the new winner's electoral votes first (`serialize.winner_ev`). Before, it printed "Blaine wins, 129–272".

**F7 · Medium · open · slice-source sentences (`profiles/<year>.json`)**
Each profile's `slice_sources` names the census vintages its year uses
(e.g. 1952 "the 1950 census aged", 2020 "ACS 2019/2021"). They were written
before most populations existed, so they describe the intended build, not
what `data.population` does. 1932 and 1936 promise the 1930 Mexican count
folded into white (C20). 1972–2024 cite vintages that differ from the files
actually used (C27).

**Next:** generate each sentence from the population build's own
provenance.

**F8 · Low · open · electoral-vote labels (`ev_label`)**
Some labels are conventions a reader could dispute (see also F4):
- **1789–1800:** before the 12th Amendment only each side's top man counts.
  Second votes (Adams 1789–92, Pinckney, Burr) aren't O. 1800 was a 73–73
  Jefferson–Burr tie decided by the House.
- **1824:** Adams won the House contingent election, not the electoral vote
  (84–99–78).
- **1832:** O is Wirt's 7 plus Floyd's 11 from South Carolina's legislature.
- **1860:** O is Breckinridge plus Bell.
- **1872:** 286–63 counts the D-ticket votes counted after Greeley's death.
  286–66 is also defensible.
- **2000:** one DC elector abstained, which isn't an O vote.
- **Order varies.** 1948 and 1956–1984 put the winner first (1948
  303–189–39, 1960 303–219–15). 1789–1836 and 1988–2024 are R–D(–O).

**F9 · Low · open · place matching in typed text (`places.ts`)**
"Washington, D.C." in a typed what-if lights up Washington state. The D.C.
rule ends in `\b`, which can't match after the final period. Carried over
from the source and kept as is during the port.

**Next:** end the D.C. pattern with a lookahead for a non-word character or the
end of the text, and add a test.

**G7 · Medium · open · generators outside the repo**
The all-years profiles, configs and platform files were written by scratch
scripts kept in session scratchpads (`gen_d1.py`, `d3_build.py`,
`d3_planks.py` and unnamed ones for the other years). So was the 1920/1924
invariant capture (`inv/capture.py`). The felony-rate parsers live in the
cache beside their PDFs. None can be rerun from the repo; the outputs are
the record.

**Next:** move the generators into `scripts/`.

**G8 · Low · open · holdout states**
Holdout sets were drawn three ways. live-1924 reuses 1920's draw. 1789–1836
take a quarter of the hand-listed popular-vote states, some of them
uncertain (TN 1800). 1880–2024 take
`sorted(random.Random(year).sample(states, 12))`.

**Next:** one formula, written down before any holdout check is run.

**G9 · Low · by design · 1920/1924 invariant**
The generalisation was checked against a capture taken before any edit.
Every plan request, compile request and publish bundle for 1920 and 1924 is
byte-identical, except 1924's compile prompt: its list of existing what-ifs
now includes `no-19th`. Each typed 1924 text misses the compile cache once
(about $0.02); no brief changes. Legacy 1916–1924 data still goes through
the untouched loaders.

**D33 · High · fixed (p6) · interviews that didn't measure the change**
A 1916 what-if ("war after the Lusitania") showed the interviews mostly never
took the change in: voters at war since 1915 still praised the President for
keeping the country out of war, because the real 1916 newspapers in their
briefs said so (non-1920 years could drop no item: `drop_topics` only knows
1920's codes). Half the twelve slots went to women who could not vote in either
world, no German-American, Irish-American or Western voter was asked (the
live configs' `only_cohorts`), cohorts nobody was interviewed in got exactly
zero effect, and one or two people per cohort bootstrapped to almost no spread
("Hughes wins in 0 of 100 draws"). Compiled what-ifs now get, in the live
configs:
- **Stronger once-per-change passes.** Compile and extract on Opus at high
  effort; research on Sonnet at medium. They run once per change, not once
  per voter, so they are the cheapest place to buy judgement.
- **Staging** (`world.py`, Opus, high): the year's items the change makes
  false leave the counterfactual brief (by id, any year); up to two in-world
  items ("a local newspaper") and up to three consequences join it; a belief
  check is designed; the groups history says the change moves are named.
- **A belief check, asked first** in each counterfactual interview (p6). Its
  two worlds must answer it differently, or it is discarded. A wrong answer
  leaves the interview out.
- **An audit** (Opus, medium) of each counterfactual answer's reason and
  quote, without its vote: reasoning from the world as it was leaves the
  interview out, whichever way it voted.
- **Escalation**: a bulk-model (Haiku) answer that fails either check is
  asked again, control and counterfactual, on Sonnet; the pair is compared
  within itself as always. Failures are counted and shown as confidence
  reasons whether or not escalation rescued them.
- **No wasted slots**: someone who cannot vote in either world is replaced by
  the next person drawn from the cohort (the first draws are unchanged), so
  each cohort's effect describes the people it can move, which is where the
  backbone applies it.
- **Focus cohorts**: up to six cohorts the staging pass names are interviewed
  for that what-if even when `only_cohorts` leaves them out.
- **Borrowed cohorts**: a cohort the change reaches but nobody was asked in
  takes the interviewed cohorts' effect (same sex and group first), per draw,
  plus between-cohort noise (their spread, at least 0.15 logit), and the
  evidence prior applies to it.
- **Spread from who was drawn**: each cohort's draws are widened to at least
  the person-to-person spread of a mean of its n people, estimated from every
  pair in the run.
Pre-registered what-ifs and runs are unchanged: every new behaviour is off in
the config defaults and gated to compiled what-ifs. Costs: about $1–2 per
typed what-if instead of about $0.50. The same day every dollar ceiling was
removed: the daily cap (SIMULACRA_DAILY_DOLLARS), the per-what-if cap
(`whatif_dollars`) and the interview caps (`max_dollars`, `max_requests`).
Every paid call is still priced first and recorded in sessions/spend.jsonl,
and a stage costing over 1.5x its estimate still stops.

**D35 · Medium · fixed (staging w2) · focus slots and an easy check**
In the first staged run (1940, "Britain Falls"), the six focus slots all went to
the first named group ("anyone in the Northeast"), and two of them to
non-citizen cohorts that yield no interviews: the Pacific Coast and the
Midwest's naturalized immigrants, also named, were never asked. The slots now
go round the named groups in turn (largest cohort first), and a cohort in
which no one can vote takes no slot. The belief check was answered right by
30 of 30 because its answer was printed in the brief; it now asks about a
consequence the brief never states, with three or four plausible options. The
audit now counts a passing phrase that relies on a state of affairs the change
ended (an ally "still fighting" after it surrendered) as contradicting it.

**D34 · High · fixed (compiler c4) · a typed what-if silently replaced**
"America loses WW2", typed into 1940, was compiled as "Britain Falls, America
Stands Alone": the United States wasn't at war by that election, and the
compile prompt (never decline; no way to say "not what you asked") let the
model substitute the nearest possible change and rename it. Everything after
compile measured the substitute; only the "What changed" line hinted at it.
Since c4 the compiler models the change as asked: a change that could not have
happened by the context date gets the world in which it did, with the earlier
departures from history it needs stated as fact, graded a-stretch or
fantastical. It records `fidelity`; a reinterpreted change leads its result,
its "how I got this" and the progress steps with a sentence saying what was
asked and what was modelled, and never takes the reader's own words as its
keywords. The 1940 substitute is kept as its own what-if, marked
reinterpreted, without the words "america loses ww2".
