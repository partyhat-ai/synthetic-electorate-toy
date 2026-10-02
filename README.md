# Synthetic voters (toy example)

A page that replays American presidential elections and reruns them with one
thing changed: who could vote, who lived where, what people cared about, or
who was on the ballot.

Every election opens as it happened. A calibrated statistical backbone decides
the counts and reproduces the certified returns. Synthetic voters, interviewed
in both worlds, supply only within-person changes and the quotes. Every result
carries a confidence tier, and `DISCLOSURES.md` records what is assumed rather
than known.

Read `VALIDITY.md` for what the system can and cannot claim.

## Layout

| Path | What |
|---|---|
| `src/` | The SvelteKit page (TypeScript, Svelte 5) and the robot narrator (`src/lib/robot`) |
| `serve/` | The API server: serves the published per-year bundles under `/api/simulacra` |
| `simharness/` | The simulation harness (Python): backbone, interviews, what-ifs, evaluation |
| `tests/` | Harness tests (pytest). Page and server tests sit next to their code (vitest) |
| `configs/`, `profiles/`, `whatifs/` | Run configs, per-election profiles, compiled what-ifs and their evidence |
| `METHOD.md`, `EVAL.md` | How the backbone works, and the 1920 prototype's results, failures included |
| `VALIDITY.md`, `DISCLOSURES.md` | What the system can claim, and the log of every known flaw |
| `docs/harness/README.md` | Running the harness: stages, typed what-ifs, interview runs |

## Run it

```sh
pnpm install
pnpm serve          # API on :8787
pnpm dev            # page on :5173, proxies /api to :8787
```

`?sample=1` runs the page on an invented stand-in model, with no server, and
`?year=1896` opens a given year. `pnpm tsx scripts/model-check.ts` prints the
stand-in model's outcome for every story what-if.

## Checks

```sh
pnpm lint && pnpm check && pnpm size && pnpm test
python -m pip install -e '.[test]' && python -m pytest -q
```

The rules every change follows are in `AGENTS.md`, and the vocabulary is in `CONTEXT.md`.
