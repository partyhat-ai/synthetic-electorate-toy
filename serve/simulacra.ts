// /api/simulacra: serves precomputed harness bundles in the page's contract.
//
// Bundles are the harness's `published/<year>.json` files (serve/bundles/ by
// default; SIMULACRA_BUNDLES points elsewhere). Everything expensive
// (population draws, the backbone, LLM agents) runs offline. Online work is
// lookup plus arithmetic:
//   - every combination of a year's what-ifs is precomputed (with draws);
//   - typed text is matched to a what-if by keyword, or returned as `unknown`;
//   - hand edits (the page's dragged dots) are applied to the point run's
//     state × group table and re-tallied; an edited run carries no draws, and
//     says so in `howIGotThis`.
// Reading is open to everyone: the demo has to work without an account. Every
// client IP is rate limited (guard.ts).
//
// With SIMULACRA_LOG set (production sets it, and SIMULACRA_AUTORUN):
//   - every POST /runs appends one line to sessions/requests.jsonl
//     (ts, year, text, whatIfs, matched, unknown, combo, exists; no IPs, no ids);
//   - unmatched text from a request carrying an access key (SIMULACRA_ACCESS_KEYS)
//     is queued in sessions/queue.jsonl, with the key's name, for
//     `python -m simharness.run whatif --queue`, while spend is under the
//     caps (guard.ts: per key per day, and in all); without a key, or over a
//     cap, the run answers
//     at once with `unknownWhy` saying why the text wasn't modelled;
//   - a queued text holds its run `running` (with the worker's `steps`) when
//     SIMULACRA_AUTORUN=<config path> starts that worker in the background from
//     the repo root (one at a time); otherwise the result says `queued`;
//   - session logs drop lines older than SIMULACRA_RETAIN_DAYS (default 7), and
//     the spend ledger keeps old lines without their `note`, so visitors'
//     words aren't kept for good;
//   - a bundle file that changed on disk is reloaded, so a publish needs no restart.
import { type ChildProcess, spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { appendFileSync, createWriteStream, existsSync, mkdirSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { homedir } from 'node:os';
import path from 'node:path';
import express, { type ErrorRequestHandler, type RequestHandler, type Router } from 'express';
import type { z } from 'zod';
import {
  Bundle,
  type Edits,
  FIELDS,
  type Field,
  IntakeStatus,
  type PageKey,
  QueueDone,
  QueueFailed,
  type Result,
  RunRequest,
  type Slice,
  type Step,
  type TableRow,
  type Told
} from './bundle';
import { type Caps, capLog, capsFromEnv, checkCaps, type KeyRing, type Limit, parseKeyRing, pruneJsonl, RateLimiter } from './guard';

const ROOT = path.resolve(import.meta.dirname, '..');

export interface SimulacraOptions {
  /** Folder of `<year>.json` bundles. */
  bundles: string;
  /** Where dev logs, the queue and the worker's status live. */
  sessions: string;
  /** Dev logging and queueing (SIMULACRA_LOG). */
  devLog: boolean;
  /** Config path for the background intake worker (SIMULACRA_AUTORUN), relative to `root`. */
  autorun: string | null;
  /** Python with the harness installed (SIMULACRA_PYTHON). */
  python: string;
  /** The repo root: the worker runs `python -m simharness.run` from here. */
  root: string;
  /** Access keys that may queue new text (SIMULACRA_ACCESS_KEYS). */
  keys: KeyRing;
  /** Dollar caps on the intake (SIMULACRA_KEY_DAILY_USD, SIMULACRA_TOTAL_USD). */
  caps: Caps;
  /** Days session logs keep a line (SIMULACRA_RETAIN_DAYS). */
  retainDays: number;
  /** Per-IP rate limits. */
  limits: Limits;
}

export interface Limits {
  /** Every request to the router. */
  readonly any: Limit;
  /** POST /runs. */
  readonly runs: Limit;
  /** POST /runs whose text would be queued (with a key). */
  readonly intake: Limit;
}

const MINUTE = 60_000;
// The page polls a run every 300 ms (1 s while a new what-if is modelled).
export const DEFAULT_LIMITS: Limits = {
  any: { max: 1200, windowMs: 10 * MINUTE },
  runs: { max: 120, windowMs: 10 * MINUTE },
  intake: { max: 10, windowMs: 60 * MINUTE }
};

export function optionsFromEnv(env: NodeJS.ProcessEnv = process.env): SimulacraOptions {
  return {
    bundles: env.SIMULACRA_BUNDLES || path.join(ROOT, 'serve', 'bundles'),
    sessions: path.join(ROOT, 'sessions'),
    devLog: Boolean(env.SIMULACRA_LOG),
    autorun: env.SIMULACRA_AUTORUN || null,
    python: env.SIMULACRA_PYTHON || path.join(homedir(), '.venvs/simharness/bin/python'),
    root: ROOT,
    keys: parseKeyRing(env.SIMULACRA_ACCESS_KEYS),
    caps: capsFromEnv(env),
    retainDays: env.SIMULACRA_RETAIN_DAYS ? Number(env.SIMULACRA_RETAIN_DAYS) : 7,
    limits: DEFAULT_LIMITS
  };
}

/** The result the page receives: a bundle result plus the brief and interviews behind it. */
export type RunResult = Result & {
  told?: Record<string, Told>;
  reading?: Record<string, unknown>[];
  pre?: Record<string, unknown>;
  interview?: { questions: string[] | undefined; byWhatIf: { whatIf: string; answers: unknown[] }[] };
  queued?: { text: string; worker: boolean };
  unknownWhy?: string;
};

interface Pending {
  text: string;
  keys: string[];
  edits: Edits;
  /** The access key's name that queued the text. */
  who: string;
}

type RunEntry =
  | { state: 'done'; year: number; created: number; key: string; result: RunResult }
  | { state: 'pending'; year: number; created: number; pending: Pending };

type Settled =
  | { status: 'running'; steps: Step[] }
  | { status: 'failed'; error: string }
  | { status: 'done'; key: string; result: RunResult };

type Totals = Record<PageKey, number>;

const RUN_TTL_MS = 60 * 60 * 1000;
const PENDING_MS = 10 * 60 * 1000;
/** Runs held at once; past it the oldest go first. */
const MAX_RUNS = 10_000;
/** Queued texts one key may have waiting at once. */
const MAX_PENDING_PER_KEY = 3;
/** The worker's plain-text log is emptied past this (CloudWatch keeps a copy). */
const MAX_WORKER_LOG_BYTES = 20 * 1024 * 1024;
const SESSION_LOGS = ['requests.jsonl', 'queue.jsonl', 'queue-done.jsonl', 'queue-failed.jsonl'];
/** The spend ledger outlives the retention, without the visitor's words in `note`. */
const LEDGER_SCRUB = ['note'];
/** Years a bundle can exist for; any other year is answered without touching the cache. */
const FIRST_YEAR = 1789;
const LAST_YEAR = 2100;

export const NEEDS_KEY = 'Modelling a new what-if needs an access key.';
export const OVER_KEY_CAP = 'You’ve used today’s budget for new what-ifs. Try again tomorrow.';
export const OVER_TOTAL_CAP = 'The budget for new what-ifs is spent.';
export const TOO_MANY_WAITING = 'You have three new what-ifs waiting already. Try again when one finishes.';
const KEYS: readonly PageKey[] = ['A', 'B', 'O'];

export const comboKey = (keys: readonly string[]): string => [...new Set(keys)].sort().join('+');

const escapeRegExp = (s: string): string => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** Whole words only: compiled what-ifs bring short keywords ("flu" must not match "influence"). */
export function readText(b: Bundle, text: string): { keys: string[]; unknown: string | null } {
  if (!text.trim()) return { keys: [], unknown: null };
  const lower = text.toLowerCase();
  const has = (w: string): boolean => new RegExp(`(^|[^a-z0-9])${escapeRegExp(w)}($|[^a-z0-9])`).test(lower);
  const keys = b.words.filter(({ words }) => words.some(has)).map(({ key }) => key);
  return keys.length ? { keys, unknown: null } : { keys: [], unknown: text };
}

function edited(row: Record<Field, number>, e: Edits[string] | undefined): Record<Field, number> {
  const f = Object.fromEntries(FIELDS.map((k) => [k, Math.max(0, row[k] + (e?.[k] ?? 0))]));
  // SAFETY: built from FIELDS, so every Field key is present.
  return f as Record<Field, number>;
}

const total = (f: Record<Field, number>): number => FIELDS.reduce((s, k) => s + f[k], 0) || 1;

/** Apply hand edits to the point run's state × group table, then re-tally states and EV. */
export function applyEdits(b: Bundle, result: Result, table: readonly TableRow[], edits: Edits): RunResult {
  const byState = new Map<string, Totals>();
  for (const row of table) {
    const f = edited(row, edits[row.slice]);
    const sum = total(f);
    const st = byState.get(row.state) ?? { A: 0, B: 0, O: 0 };
    for (const k of KEYS) st[k] += (row.adults * f[k]) / sum;
    byState.set(row.state, st);
  }
  const ev: Totals = { A: 0, B: 0, O: 0 };
  const states = result.states.map((s) => {
    const v = byState.get(s.code) ?? { A: 0, B: 0, O: 0 };
    const [first = 'A', second = 'B'] = [...KEYS].sort((x, y) => v[y] - v[x]);
    const votes = v.A + v.B + v.O || 1;
    ev[first] += b.ev[s.code] ?? 0;
    return {
      code: s.code,
      won: first,
      flipped: first !== b.historyWinner[s.code],
      margin: Math.round(((v[first] - v[second]) / votes) * 1000) / 10
    };
  });
  const need = Object.values(b.ev).reduce((s, x) => s + x, 0) / 2;
  const winner = KEYS.find((k) => ev[k] > need) ?? null;
  const slices = result.slices.map((s): Slice => {
    const e = edits[s.key];
    if (!e) return s;
    const f = edited(s, e);
    const sum = total(f);
    return { ...s, ...Object.fromEntries(FIELDS.map((k) => [k, f[k] / sum])) };
  });
  const { range: _range, drawsWon: _drawsWon, ...rest } = result;
  return {
    ...rest,
    ev,
    winner,
    states,
    slices,
    howIGotThis: [...(result.howIGotThis ?? []), 'You moved some groups by hand, so this is one run with no range.']
  };
}

/** One computed result for a year's what-if keys, or null when the combination wasn't precomputed. */
export function compute(
  b: Bundle,
  keys: readonly string[],
  edits: Edits,
  unknown: string | null
): { key: string; result: RunResult } | null {
  const key = comboKey(keys);
  const base = b.runs[key];
  if (!base) return null;
  const result = Object.keys(edits).length ? applyEdits(b, base, b.tables[key] ?? [], edits) : base;
  // Additive: the interviews behind each applied what-if, when the bundle has them.
  const byWhatIf = b.interviews.byWhatIf ?? {};
  const interviews = keys.flatMap((k) => {
    const answers = byWhatIf[k];
    return answers ? [{ whatIf: k, answers }] : [];
  });
  // What the voters were told for each applied what-if, and the dated newspaper items in their briefs.
  const told = Object.fromEntries(keys.flatMap((k) => (b.told?.[k] ? [[k, b.told[k]]] : [])));
  return {
    key,
    result: {
      ...result,
      unknown,
      ...(Object.keys(told).length ? { told } : {}),
      ...(b.reading?.length ? { reading: b.reading } : {}),
      ...(b.pre ? { pre: b.pre } : {}),
      ...(interviews.length ? { interview: { questions: b.interviews.questions, byWhatIf: interviews } } : {})
    }
  };
}

const norm = (t: string): string => t.toLowerCase().split(/\s+/).filter(Boolean).join(' ');

function readJsonl<T>(file: string, schema: z.ZodType<T>): T[] {
  let text: string;
  try {
    text = readFileSync(file, 'utf8');
  } catch {
    return [];
  }
  return text
    .split('\n')
    .filter(Boolean)
    .flatMap((line) => {
      try {
        const parsed = schema.safeParse(JSON.parse(line));
        return parsed.success ? [parsed.data] : [];
      } catch {
        return [];
      }
    });
}

/** A year's answer at a URL that names its run never changes. */
export const IMMUTABLE = 'public, max-age=31536000, s-maxage=31536000, immutable';
/** Unversioned answers and the manifest: a minute fresh, then revalidated. */
export const SHORT_CACHE = 'public, max-age=60, s-maxage=60, stale-while-revalidate=300';

export function createSimulacraRouter(opts: SimulacraOptions = optionsFromEnv()): Router {
  const bundles = new Map<number, { bundle: Bundle | null; mtime: number }>();
  const runs = new Map<string, RunEntry>();
  let worker: ChildProcess | null = null;
  let queuedWhileBusy = false;

  const mtimeOf = (file: string): number => (existsSync(file) ? statSync(file).mtimeMs : 0);

  function loadBundle(year: number): Bundle | null {
    if (!Number.isInteger(year) || year < FIRST_YEAR || year > LAST_YEAR) return null;
    const file = path.join(opts.bundles, `${year}.json`);
    const cached = bundles.get(year);
    if (cached && (!opts.devLog || cached.mtime === mtimeOf(file))) return cached.bundle;
    let bundle: Bundle | null = null;
    if (existsSync(file)) {
      const parsed = Bundle.safeParse(JSON.parse(readFileSync(file, 'utf8')));
      if (parsed.success) bundle = parsed.data;
      else console.warn(`simulacra: ${file} doesn't fit the bundle contract`, parsed.error.issues.slice(0, 3));
    }
    bundles.set(year, { bundle, mtime: mtimeOf(file) });
    return bundle;
  }

  function appendLine(name: string, row: unknown): void {
    try {
      mkdirSync(opts.sessions, { recursive: true });
      appendFileSync(path.join(opts.sessions, name), `${JSON.stringify(row)}\n`);
    } catch (e) {
      console.warn('simulacra: session log failed', e instanceof Error ? e.message : e);
    }
  }

  function startWorker(): void {
    if (!opts.autorun) return;
    if (worker) {
      queuedWhileBusy = true;
      return;
    }
    queuedWhileBusy = false;
    mkdirSync(opts.sessions, { recursive: true });
    const child = spawn(opts.python, ['-m', 'simharness.run', 'whatif', '--queue', '--limit', '5', '--config', opts.autorun], {
      cwd: opts.root,
      stdio: ['ignore', 'pipe', 'pipe']
    });
    const out = createWriteStream(path.join(opts.sessions, 'intake.log'), { flags: 'a' });
    child.stdout?.pipe(out);
    child.stderr?.pipe(out);
    child.on('error', (e) => out.write(`simulacra: worker failed to start: ${e.message}\n`));
    // Text typed while a worker ran is picked up by a fresh one (a worker that
    // stopped on a cap leaves its text queued and isn't restarted by itself).
    child.on('exit', () => {
      worker = null;
      if (queuedWhileBusy) startWorker();
    });
    worker = child;
  }

  // Runs are added in creation order (an entry replaced in place keeps its
  // slot), so the oldest are at the front: pruning stops at the first live one.
  function newRun(entry: RunEntry): string {
    const id = randomUUID();
    runs.set(id, entry);
    for (const [k, r] of runs) {
      if (Date.now() - r.created <= RUN_TTL_MS && runs.size <= MAX_RUNS) break;
      runs.delete(k);
    }
    return id;
  }

  const pendingFor = (who: string): number => {
    let n = 0;
    for (const r of runs.values()) if (r.state === 'pending' && r.pending.who === who) n += 1;
    return n;
  };

  // Session logs keep SIMULACRA_RETAIN_DAYS of lines. The worker appends to
  // them, so they're rewritten only while no worker runs.
  function prune(): void {
    if (!opts.devLog || worker) return;
    const maxAge = opts.retainDays * 24 * 60 * MINUTE;
    for (const name of [...SESSION_LOGS, 'spend.jsonl']) {
      try {
        const scrub = name === 'spend.jsonl' ? LEDGER_SCRUB : undefined;
        const n = pruneJsonl(path.join(opts.sessions, name), maxAge, Date.now(), scrub);
        if (n) console.log(`simulacra: ${scrub ? 'scrubbed' : 'dropped'} ${n} lines older than ${opts.retainDays} days in ${name}`);
      } catch (e) {
        console.warn(`simulacra: pruning ${name} failed`, e instanceof Error ? e.message : e);
      }
    }
    capLog(path.join(opts.sessions, 'intake.log'), MAX_WORKER_LOG_BYTES);
  }
  prune();
  setInterval(prune, 60 * MINUTE).unref();

  const limiters = {
    any: new RateLimiter(opts.limits.any),
    runs: new RateLimiter(opts.limits.runs),
    intake: new RateLimiter(opts.limits.intake)
  };
  const limited = (res: express.Response, retryAfterS: number): void => {
    res.set('Retry-After', String(retryAfterS)).status(429).json({ error: 'Too many requests just now. Try again in a few minutes.' });
  };
  const rateLimit =
    (which: keyof typeof limiters): RequestHandler =>
    (req, res, next) => {
      const a = limiters[which].admit(req.ip ?? 'unknown');
      if (a.ok) next();
      else limited(res, a.retryAfterS);
    };

  // Where the worker is with a pending run's text.
  function settle(r: Extract<RunEntry, { state: 'pending' }>): Settled {
    const t = norm(r.pending.text);
    const sameYear = (x: { year?: number | null }): boolean => (x.year ?? 1920) === r.year;
    const outcome = readJsonl(path.join(opts.sessions, 'queue-done.jsonl'), QueueDone)
      .filter((x) => x.text === t && sameYear(x))
      .pop();
    const failed = readJsonl(path.join(opts.sessions, 'queue-failed.jsonl'), QueueFailed)
      .filter((x) => x.text === t && sameYear(x) && x.at * 1000 >= r.created)
      .pop();
    const b = loadBundle(r.year);
    if (outcome && (outcome.status === 'modelled' || outcome.status === 'keyword') && outcome.key && b) {
      const done =
        compute(b, [...new Set([...r.pending.keys, outcome.key])], r.pending.edits, null) ??
        compute(b, [outcome.key], r.pending.edits, null);
      if (done) return { status: 'done', key: done.key, result: done.result };
      return { status: 'failed', error: 'The new what-if was modelled, but not in this combination. Try it on its own.' };
    }
    const stopped = outcome ?? failed;
    if (stopped) {
      // Not modellable, or the worker stopped: the run finishes unchanged, saying why.
      const done = b ? compute(b, r.pending.keys, r.pending.edits, r.pending.text) : null;
      const why = stopped.why ?? '';
      if (!done) return { status: 'failed', error: why || 'Couldn’t model that.' };
      return { status: 'done', key: done.key, result: { ...done.result, unknownWhy: why } };
    }
    if (Date.now() - r.created > PENDING_MS) return { status: 'failed', error: 'Modelling that took too long. Try again in a minute.' };
    if (!worker) startWorker();
    let steps: Step[] = [{ text: 'Waiting for the what-ifs typed before this one.', state: 'doing' }];
    try {
      const st = IntakeStatus.safeParse(JSON.parse(readFileSync(path.join(opts.sessions, 'intake-status.json'), 'utf8')));
      if (st.success && st.data.text === t) steps = st.data.steps;
    } catch {
      // not started
    }
    return { status: 'running', steps: [{ text: `Reading “${r.pending.text}”: it’s new to me.`, state: 'done' }, ...steps] };
  }

  const router = express.Router();
  router.use(rateLimit('any'));
  router.use(express.json({ limit: '64kb' }));

  // Every published year and the run its bundle came from. The page reads it
  // first and asks for each year at /elections/<year>?v=<runId>, so a year's
  // answer can be cached for good: a new run means a new URL.
  router.get('/manifest', (_req, res) => {
    const years: Record<string, string> = {};
    const files = existsSync(opts.bundles) ? readdirSync(opts.bundles) : [];
    for (const f of files.filter((name) => /^\d{4}\.json$/.test(name)).sort()) {
      const b = loadBundle(Number(f.slice(0, 4)));
      if (b) years[f.slice(0, 4)] = b.runId;
    }
    res.set('Cache-Control', SHORT_CACHE).json({ years });
  });

  // A year without a bundle answers 200 with `simulated: false`, not 404: the
  // page reads a 404 before any answer as "there is no simulation service".
  router.get('/elections/:year', (req, res) => {
    const b = loadBundle(Number(req.params.year));
    if (!b) {
      res.set('Cache-Control', SHORT_CACHE).json({ slices: [], whatIfs: [], simulated: false });
      return;
    }
    // Immutable only when the URL names the run being served.
    res.set('Cache-Control', req.query.v === b.runId ? IMMUTABLE : SHORT_CACHE);
    res.json({ ...b.election, simulated: true, runId: b.runId });
  });

  router.post('/runs', rateLimit('runs'), (req, res) => {
    const body = RunRequest.safeParse(req.body ?? {});
    if (!body.success) {
      res.status(400).json({ error: 'bad request', issues: body.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`) });
      return;
    }
    const { year, whatIfs, text, edits } = body.data;
    const b = loadBundle(year);
    if (!b) {
      res.status(404).json({ error: 'no simulation for this year' });
      return;
    }
    const known = new Set(b.election.whatIfs.map((w) => w.key));
    const chosen = whatIfs.filter((k) => known.has(k));
    const read = readText(b, text);
    const keys = [...chosen, ...read.keys];
    const done = compute(b, keys, edits, read.unknown);
    let queued: string | null = null;
    // Why unknown words weren't queued, when they weren't.
    let unknownWhy: string | null = null;
    if (opts.devLog) {
      const ts = new Date().toISOString();
      appendLine('requests.jsonl', { ts, year, text, whatIfs, matched: read.keys, unknown: read.unknown, combo: comboKey(keys), exists: Boolean(done) });
      if (read.unknown) {
        const who = opts.keys.identify(req.get('authorization'));
        const cap = who ? checkCaps(path.join(opts.sessions, 'spend.jsonl'), who, opts.caps) : null;
        if (!who) unknownWhy = NEEDS_KEY;
        else if (cap?.kind === 'over') unknownWhy = cap.which === 'total' ? OVER_TOTAL_CAP : OVER_KEY_CAP;
        else if (pendingFor(who) >= MAX_PENDING_PER_KEY) unknownWhy = TOO_MANY_WAITING;
        else {
          const a = limiters.intake.admit(req.ip ?? 'unknown');
          if (!a.ok) {
            limited(res, a.retryAfterS);
            return;
          }
          appendLine('queue.jsonl', { ts, year, text: read.unknown, who });
          queued = who;
          startWorker();
        }
      }
    }
    // With the worker on, new words hold the run open (GET reports the
    // worker's steps) until they are compiled, researched, interviewed and
    // published; then the run finishes with the new what-if applied.
    if (queued && read.unknown && opts.autorun) {
      const pending = { text: read.unknown, keys: chosen, edits, who: queued };
      res.json({ id: newRun({ state: 'pending', year, created: Date.now(), pending }) });
      return;
    }
    if (!done) {
      res.status(422).json({ error: 'That combination has not been computed.' });
      return;
    }
    let result: RunResult = done.result;
    if (queued && read.unknown) result = { ...result, queued: { text: read.unknown, worker: Boolean(worker) } };
    else if (unknownWhy) result = { ...result, unknownWhy };
    res.json({ id: newRun({ state: 'done', year, created: Date.now(), key: done.key, result }) });
  });

  router.get('/runs/:id', (req, res) => {
    const r = runs.get(req.params.id);
    if (!r) {
      res.status(404).json({ error: 'no such run' });
      return;
    }
    let result: RunResult;
    if (r.state === 'pending') {
      const s = settle(r);
      if (s.status === 'running') {
        res.json({ status: 'running', done: 0, total: 0, error: null, steps: s.steps });
        return;
      }
      if (s.status === 'failed') {
        runs.delete(req.params.id);
        res.json({ status: 'failed', error: s.error });
        return;
      }
      runs.set(req.params.id, { state: 'done', year: r.year, created: r.created, key: s.key, result: s.result });
      result = s.result;
    } else {
      result = r.result;
    }
    const count = result.states.length;
    res.json({ status: 'done', done: count, total: count, error: null, result });
  });

  router.post('/runs/:id/cancel', (req, res) => {
    runs.delete(req.params.id);
    res.json({ ok: true });
  });

  router.get('/elections/:year/voters/:slice', (req, res) => {
    const b = loadBundle(Number(req.params.year));
    if (!b) {
      res.status(404).json({ error: 'no simulation for this year' });
      return;
    }
    const run = typeof req.query.run === 'string' ? runs.get(req.query.run) : undefined;
    const key = run?.state === 'done' ? run.key : '';
    const voter = b.voters[key]?.[req.params.slice] ?? b.voters['']?.[req.params.slice];
    if (!voter) {
      res.status(404).json({ error: 'no voter for this group' });
      return;
    }
    res.json(voter);
  });

  // A body that isn't JSON answers in JSON too.
  const onError: ErrorRequestHandler = (err: unknown, _req, res, next) => {
    if (res.headersSent) {
      next(err);
      return;
    }
    const status = err instanceof SyntaxError ? 400 : 500;
    res.status(status).json({ error: status === 400 ? 'bad request' : 'server error' });
  };
  router.use(onError);

  return router;
}
