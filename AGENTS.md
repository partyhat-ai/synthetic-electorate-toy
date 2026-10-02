# Rules for coding agents

These are gates, not advice. CI enforces every one of them on the head SHA.

## Code
- TypeScript `strict`. No `any`. No `as` casts unless a `// SAFETY:` comment directly
  above states the invariant that was checked. Prefer `satisfies`. Use `never` for
  exhaustive switches.
- No file over 1,000 lines (`pnpm size`).
- No nested ternaries. One level of `a ? b : c` is fine.
- Parse at the boundary: every server response, `postMessage` payload, `localStorage`
  read and bundle file is parsed once, with zod, where it enters. Types derive from the
  schemas. Inside the boundary, branch on domain values, not `typeof`.
- Typed outcomes: API calls return `{ kind: 'ok' | 'error' | 'indeterminate' | 'unsupported' }`.
  `indeterminate` means a write may have landed (poll, don't resubmit). Never return an
  empty object as a stand-in for failure.
- No new runtime dependency without a one-line justification in the PR.

## Tests
- `pnpm test` (vitest) and `pnpm test:py` (pytest) run every suite. No module mocks:
  inject real interfaces.
- A test that needs raw data outside the repo skips with a stated reason. It never passes silently.

## Data and provenance
- Provenance hashes are computed by script, never typed.
- Only evaluate-stage code reads held-out benchmarks (`test_benchmarks_isolated`).
- Add to `DISCLOSURES.md` the moment an inaccuracy or assumption is found.
- No secrets in the repo. The harness reads `ANTHROPIC_API_KEY` or
  `~/.config/simulacra/anthropic.env`.

## Commits and merges
- Imperative subject under 70 characters that names the change. A body only when the
  reason isn't obvious. No hype words, no emoji.
- Squash merges only, with CI green on the head SHA.
