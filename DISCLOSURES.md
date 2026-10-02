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
