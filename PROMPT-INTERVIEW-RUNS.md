# Prompt: cheap live interview runs, and seeing them in the page

Paste everything below the line into a fresh Claude Code session.

---

You're picking up the Simulacra Americana simulation harness. Your job:

1. Get an API key from Cameron.
2. Walk Cameron through small, cheap, manual interview runs against the real
   Claude API.
3. Make it quick to see the results in the live page, beside the robot.
4. Make it quick to change what the interviews collect and how the page shows
   it.

Work in short steps. Show Cameron what each step will do and cost, then do it.

## Read first (in this order)

The harness lives in the repo root (code in `simharness/`; this README is `docs/harness/README.md`).

1. `README.md`: the layout and the pipeline stages.
2. `DISCLOSURES.md`: every known flaw. Log anything new you find here, the
   moment you find it.
3. `EVAL.md`, deviation 10: why the 1920 prototype's agent answers
   (Claude Code subagents) must be redone on the API.
4. `METHOD.md` §C: how the interviews work (control, counterfactual, probe,
   label swap).
5. `../NOTE-FOR-UI-FROM-HARNESS.md` and `../HANDOFF-UI.md`: the page's
   contract and its rules.

## Step 1: the API key

Ask Cameron for a key. Offer these routes, in this order of preference:

**a) A file outside the repo.** Cameron runs this in his own terminal, not
in this chat, so the key never enters the transcript:

```sh
mkdir -p ~/.config/simulacra && chmod 700 ~/.config/simulacra
printf 'ANTHROPIC_API_KEY=%s\n' 'sk-ant-…' > ~/.config/simulacra/anthropic.env
chmod 600 ~/.config/simulacra/anthropic.env
```

Then add a loader to `simharness/llm.py`: use `ANTHROPIC_API_KEY` if it is
set, otherwise read that file. Never print the key, log it, or write it into
the repo or a run folder.

**b) `ant auth login`,** if Cameron installs the `ant` CLI. The SDK picks up
the profile with no key in any file.

**c) Export the key in the terminal that launches Claude Code**, then restart
the session.

**Rules:**
- Don't ask Cameron to paste the key into the chat, and don't use the `!`
  prefix for it. Both put it in the transcript.
- Don't search the machine for keys (keychain, `.env` files). The last
  session's attempt was blocked, correctly.
- If Cameron pastes a key anyway, use it once to write file (a), tell him it
  is now in the transcript, and suggest rotating it later.

**Environment.** The system Python has `anthropic` 0.46, which predates
`output_config`. Make a venv outside the repo:

```sh
python3 -m venv ~/.venvs/simharness
~/.venvs/simharness/bin/pip install 'anthropic>=1.0' numpy pandas scipy
```

Run every harness command with `~/.venvs/simharness/bin/python`.

## Step 2: ultra-cheap runs, one rung at a time

Before sending anything, the harness must:
1. print a dry-run estimate: requests × model × input and output size, in
   dollars;
2. refuse to send past a hard cap.

Ask Cameron for the cap. Suggest $1 per run until the ladder is climbed.

### Knobs to add to `configs/*.json` → `agents`

All additive; defaults keep today's behaviour.

| Knob | Meaning |
|---|---|
| `arms` | Which of `control`, `cf`, `swap` and `probe` to send |
| `only_cohorts` | A list of cohort keys to interview; every other cohort is skipped |
| `max_requests` | A hard cap on requests per run |
| `max_dollars` | A hard stop, from the estimate |
| `check_share` | Set to 0 to skip the Opus subsample |

Filter the requests in `agentlayer.build_requests`. Enforce the caps in
`Run.ask`.

### Model notes (check `/claude-api` before coding against them)

- **`claude-haiku-4-5` is the cheapest.** It **rejects `output_config.effort`**
  and takes thinking only as `budget_tokens`. Give `AnthropicBackend.params`
  a per-model branch: no `effort` for Haiku. Confirm Haiku supports
  structured outputs before relying on it; if it doesn't, fall back to a
  strict tool.
- **`claude-sonnet-5-5` is the pre-registered bulk model.** It rejects
  non-default temperature. Use `effort: low`.
- **Use `anthropic-batch` for anything past a smoke test.** Half price;
  results in minutes to hours.
- **Hash `simharness/*.py` into the run id** (DISCLOSURES G1), so a changed
  prompt or code can't reuse an old run's folder.

### The ladder

Stop after each rung, show Cameron the answers, and ask before the next.

| Rung | What | Config | Scale |
|---|---|---|---|
| 0. Smoke | 1 request, `anthropic` backend | One cohort, `arms: ["control"]`, `per_cohort: 1` | about a cent |
| 1. Micro-pair | League what-if, paired arms only | 6 of the largest voting cohorts × 2 agents; `arms: ["control", "cf"]`; `what_ifs: ["league"]`; `check_share: 0` | 24 requests |
| 2. Leakage check | Rung 1 plus probes and swaps on those agents | `arms: ["control", "cf", "swap", "probe"]` | about 40 requests |
| 3. Pilot | The pre-registered prototype on the API | `configs/prototype-1920.json` with `backend: "anthropic-batch"` | 442 requests |

**Rung 0.** Print the raw JSON, `usage` and the actual cost. Check:
- the schema came back valid;
- the answer reads like a person, not a summary.

**Rung 1** is the cheapest run that yields a paired effect. Everything else
(backbone, evaluation, publish) is free and runs locally.

**Rung 3** replaces the subagent answers. Then:
1. rerun `analyze`, `evaluate` and `publish`;
2. compare the result with `EVAL.md`;
3. update `DISCLOSURES.md` D1–D8;
4. update `EVAL.md` with the new numbers.

Keep the old run folder; don't overwrite it.

**Commands, per rung:**

```sh
H=~/.venvs/simharness/bin/python
cd "$(git rev-parse --show-toplevel)"
$H -m simharness.run backbone --config configs/<rung>.json   # free, ~10 s
$H -m simharness.run plan     --config configs/<rung>.json   # prints request counts; add the estimate here
$H -m simharness.run ask      --config configs/<rung>.json   # the only step that spends money
$H -m simharness.run analyze  --config configs/<rung>.json
$H -m simharness.run publish  --config configs/<rung>.json   # → runs/<id>/published/1920.json
```

**After every run:**
- Read five answers aloud to Cameron: the quote, the reason, and the
  control-vs-counterfactual pair.
- Report L1 (the probe hit rate) and A2 (homogenization) if the rung
  included them.
- Log anything odd in `DISCLOSURES.md`.

## Step 3: see it in the live page

**The dev server.** Run
`~/Documents/fromDesktop/creator-rows-dev-kit/start-web.sh`. It serves
<http://localhost:5185> and logs to `creator-rows-dev-kit/logs/web.log`.

- `/simulacra-americana?sample=1&year=1920` is the sample stand-in.
- Without `sample=1`, the page calls `AUTH_API_BASE + /api/simulacra`:
  production, which has no simulation service.

**Point the page at a local bundle.** This is the fastest loop, and nothing
touches the production auth server.

1. **A dev server for the router** (new file, `harness/serve/dev-server.cjs`,
   about 20 lines):
   - Express on `:8787`.
   - Mounts `serve/simulacra.ts` at `/api/simulacra`.
   - Sets `SIMULACRA_BUNDLES` to the run's `published/` folder.
   - Sends CORS headers for `http://localhost:5185`, including a preflight
     for `Content-Type` and `Authorization`: api.js uses authenticated fetch
     when signed in.
   - `express` isn't installed in the web repo. Borrow the auth server's,
     read-only:
     `NODE_PATH=~/Documents/fromDesktop/auth-server/partyhat-authorization-server/node_modules node serve/dev-server.cjs`.
   - `serve/package.json` already marks the folder as CommonJS.
2. **A dev-only override in the page.**
   - `createSimulacraApi(base)` already takes a base URL.
   - In `src/routes/simulacra-americana/+page.svelte`, near line 39, pass
     `params.get('simapi')`. Only do this when `import.meta.env.DEV`, so a
     link can never redirect production users.
   - Then open
     `http://localhost:5185/simulacra-americana?simapi=http://localhost:8787&year=1920`.
3. **Restart after each publish.** The router caches bundles in memory, so
   restart the dev server after a new `publish`. Or add a `?reload=1` that
   clears the cache in dev.

**Don't:**
- set `PUBLIC_AUTH_URL` for this, because it reroutes all of the app's auth;
- deploy the router to the real auth server. That is a production deploy:
  ask Cameron, and only on his word.

## Step 4: change what the interviews collect

A field travels through five places. Change them together, and bump the
prompt version, because a new question means a new instrument and new runs:

| Place | File | What to change |
|---|---|---|
| 1. The instructions | `simharness/prompts.py`: `SYSTEM` (field descriptions) | Say what the field is and its tone rules |
| 2. The schema | `prompts.answer_schema` | Add the field and add it to `required`. Keep `additionalProperties: false`. |
| 3. The question | `QUESTIONS` (3 paraphrases) | Only if the field needs asking. Keep all three parallel. |
| 4. Numbers | `simharness/paired.py`: `normalize` | Only if the field feeds a count. Most fields don't. |
| 5. The payload | `simharness/run.py`: `_voters` | Add it to the voter object; it reaches the page through `GET /elections/:year/voters/:slice` |

Then:
- bump `PROMPT_VERSION` in `prompts.py`;
- document the field in `NOTE-FOR-UI-FROM-HARNESS.md`;
- rerun from `plan`, which starts a new run id.

Never mix answers from two prompt versions in one analysis.

**Good first fields to try,** each cheap to test at rung 1:
- `worry`: the one thing on the person's mind this week, in 8 words.
- `changed_because`: counterfactual arm only. What in their world made the
  difference, in one sentence.
- `heard_from`: which dated item moved them. This already exists as
  `sources_used`, so display it rather than adding it.

## Step 5: change how it shows beside the robot

- **Where the robot's words come from.**
  - `say(...)` in `src/routes/simulacra-americana/+page.svelte`, around lines
    431–475, picks the robot's line.
  - For a picked group it returns `{ quote, by, text }`, around line 457,
    from the voter object.
  - `src/lib/simulacra/WhatIf.svelte` renders the bubble. The robot sits
    in the slot beside it.
- **Voter fields already served** (NOTE-FOR-UI §2): `quote`, `controlQuote`,
  `cohort`, `cohortAdults`, `weight`, `contextDate`, `sources[]`,
  `memorizationExposed`, `unchanged`, `namesRestored`.
- **Cheap display ideas,** one line each, no new chrome:
  - A provenance line under the quote: "From the Butler County Press,
    8 Oct 1920 · stands for 1.2 million adults".
  - The quote follows the History/Rerun switch: `controlQuote` in History,
    `quote` in the rerun.
  - A quiet "The model knows how 1920 ended" when `memorizationExposed`
    is set.
- **Rules from HANDOFF-UI.md:**
  - Dark mode is a CSS filter: author neutrals in light values.
  - Text wears ink, never party colours.
  - Copy is sentence case with no exclamation marks; buttons are Title Case.
  - Only about 41px is free above the composer at 1440×900. Check
    `?sample=1&year=1912&light` after a rerun.
  - `$:` statements track only the names written in them: pass new state
    into `say()` as arguments.
  - `?sample=1` must keep working.
- **Check your work:**
  - Run the compile check in HANDOFF-UI.md, "Checking your work".
  - Take one screenshot if the layout moved.
  - No headless test-harness runs unless Cameron asks.
- **Coordination.** The page belongs to a UI session (last seen as
  `vaultsync-desktop-3d`). Before editing `+page.svelte`, `WhatIf.svelte` or
  any existing file in `src/lib/simulacra/`:
  - run `ListAgents`;
  - if that session is live, send it a short note of what you'll change;
  - or get Cameron's go-ahead.

  Everything under `harness/` is yours.

## Guardrails

- **Money.**
  - Show the estimate before every `ask`.
  - Never exceed Cameron's cap.
  - Stop if a run's actual cost exceeds its estimate by more than 50%, and
    say why.
- **The key.** It lives only in `~/.config/simulacra/anthropic.env`, a
  profile, or the environment. It never goes in the repo, a run folder, a
  log or a message.
- **Git.** Don't commit or push; that's Cameron's call. Don't run git
  commands that touch the working tree: another session works in this repo.
- **Honesty.**
  - Every surprise, bug or post-hoc change goes into `DISCLOSURES.md` with
    an ID.
- **Production.** No deploys to the auth server, and no changes to production
  config, without Cameron's explicit yes.
