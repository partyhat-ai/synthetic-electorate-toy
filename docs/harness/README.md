# Simulacra Americana harness

This is the simulation behind the page. Its code and data sit at the repo root
(`simharness/`, `configs/`, `extracts/`, `runs/`); this README lives in
`docs/harness/`, and the method documents stay at the root.

- **The statistical backbone** decides the counts.
- **LLM agents** will supply the counterfactual response and the quotes.

Read [`METHOD.md`](../../METHOD.md) first. Then read [`EVAL.md`](../../EVAL.md) (the 1920 prototype's results, failures included).

Nothing here is imported by the page. The bundle's shape is
`simharness.serialize.Bundle`, with a shared example at
`tests/fixtures/bundle.example.json` (the page's zod schema parses the same file).

## Layout

| Path | What |
|---|---|
| `simharness/config.py` | Run config. A run's id hashes the config and the data manifest. |
| `simharness/data.py` | Loaders for the cache (labels, census, franchise, corpus) |
| `simharness/backbone.py` | Turnout and choice by cell, 400 posterior draws, exact calibration |
| `simharness/cohorts.py`, `agents.py` | Agent cohorts (merge rule) and invented people drawn from them |
| `simharness/aggregate.py`, `serialize.py` | Draws → states, EV and ranges → the page's shape |
| `simharness/evaluate.py`, `benchmarks.py` | Pre-registered checks. Only these read held-out benchmarks. |
| `simharness/run.py` | The command line (`python3 -m simharness.run <stage>`) |
| `simharness/pipeline.py` | The stages: backbone and evaluate (`Run`) |
| `extracts/` | IPUMS extract definitions: we ship definitions, never microdata |
| `runs/<id>/` | Everything a run wrote: config, fit, validation |

The raw data lives outside the repo, in `SIMHARNESS_CACHE`. It defaults to
`~/research_notes/historical_election_sim_data/harness_cache`, and each folder
there has a `PROVENANCE-*.md`.

Some sources can't be redistributed (IPUMS, NHGIS), and the UI agent's dev
server shouldn't watch the cache. Only aggregates reach `runs/`.

## Run it

From the repo root (`pip install -e '.[test]'` once):

```sh
python3 -m simharness.run backbone      # fit
python3 -m simharness.run evaluate      # pre-registered checks → validation.json
python3 -m pytest -q                    # fast unit checks (tests/)
```
