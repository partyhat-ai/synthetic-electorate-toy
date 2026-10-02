# Synthetic voters (toy example)

A page that replays American presidential elections and reruns them with one
thing changed: who could vote, who lived where, what people cared about, or
who was on the ballot.

## Layout

| Path | What |
|---|---|
| `src/` | The SvelteKit page (TypeScript, Svelte 5) |
| `simharness/` | The simulation harness (Python): backbone, interviews, what-ifs, evaluation |
| `tests/` | Harness tests (pytest). Page tests sit next to their code (vitest) |

## Checks

```sh
pnpm lint && pnpm check && pnpm size && pnpm test
python -m pip install -e '.[test]' && python -m pytest -q
```

The rules every change follows are in `AGENTS.md`, and the vocabulary is in `CONTEXT.md`.
