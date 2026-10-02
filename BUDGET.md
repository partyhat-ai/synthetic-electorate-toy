# Budget

## Prices

Claude API list prices, per million tokens, from the Claude API reference:

| Model | Input | Output | Batch |
|---|---|---|---|
| `claude-sonnet-5-5` | $2 | $10 | Half price |
| `claude-opus-5-5` | $4 | $20 | Half price |

**Prompt caching doesn't help here.** The shared system prompt is about 380
tokens, below the minimum cacheable prefix. Every brief after it is unique to
one person. So none of the figures below assume caching.

## Tokens per request (measured on the p1 requests)

**Input.**

| Part | Size |
|---|---|
| System prompt | 1,524 characters |
| Brief and question | 3,554 characters on average |
| Output schema | 660 characters |

That is about **1,450 input tokens** per request, at about 4 characters per
token. `count_tokens` wasn't available without an API key; recount with it
before relying on the figures to within 20%.

**Output.** The answer JSON is about 60 words of text plus keys, roughly 150
tokens. Low-effort adaptive thinking adds an unmeasured amount, budgeted here
at 400 tokens. That gives about **550 output tokens** per request.

| Per request | Standard | Batch |
|---|---|---|
| Sonnet 5.5 | $0.0084 | $0.0042 |
| Opus 5.5 | $0.0168 | $0.0084 |

## The prototype, re-priced for the API

The prototype had 442 requests:
- 112 people
- 30 cohorts
- 4 agents per cohort
- 3 paraphrases
- Opus on 20% of people

| | Requests | Input tokens | Output tokens | Standard | Batch |
|---|---|---|---|---|---|
| Sonnet | 400 | 0.58M | 0.22M | $3.36 | $1.68 |
| Opus | 42 | 0.06M | 0.02M | $0.71 | $0.35 |
| **Total** | 442 | 0.64M | 0.24M | **$4.07** | **$2.03** |

The prototype itself ran through Claude Code subagents (EVAL.md, deviation
10), so it spent no API money. It spent 0.93M subagent tokens (the nine answer batches) in the
session instead.

## Recommended production configuration, per election

Changes from the prototype:

| Setting | Prototype | Production | Why |
|---|---|---|---|
| Agents per cohort | 4 | 12 | Measures homogenization (A2), and the pre-registered shrinkage pseudo-count of 8 stops dominating |
| Agent cohorts | 30 | 36 | |
| Opus share | 20% | 20% | Unchanged |
| Paraphrases | 3 | 3 | Unchanged |

What-ifs per election: 2 issue (full paired arms) and 2 franchise
(cross-check arms on the cohorts reached, about half).

| Arm | Requests |
|---|---|
| Control (Sonnet) | 408 |
| Issue counterfactuals: 2 × 408 | 816 |
| Franchise cross-checks: 2 × about 200 | 400 |
| Label swap (half of people) | 204 |
| Recall probe (a quarter of people) | 102 |
| Opus: 20% of control and issue arms | 245 |
| **Total** | **about 2,175** |

That is about 3.2M input and 1.2M output tokens per election rerun.

| Scope | Standard | Batch (recommended) |
|---|---|---|
| One election, full precompute | $20.30 | **$10.15** |
| All 60 elections | $1,218 | **$609** |
| One user-typed issue what-if not precomputed: 408 counterfactuals + 82 Opus | $4.80 | $2.40, but minutes to hours |

The backbone is free to rerun: about 10 seconds of CPU for 400 draws, and
about 7 seconds to publish every combination (a 0.43 MB bundle for 1920).

## What runs where

| Part | Where | Why |
|---|---|---|
| Census, franchise and returns ingestion; population draws | Offline, in the harness | Data terms (IPUMS and NHGIS can't be redistributed); slow; changes only with new data |
| Backbone fit, calibration, 400 draws | Offline | Deterministic by seed; about 10 s per election, but it needs numpy and scipy |
| Agent interviews: control, counterfactuals, probes, swaps | Offline, through `anthropic-batch` | Half price, and nothing waits on it; the pre-registration fixes prompts before the run |
| Analysis, validation, publishing the bundle | Offline | Produces `published/<year>.json` |
| `/api/simulacra`: election, runs, voters | Auth server (`serve/simulacra.ts`) | Lookup, plus re-tallying hand edits; no model calls; about 1 ms per request |
| Reading typed what-ifs into a key | Auth server | Keyword match today. A `claude-haiku-4-5` classifier call (about $0.001 each) is the upgrade; it must refuse rather than substitute. |
| A genuinely new typed issue what-if | Offline queue | Needs 400+ interviews; answer with "I haven't run that yet", and queue it |

**The auth server never holds microdata or an LLM key for the page's core
flow.** Bundles are aggregates: 0.43 MB for 1920, with every combination of 4
what-ifs.
