# Simulacra Americana harness

This is the simulation behind `/api/simulacra`. Its code and data sit at the repo
root (`simharness/`, `configs/`, `whatifs/`, `extracts/`, `runs/`,
`serve/`); this README and the UI note live in `docs/harness/`, and the method
documents stay at the root.

- **The statistical backbone** decides the counts.
- **LLM agents** supply the counterfactual response and the quotes.

Read [`METHOD.md`](../../METHOD.md) first. Then read [`EVAL.md`](../../EVAL.md) (the 1920 prototype's results, failures included).

**[`VALIDITY.md`](../../VALIDITY.md)** takes stock of what the harness can and can't claim: contamination by the language model's knowledge, leakage, historical bias, the held-out checks that exist and the ones that don't, and the next steps in order.

**[`DISCLOSURES.md`](../../DISCLOSURES.md)** is the running log of every known inaccuracy and honesty flag.
Add to it the moment something is found.

Nothing here is imported by the page; the page reads bundles through the
server. The contract changes the page could use are described in
[`NOTE-FOR-UI-FROM-HARNESS.md`](NOTE-FOR-UI-FROM-HARNESS.md). The bundle's shape is
`simharness.serialize.Bundle`, with a shared example at
`tests/fixtures/bundle.example.json` (the server's zod schema parses the same file).

## Layout

| Path | What |
|---|---|
| `simharness/config.py` | Run config. A run's id hashes the config and the data manifest. |
| `simharness/data.py` | Loaders for the cache (labels, census, franchise, corpus, platforms) |
| `simharness/backbone.py` | Turnout and choice by cell, 400 posterior draws, exact calibration |
| `simharness/whatifs.py` | The what-ifs: what each changes, its assumption, and the facts a counterfactual brief states |
| `simharness/cohorts.py`, `agents.py` | Agent cohorts (merge rule) and invented people drawn from them |
| `simharness/prompts.py` | The versioned prompts: blinded control, non-hypothetical counterfactual, probe, schemas |
| `simharness/agentlayer.py` | Every model request for a run |
| `simharness/llm.py` | Backends: `anthropic`, `anthropic-batch`, `transcript`, `mock` |
| `simharness/paired.py` | Paired differences, cohort bias, the pre-registered shrinkage |
| `simharness/quotes.py` | Quote selection and the stereotype audit |
| `simharness/aggregate.py`, `serialize.py` | Draws → states, EV and ranges → the page's shape |
| `simharness/evaluate.py`, `benchmarks.py` | Pre-registered checks. Only these read held-out benchmarks. |
| `simharness/scenario.py` | Any typed what-if → a spec of one of five kinds (franchise, population, issue/event, candidate) with generic mechanics |
| `simharness/evidence.py` | Historical evidence: web-search research, grounded extraction, source tiers, agreement, blend, confidence tiers |
| `simharness/intake.py` | Typed what-if intake: compile → research → register → run → `serve/bundles/`; the router's queue |
| `simharness/profiles.py` | One profile per election (names, blinded descriptors, label letters, ballot wording, sources): 1920 and 1924 |
| `simharness/run.py` | The command line (`python3 -m simharness.run <stage>`) |
| `simharness/pipeline.py` | The stages: backbone, plan, ask, analyze, verify, evaluate (`Run`) |
| `simharness/publish.py` | The publish stage: every what-if combination → the bundle |
| `serve/simulacra.ts`, `serve/index.ts` | The Express router that serves the bundles, and the server that mounts it at `/api/simulacra` next to the static page |
| `serve/bundles/<year>.json` | The bundles the server serves (`SIMULACRA_BUNDLES` overrides the folder) |
| `extracts/` | IPUMS extract definitions: we ship definitions, never microdata |
| `runs/<id>/` | Everything a run wrote: config, fit, requests, answers, analysis, validation, `published/1920.json`. The repo keeps only `config.json`, `analysis.json`, `validation.json` and `published/`; `fit.pkl`, `effects.pkl` and `agents/` are regenerable and stay local |
| `runs/_cache/` | Identical-request answer cache (regenerable from `runs/*`; gitignored) |
| `whatifs/<key>.json`, `whatifs/evidence/<key>.json` | Compiled what-ifs (exploratory) and every what-if's researched evidence; both hashed into run ids |
| `sessions/` | Dev only, gitignored: typed requests, the unknown-text queue, intake outcomes, the spend ledger |
| `scripts/harness/bundle_fixture.py` | Trims the served 1920 bundle into the shared contract example |
| `scripts/harness/sessions-report.py` | What people typed, the share unmodelled, unknowns by kind, today's spend |

The raw data lives outside the repo, in `SIMHARNESS_CACHE`. It defaults to
`~/research_notes/historical_election_sim_data/harness_cache`, and each folder
there has a `PROVENANCE-*.md`.

Some sources can't be redistributed (IPUMS, NHGIS), and the UI agent's dev
server shouldn't watch the cache. Only aggregates reach `runs/`.

## Run it

From the repo root (`pip install -e '.[test]'` once; add `'.[llm]'` for the paid stages):

```sh
python3 -m simharness.run backbone      # fit + unchanged-run reproduction
python3 -m simharness.run plan          # agents and requests (no model calls)
python3 -m simharness.run ask           # send requests (backend from the config)
python3 -m simharness.run analyze       # paired effects, probes, bias, audit
python3 -m simharness.run evaluate      # pre-registered checks → validation.json
python3 -m simharness.run publish       # every what-if combination → published/1920.json
python3 -m pytest -q                    # fast unit checks (tests/)
```

Typed what-ifs and historical evidence (all paid stages priced first; $0.50 per
what-if, $2 a day via `SIMULACRA_DAILY_DOLLARS`; see `simharness/intake.py`):

```sh
H=~/.venvs/simharness/bin/python
$H -m simharness.run whatif --text "charlie chaplin ran as an independent" --config configs/live-1920.json
$H -m simharness.run whatif --queue --config configs/live-1920.json     # what the page couldn't model
$H -m simharness.run research --config configs/live-1920.json           # evidence for the config's what-ifs
$H -m simharness.run research --key league --refresh | --reextract ...  # one what-if; search again, or re-read saved notes
```

How a typed what-if is modelled:
1. **Compile** (Sonnet): the words become a settled-fact change of one kind,
   with who it reaches, a plausibility grade, keywords and research questions.
   Nominee and party names are sent back and masked. A request that means an
   existing what-if only adds keywords.
2. **Research** (Sonnet + web search): scholarship, official statistics and
   archives on the change itself, the same groups in the most similar
   situations, and any named person's record before the context date.
3. **Extract** (Sonnet, structured): findings grounded in the sources the
   search returned. Each is graded by source tier × match, and signed for the
   scenario (a situation the change undoes counts the other way).
4. **Interview**: the usual paired control/counterfactual briefs. A candidate
   gets a third labelled ballot line (p4). Identical earlier requests are
   reused, so only the new arm is paid for.
5. **Evaluate**: the interviews against the record on votes and turnout
   (corroborated, consistent, contradicted, untested). For exploratory
   what-ifs, the evidence is also a precision-weighted prior on each cohort's
   effect.
6. **Confidence**: high, medium, low or very low ("Extremely low
   confidence"), with the reasons. The tier reaches the page as
   `confidenceTier`, `confidenceFlags` and `confidenceReasons`, and as a
   sentence in the summary.

With `SIMULACRA_LOG=1`, the server (`pnpm serve`) logs requests to `sessions/`, queues unknown text,
and reloads a changed bundle without a restart. `SIMULACRA_AUTORUN=configs/live-1920.json`
also starts the queue worker as text arrives (`SIMULACRA_PYTHON` picks the interpreter;
it runs from the repo root).

The `ask` stage depends on the backend:
- **`anthropic` or `anthropic-batch`:** needs `pip install -e '.[llm]'`
  and `ANTHROPIC_API_KEY`, or an `ant auth login` profile.
- **`transcript`:** writes `runs/<id>/agents/transcript/requests.jsonl` and
  reads `responses.jsonl`, one `{"id", "model", "answer"}` per line. Any
  runner can fill it.

Serve the bundles:
1. `pnpm build` (the static page, into `build/`), then `pnpm serve` (`serve/index.ts`, `PORT`, default 8787).
2. The router reads `serve/bundles/<year>.json`; set `SIMULACRA_BUNDLES` to serve another folder, such as `runs/<id>/published`.

## Years

- **1920** is the original fit, identified by the 1916→1920 suffrage
  experiment.
- **1924** is carried forward from it (`backbone.carry_forward`; DISCLOSURES
  C13–C16). It has its own `configs/live-1924.json`.
- `run verify` checks 1924: exact reproduction, plus Corder–Wolbrecht 1924.
  `evaluate` stays 1920's pre-registered set.
