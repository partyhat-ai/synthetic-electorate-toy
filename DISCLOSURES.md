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
