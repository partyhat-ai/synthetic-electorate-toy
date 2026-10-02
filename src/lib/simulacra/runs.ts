// A rerun from start to finish: ask the server to start it, poll it until
// it's done, failed or stopped, and hand the page the result. Plain
// TypeScript: the page keeps the run on show in its own state and passes in
// how to read and write it, so the loop can be driven by a fake API and a
// fake clock in tests.
import type { RunAsk, SimulacraApi } from './api';
import type { RunResult, RunStatus, Step, WhatIf } from './schemas';

/** The run on show while it works. `id` is null until the server has started it. */
export interface ActiveRun {
  /** This start, among all of the page's starts. */
  readonly token: number;
  readonly id: string | null;
  readonly year: number;
  /** States counted so far, of `total`. */
  readonly done: number;
  readonly total: number;
  /** The typed words, trimmed. */
  readonly text: string;
  /** The chosen what-ifs' labels. */
  readonly labels: readonly string[];
  /** New words being modelled on the server: its working so far. */
  readonly steps: readonly Step[] | null;
}

/** Poll this often, ms; less often while the server models new words (about a minute). */
export const POLL_MS = 300;
export const POLL_MODELLING_MS = 1000;
/** Stop waiting on a run after this long, ms (= the server's own limit on modelling new words). */
export const GIVE_UP_MS = 10 * 60 * 1000;
export const GAVE_UP = 'I stopped waiting after 10 minutes: the server never finished this rerun. Try again.';

export type PollEnd =
  | { readonly kind: 'done'; readonly result: RunResult }
  | { readonly kind: 'failed'; readonly message: string }
  | { readonly kind: 'gave-up'; readonly message: string }
  /** The page stopped or replaced the run. */
  | { readonly kind: 'dropped' };

export interface PollOptions {
  readonly sleep: (ms: number) => Promise<void>;
  readonly now: () => number;
  /** When the run was started, on `now`'s clock. */
  readonly startedAt: number;
  /** Whether the page still wants this run. */
  readonly current: () => boolean;
  /** Each `running` answer. */
  readonly onProgress?: (status: Extract<RunStatus, { status: 'running' }>) => void;
}

/**
 * Polls run `id` until it ends. An indeterminate answer keeps polling, and
 * so does a rate-limited one (less often); any other error ends it; past
 * GIVE_UP_MS it gives up, with the reason.
 */
export async function pollRun(api: Pick<SimulacraApi, 'run'>, id: string, o: PollOptions): Promise<PollEnd> {
  let wait = POLL_MS;
  for (;;) {
    await o.sleep(wait);
    if (!o.current()) return { kind: 'dropped' };
    if (o.now() - o.startedAt >= GIVE_UP_MS) return { kind: 'gave-up', message: GAVE_UP };
    const out = await api.run(id);
    if (!o.current()) return { kind: 'dropped' };
    switch (out.kind) {
      case 'ok': {
        const r = out.value;
        switch (r.status) {
          case 'running':
            o.onProgress?.(r);
            wait = r.steps ? POLL_MODELLING_MS : POLL_MS;
            break;
          case 'done':
            return { kind: 'done', result: r.result };
          case 'failed':
            return { kind: 'failed', message: r.error || 'The rerun failed.' };
          default:
            r satisfies never;
        }
        break;
      }
      case 'indeterminate':
        wait = POLL_MS;
        break;
      case 'error':
        // Too many requests: the run goes on on the server; ask less often.
        if (out.reason === 'limited') {
          wait = POLL_MODELLING_MS;
          break;
        }
        return { kind: 'failed', message: out.message || 'Lost track of the rerun.' };
      case 'unsupported':
        return { kind: 'failed', message: out.message || 'Lost track of the rerun.' };
      default:
        out satisfies never;
    }
  }
}

/** A rerun that finished, for the page to keep. */
export interface Finished {
  readonly year: number;
  readonly id: string;
  readonly result: RunResult;
  /** The what-ifs chosen when it started. */
  readonly keys: readonly string[];
  readonly text: string;
  /** What it applied that the year now lists (a what-if built from typed words included). */
  readonly applied: readonly string[];
}

export interface RunnerDeps {
  readonly api: SimulacraApi;
  readonly sleep?: (ms: number) => Promise<void>;
  readonly now?: () => number;
  getRun(): ActiveRun | null;
  setRun(run: ActiveRun | null): void;
  /** Reloads a year's groups and what-ifs from the server. */
  reloadSim(year: number): Promise<void>;
  /** The what-ifs a year lists now. */
  whatIfsOf(year: number): readonly WhatIf[];
  finished(f: Finished): void;
  failed(message: string): void;
}

export interface StartRequest {
  readonly year: number;
  readonly keys: readonly string[];
  readonly text: string;
  readonly edits: NonNullable<RunAsk['edits']>;
  readonly total: number;
  readonly labels: readonly string[];
}

export interface Runner {
  /** Stops any run on show and starts this one. Resolves when it has ended. */
  start(req: StartRequest): Promise<void>;
  /** Stops the run on show, telling the server. */
  stop(): void;
}

const wait = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

export function createRunner(deps: RunnerDeps): Runner {
  const sleep = deps.sleep ?? wait;
  const now = deps.now ?? Date.now;
  let tokens = 0;

  function stop(): void {
    const r = deps.getRun();
    deps.setRun(null);
    if (r?.id) void deps.api.stopRun(r.id);
  }

  async function start(req: StartRequest): Promise<void> {
    if (deps.getRun()) stop();
    tokens += 1;
    const token = tokens;
    const { year, keys, text, edits } = req;
    deps.setRun({ token, id: null, year, done: 0, total: req.total, text, labels: req.labels, steps: null });
    const startedAt = now();
    const started = await deps.api.startRun(year, { whatIfs: [...keys], text, edits });
    const mine = deps.getRun();
    if (!mine || mine.token !== token) return;
    if (started.kind !== 'ok') {
      // Indeterminate: the run may have started, but with no id there's
      // nothing to poll; it isn't resubmitted.
      deps.setRun(null);
      deps.failed(started.message || 'The rerun didn’t start.');
      return;
    }
    const id = started.value.id;
    deps.setRun({ ...mine, id });
    const current = () => deps.getRun()?.id === id;
    const end = await pollRun(deps.api, id, {
      sleep,
      now,
      startedAt,
      current,
      onProgress: (r) => {
        const run = deps.getRun();
        if (run) deps.setRun({ ...run, done: r.done, total: r.total, steps: r.steps ?? null });
      },
    });
    switch (end.kind) {
      case 'dropped':
        return;
      case 'gave-up':
        stop();
        deps.failed(end.message);
        return;
      case 'failed':
        deps.setRun(null);
        deps.failed(end.message);
        return;
      case 'done':
        break;
      default:
        end satisfies never;
    }
    const result = end.result;
    // A what-if the server just built from typed words: reload the year's
    // what-ifs so its chip appears, already chosen.
    const listed = (ws: readonly WhatIf[], k: string) => ws.some((w) => w.key === k);
    let known = deps.whatIfsOf(year);
    if (result.applied.some((a) => !listed(known, a.key))) {
      await deps.reloadSim(year);
      if (!current()) return;
      known = deps.whatIfsOf(year);
    }
    const applied = result.applied.map((a) => a.key).filter((k) => listed(known, k));
    deps.finished({ year, id, result, keys, text, applied });
  }

  return { start, stop };
}
