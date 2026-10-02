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
// Signed-out requests are allowed: the demo has to work without an account.
//
// Dev only (SIMULACRA_LOG set; production never sets it):
//   - every POST /runs appends one line to sessions/requests.jsonl
//     (ts, year, text, whatIfs, matched, unknown, combo, exists; no IPs, no ids);
//   - unmatched text is queued in sessions/queue.jsonl for
//     `python -m simharness.run whatif --queue`, and the result says `queued`.
import { randomUUID } from 'node:crypto';
import { appendFileSync, existsSync, mkdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import express, { type ErrorRequestHandler, type Router } from 'express';
import { Bundle, type Edits, FIELDS, type Field, type PageKey, type Result, RunRequest, type Slice, type TableRow } from './bundle';

const ROOT = path.resolve(import.meta.dirname, '..');

export interface SimulacraOptions {
  /** Folder of `<year>.json` bundles. */
  bundles: string;
  /** Where dev logs and the queue live. */
  sessions: string;
  /** Dev logging and queueing (SIMULACRA_LOG). */
  devLog: boolean;
}

export function optionsFromEnv(env: NodeJS.ProcessEnv = process.env): SimulacraOptions {
  return {
    bundles: env.SIMULACRA_BUNDLES || path.join(ROOT, 'serve', 'bundles'),
    sessions: path.join(ROOT, 'sessions'),
    devLog: Boolean(env.SIMULACRA_LOG)
  };
}

/** The result the page receives: a bundle result plus the interviews behind it. */
export type RunResult = Result & {
  interview?: { questions: string[] | undefined; byWhatIf: { whatIf: string; answers: unknown[] }[] };
  queued?: { text: string };
};

interface RunEntry {
  year: number;
  created: number;
  key: string;
  result: RunResult;
}

type Totals = Record<PageKey, number>;

const RUN_TTL_MS = 60 * 60 * 1000;
const KEYS: readonly PageKey[] = ['A', 'B', 'O'];

export const comboKey = (keys: readonly string[]): string => [...new Set(keys)].sort().join('+');

/** Typed text → the what-ifs whose keywords it contains. */
export function readText(b: Bundle, text: string): { keys: string[]; unknown: string | null } {
  if (!text.trim()) return { keys: [], unknown: null };
  const lower = text.toLowerCase();
  const has = (w: string): boolean => lower.includes(w);
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
  return {
    key,
    result: {
      ...result,
      unknown,
      ...(interviews.length ? { interview: { questions: b.interviews.questions, byWhatIf: interviews } } : {})
    }
  };
}

export function createSimulacraRouter(opts: SimulacraOptions = optionsFromEnv()): Router {
  const bundles = new Map<number, Bundle | null>();
  const runs = new Map<string, RunEntry>();

  function loadBundle(year: number): Bundle | null {
    if (!Number.isInteger(year)) return null;
    const cached = bundles.get(year);
    if (cached !== undefined) return cached;
    const file = path.join(opts.bundles, `${year}.json`);
    let bundle: Bundle | null = null;
    if (existsSync(file)) {
      const parsed = Bundle.safeParse(JSON.parse(readFileSync(file, 'utf8')));
      if (parsed.success) bundle = parsed.data;
      else console.warn(`simulacra: ${file} doesn't fit the bundle contract`, parsed.error.issues.slice(0, 3));
    }
    bundles.set(year, bundle);
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

  function newRun(entry: RunEntry): string {
    const id = randomUUID();
    runs.set(id, entry);
    for (const [k, r] of runs) if (Date.now() - r.created > RUN_TTL_MS) runs.delete(k);
    return id;
  }

  const router = express.Router();
  router.use(express.json({ limit: '64kb' }));

  // A year without a bundle answers 200 with `simulated: false`, not 404: the
  // page reads a 404 before any answer as "there is no simulation service".
  router.get('/elections/:year', (req, res) => {
    const b = loadBundle(Number(req.params.year));
    if (!b) {
      res.json({ slices: [], whatIfs: [], simulated: false });
      return;
    }
    res.json({ ...b.election, simulated: true });
  });

  router.post('/runs', (req, res) => {
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
    let queued = false;
    if (opts.devLog) {
      const ts = new Date().toISOString();
      appendLine('requests.jsonl', { ts, year, text, whatIfs, matched: read.keys, unknown: read.unknown, combo: comboKey(keys), exists: Boolean(done) });
      if (read.unknown) {
        appendLine('queue.jsonl', { ts, year, text: read.unknown });
        queued = true;
      }
    }
    if (!done) {
      res.status(422).json({ error: 'That combination has not been computed.' });
      return;
    }
    const result: RunResult = queued && read.unknown ? { ...done.result, queued: { text: read.unknown } } : done.result;
    res.json({ id: newRun({ year, created: Date.now(), key: done.key, result }) });
  });

  router.get('/runs/:id', (req, res) => {
    const r = runs.get(req.params.id);
    if (!r) {
      res.status(404).json({ error: 'no such run' });
      return;
    }
    const count = r.result.states.length;
    res.json({ status: 'done', done: count, total: count, error: null, result: r.result });
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
    const key = run?.key ?? '';
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
