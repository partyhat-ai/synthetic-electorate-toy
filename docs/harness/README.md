# Simulacra Americana harness

This is the simulation behind the page. Its code and data sit at the repo root
(`simharness/`, `configs/`, `extracts/`, `runs/`); this README lives in
`docs/harness/`, and the method documents stay at the root.

- **The statistical backbone** decides the counts.
- **LLM agents** supply the counterfactual response and the quotes.

Read [`METHOD.md`](../../METHOD.md) first. Then read [`EVAL.md`](../../EVAL.md) (the 1920 prototype's results, failures included).

**[`DISCLOSURES.md`](../../DISCLOSURES.md)** is the running log of every known inaccuracy and honesty flag.
Add to it the moment something is found.

Nothing here is imported by the page. The bundle's shape is
`simharness.serialize.Bundle`, with a shared example at
`tests/fixtures/bundle.example.json` (the page's zod schema parses the same file).

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
| `simharness/run.py` | The command line (`python3 -m simharness.run <stage>`) |
| `simharness/pipeline.py` | The stages: backbone, plan, ask, analyze, evaluate (`Run`) |
| `extracts/` | IPUMS extract definitions: we ship definitions, never microdata |
| `runs/<id>/` | Everything a run wrote: config, fit, requests, answers, analysis, validation. The repo keeps only `config.json`, `analysis.json` and `validation.json`; `fit.pkl`, `effects.pkl` and `agents/` are regenerable and stay local |

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
python3 -m pytest -q                    # fast unit checks (tests/)
```

The `ask` stage depends on the backend:
- **`anthropic` or `anthropic-batch`:** needs `pip install -e '.[llm]'`
  and `ANTHROPIC_API_KEY`, or an `ant auth login` profile.
- **`transcript`:** writes `runs/<id>/agents/transcript/requests.jsonl` and
  reads `responses.jsonl`, one `{"id", "model", "answer"}` per line. Any
  runner can fill it.
