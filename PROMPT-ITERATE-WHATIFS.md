# Prompt: watch what people ask, and grow the what-if pipeline in small loops

Paste everything below the line into a fresh Claude Code session.

---

You're taking over the Simulacra Americana what-if pipeline: the harness that
interviews simulated 1920 voters on the Claude API and the page that shows
the reruns. Your job is a loop:

1. Log every what-if people type in the page.
2. Every so often, read what they asked, especially the ones the robot
   couldn't model.
3. Make the smallest change to the pipeline that turns the most common kind
   of unmodelled request into one it can model.
4. Run it cheaply, publish it, check it in the page, and report.

Work in short, shippable steps. Cameron is working in code-red mode: ship in
a straight line, fix forward, no test-harness runs unless he asks. The one
hard stop is money (below).

## Where things are

Harness: the repo root (code in `simharness/`; this README is `docs/harness/README.md`).
Read these first, in order:

1. `README.md`: the stages.
2. `PROMPT-INTERVIEW-RUNS.md`: how the previous session set up keys, the
   venv, cost caps and the page link. Everything in it still holds.
3. `DISCLOSURES.md`, including the log at the bottom (G2, D9–D13 are this
   week's). Log every new surprise there with an ID, the moment you find it.
4. `simharness/whatifs.py` (`REGISTRY`: what a what-if is), `agentlayer.py`
   (how its interviews are built), `prompts.py` (`SYSTEM`, `QUESTIONS`,
   `PROMPT_VERSION`, now `p3`) and `run.py` (`publish`, `_bundle`,
   `_voters`, `_interviews`).
5. `serve/simulacra.ts`: the router. `readText` matches typed words to a
   what-if by keyword (`bundle.words`); anything unmatched comes back as
   `unknown`, and the robot says "I couldn't turn … into a change I can
   model."

The page is `src/routes/simulacra-americana/+page.svelte` (the `say()`,
`traceOf()` and `startReveal()` functions give the robot's words and steps)
plus `src/lib/simulacra/WhatIf.svelte` (the bubble, More/Less and the
interviews).

## Current state

- **Key:** the Anthropic key is in `~/.config/simulacra/anthropic.env`;
  `llm.api_key()` reads it. Never print it or copy it anywhere.
- **Python:** `~/.venvs/simharness/bin/python` (anthropic 1.10).
- **Configs:**
  - `configs/quick-1920.json`: 2 agents, all arms, about 3¢, about 10 s.
  - `configs/rung1-1920.json`: 6 cohorts × 2, league only, about 7¢.
  - Knobs in `agents`: `arms`, `only_cohorts`, `max_requests`,
    `max_dollars`, `max_tokens`.
- **Model:** runs use `claude-haiku-4-5` (no `effort`; the backend strips it).
- **Run ids** hash the config, the data and all of `simharness/*.py` (G1).
  So any code change means a new run folder and a fresh `ask`.
- **Latest run:** `runs/1920-35ff30a7c5`, prompt p3, with `interviews` in the
  bundle. Superseded by the live bundle (`serve/bundles/RUN_ID`), prompt p4.
- **Dev router:** `serve/dev-server.cjs` on :8787 serves one run's
  `published/`. Restart it after every publish:

  ```sh
  pkill -f "node dev-server.cjs"; cd serve && SIMULACRA_BUNDLES="$PWD/../runs/<id>/published" \
    NODE_PATH=~/Documents/fromDesktop/auth-server/partyhat-authorization-server/node_modules \
    nohup node dev-server.cjs > /tmp/simdev.log 2>&1 &
  ```

- **Page:** <http://localhost:5185/simulacra-americana?simapi=http://localhost:8787&year=1920>.
  The web dev server is `~/Documents/fromDesktop/creator-rows-dev-kit/start-web.sh`,
  logging to `logs/web.log`.
- **Git:** nothing from these sessions is committed. Don't commit or push.
  That's Cameron's call.

## Update (evidence session): what now exists

Step 1 is done, and the loop's fixes are largely automated:
- **Logging.** `serve/simulacra.ts` logs every `POST /runs` in dev
  (`sessions/requests.jsonl`) and queues unknown text
  (`sessions/queue.jsonl`). `scripts/harness/sessions-report.py` reads both.
- **`run whatif`.** `--text "…"` or `--queue` compiles any text into one of
  five kinds, including the new *candidate* kind (a third ballot line, p4).
  It then researches historical evidence with web search, interviews only the
  new arm (identical requests are reused), and publishes to
  `serve/bundles/1920.json`. A request that means an existing what-if just
  gains keywords.
- **Confidence.** Every what-if carries a tier from high to "Extremely low",
  with reasons, and the evidence's agreement with the interviews.
- **Config.** `configs/live-1920.json` accumulates what-ifs. Read
  README.md "Typed what-ifs" and DISCLOSURES D14–D20, E5–E6, G4–G6 and H1–H4
  first.

So each iteration is now:
1. Run `sessions-report.py`.
2. Run `run whatif --queue --limit 1`.
3. Read its five interviews and its evidence.
4. Fix what reads wrong: the compiler (`scenario.COMPILE_SYSTEM`), the
   research prompt, the source tiers, or the confidence rules.
5. Log it.

Serve the live bundle:

```sh
cd serve && SIMULACRA_BUNDLES="$PWD/bundles" NODE_PATH=~/Documents/fromDesktop/auth-server/partyhat-authorization-server/node_modules \
  nohup node dev-server.cjs > /tmp/simdev.log 2>&1 &
```

## Step 1: log the sessions (done; kept for reference)

In `serve/simulacra.ts`, `POST /runs`: append one JSON line per request to
`harness/sessions/requests.jsonl`, in dev only (when `SIMULACRA_LOG` is set;
the dev server sets it). Each line holds:

- `ts`, `year`, `text`, `whatIfs`;
- `matched` (the keys `readText` found) and `unknown`;
- `combo`, and whether that combination existed.

No IPs and no user ids. Add `harness/sessions/` to `.gitignore`.

Then write `scripts/harness/sessions-report.py`. It prints, since a given time:

- the count of requests;
- the share that were `unknown`;
- the unknowns clustered roughly by kind: a new candidate or entrant, a
  franchise change, an event or scandal, a policy, a demographic shift, or
  another year's issue;
- the top 10 raw texts.

This is how you'll pick what to build next.

## Step 2: the loop

Each iteration takes at most about 30 minutes and has one change:

1. **Read.** Run `sessions-report.py`. Pick the biggest cluster of unknowns,
   or the worst-looking modelled answer.
2. **Choose the smallest fix**, cheapest first:
   - *A keyword.* The words were modellable but unmatched ("League of
     Nations passes", "Wilson's treaty"). Add the words in `run.py`
     `_bundle` → `words`. No new interviews; republish only.
   - *A new what-if of an existing kind:* franchise, population or issue.
     Add an entry to `REGISTRY` in `whatifs.py` with its `facts`, its
     `drop_topics` and its keywords. Then plan and ask at rung 1 (about 7¢).
   - *A new kind of what-if*, such as a new candidate entering (the first
     request that exposed this was "charlie chaplin ran as an independent").
     This means:
     - a third ballot line in `agentlayer.parties()` / `prompts.ballot_block`;
     - a paired arm with that line added;
     - `paired.normalize` counting the third choice;
     - `publish` applying its effect to the O (other) share through
       `apply_effects`.

     Build the general case, "a named person runs as an independent with
     these positions", with the positions written in a neutral, dated
     paraphrase. Keep the other candidates' labels blinded as today.
     Bump `PROMPT_VERSION`, because the ballot changed.
   - *A prompt or instrument change*, for example when quotes are too long
     (D13), or an answer reads like a summary rather than a person. Change
     `prompts.py` and bump `PROMPT_VERSION`. Never mix prompt versions in
     one analysis.
3. **Run.** Use `plan` (read the estimate), then `ask`, `analyze`, `publish`.
   Restart the dev router.
4. **Check in the page.**
   - Type the original request. It should now run.
   - Watch the bubble's steps and open More to read the interviews.
   - Read five answers yourself: are they people, not summaries? Is any
     letter label in a quote (D11)?
5. **Report to Cameron in a few lines:**
   - what people asked;
   - what you changed;
   - what it cost;
   - what the rerun now says;
   - anything logged in `DISCLOSURES.md`.

Then go to the next iteration.

To wait between iterations, use a long self-paced loop (20–30 minutes) or
wait for Cameron. Don't poll faster than people use the page.

## Guardrails

- **Money: the one hard stop.**
  - Every `ask` prints its estimate first.
  - Keep `max_dollars` at or below 0.50 per run, and stay under $2 a day in
    total, unless Cameron says otherwise.
  - Stop and say why if a run's actual cost exceeds its estimate by more
    than 50%.
- **Honesty.**
  - Every what-if you add is a modelling assumption. Write its
    `assumption` string plainly; the page shows it.
  - Log every surprise, bug or post-hoc change in `DISCLOSURES.md`.
  - New what-ifs are exploratory. Say so in their disclosure entry.
- **Content.** Invented candidates, celebrities and so on are fine as
  hypotheticals, but the brief must present them neutrally and in period.
  Never put words in a real person's mouth as if they were real quotes.
  Voters' quotes are about the candidate, not by them.
- **Scope.** The harness, `serve/` and new files under `harness/` are
  yours. For `+page.svelte`, `WhatIf.svelte`, `MiniMap.svelte`,
  `Places.svelte` and `places.js`:
  - run `ListAgents`;
  - if a UI session is live, message it before editing;
  - otherwise go ahead, and describe the change in your report.
- **Production.** No deploys to the auth server, and no changes to
  production config, without Cameron's explicit yes. `?simapi=` works in
  dev only, by design.
