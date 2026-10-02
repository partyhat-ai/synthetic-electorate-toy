// Simulacra Americana's connection to the simulation server, under
// /api/simulacra (pnpm serve in development, proxied by Vite). The page
// shows each election as it happened (history.ts) with none of it; the
// groups of voters, the what-ifs and every rerun come from here, or from the
// labelled stand-in in sample.ts, which has the same shape.
//
// Every answer is parsed once here (schemas.ts). Every call returns an
// Outcome, never throws:
//   ok            the parsed value
//   error         the server answered no, was unreachable, or sent something unreadable
//   indeterminate a write timed out after it may have landed: poll, don't resubmit
//   unsupported   there is no simulation service (a 404 before any answer)
import type { z } from 'zod';
import {
  CancelledSchema,
  type ElectionResponse,
  ElectionResponseSchema,
  ManifestSchema,
  type RunStatus,
  RunStatusSchema,
  type StartedRun,
  StartedRunSchema,
  type Voter,
  VoterSchema,
} from './schemas';

export type * from './schemas';

/** Why a call failed. */
export type ErrorReason =
  /** No answer: the network, or a read that timed out. */
  | 'offline'
  /** 401 / 403. */
  | 'auth'
  /** A 404 after the service has answered before. */
  | 'missing'
  /** Any other non-2xx. */
  | 'failed'
  /** A 2xx whose body isn't the contract. */
  | 'malformed';

export type Outcome<T> =
  | { readonly kind: 'ok'; readonly value: T }
  | { readonly kind: 'error'; readonly reason: ErrorReason; readonly message: string; readonly status: number }
  | { readonly kind: 'indeterminate'; readonly message: string }
  | { readonly kind: 'unsupported'; readonly message: string };

/** Fractions of a group's adults moved by hand (the page's dragged dots); each change sums to 0. */
export type SliceEdit = Partial<Record<'A' | 'B' | 'O' | 'home' | 'barred', number>>;
export type Edits = Readonly<Record<string, SliceEdit>>;

export interface RunAsk {
  /** What-if keys, as the election lists them. */
  readonly whatIfs?: readonly string[];
  /** A what-if in the user's own words, for the server to read. */
  readonly text?: string;
  /** Groups changed by hand, applied after the what-ifs. */
  readonly edits?: Edits;
}

/** What the page needs from a simulation: the server (createSimulacraApi) or the sample (createSampleApi). */
export interface SimulacraApi {
  /** True for the made-up stand-in; the page labels it. */
  readonly sample: boolean;
  /**
   * A year's voters and what-ifs. `fresh` skips every cache (after a run that
   * may have published a new what-if for the year).
   */
  election(year: number, opts?: { readonly fresh?: boolean }): Promise<Outcome<ElectionResponse>>;
  startRun(year: number, ask?: RunAsk): Promise<Outcome<StartedRun>>;
  run(runId: string): Promise<Outcome<RunStatus>>;
  stopRun(runId: string): Promise<Outcome<null>>;
  voter(year: number, slice: string, runId?: string | null): Promise<Outcome<Voter>>;
}

export type Fetch = (input: string, init?: RequestInit) => Promise<Response>;

export interface ApiOptions {
  /** Defaults to the global fetch. */
  readonly fetch?: Fetch;
  /** Defaults to the same-origin /api/simulacra. */
  readonly base?: string;
  /** How long a call waits for an answer, ms. */
  readonly timeoutMs?: number;
}

export const DEFAULT_BASE = '/api/simulacra';
export const DEFAULT_TIMEOUT_MS = 20_000;

const failed = (reason: ErrorReason, message: string, status = 0): Outcome<never> => ({
  kind: 'error',
  reason,
  message,
  status,
});

function statusError(status: number): Outcome<never> {
  if (status === 401 || status === 403) return failed('auth', 'Sign in to rerun elections.', status);
  return failed('failed', `The simulation server answered ${status}.`, status);
}

export function createSimulacraApi(options: ApiOptions = {}): SimulacraApi {
  const doFetch: Fetch = options.fetch ?? ((input, init) => globalThis.fetch(input, init));
  const root = options.base ?? DEFAULT_BASE;
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  // A 404 before the service has ever answered means there's no service.
  let answered = false;
  // year → the run its bundle came from (GET /manifest): each year is asked
  // for at /elections/<year>?v=<runId>, a URL the CDN may keep for good.
  let manifest: Promise<Map<number, string>> | null = null;

  async function readManifest(): Promise<Map<number, string>> {
    const abort = new AbortController();
    const timer = setTimeout(() => abort.abort(), timeoutMs);
    try {
      const res = await doFetch(`${root}/manifest`, { signal: abort.signal });
      if (!res.ok) return new Map();
      const parsed = ManifestSchema.safeParse(await res.json());
      if (!parsed.success) return new Map();
      return new Map(Object.entries(parsed.data.years).map(([y, run]) => [Number(y), run]));
    } catch {
      // No manifest (an older server, or offline): years load unversioned.
      return new Map();
    } finally {
      clearTimeout(timer);
    }
  }

  async function call<S extends z.ZodType>(path: string, schema: S, body?: unknown): Promise<Outcome<z.output<S>>> {
    const write = body !== undefined;
    const abort = new AbortController();
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      abort.abort();
    }, timeoutMs);
    const init: RequestInit = write
      ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: abort.signal }
      : { signal: abort.signal };
    let res: Response;
    let json: unknown;
    try {
      res = await doFetch(root + path, init);
      if (res.status === 404 && !answered) {
        return { kind: 'unsupported', message: 'This server has no simulation service yet.' };
      }
      if (res.status === 404) return failed('missing', 'Not found.', 404);
      if (!res.ok) return statusError(res.status);
      answered = true;
      try {
        json = await res.json();
      } catch {
        if (timedOut && write) return { kind: 'indeterminate', message: 'The simulation server stopped answering mid-reply.' };
        if (timedOut) return failed('offline', 'The simulation server stopped answering.', res.status);
        return failed('malformed', 'The simulation server sent an unreadable answer.', res.status);
      }
    } catch {
      // The write may have reached the server before the wait ran out.
      if (timedOut && write) return { kind: 'indeterminate', message: 'The simulation server didn’t answer in time.' };
      return failed('offline', 'Can’t reach the simulation server.');
    } finally {
      clearTimeout(timer);
    }
    const parsed = schema.safeParse(json);
    if (!parsed.success) return failed('malformed', 'The simulation server sent an answer this page can’t read.', res.status);
    return { kind: 'ok', value: parsed.data };
  }

  const id = encodeURIComponent;
  return {
    sample: false,
    election: async (year, opts = {}) => {
      manifest ??= readManifest();
      const versions = await manifest;
      const known = versions.get(year);
      let v = '';
      if (opts.fresh) v = `?v=fresh-${Date.now().toString(36)}`;
      else if (known) v = `?v=${id(known)}`;
      const out = await call(`/elections/${year}${v}`, ElectionResponseSchema);
      if (out.kind === 'ok' && out.value.runId) versions.set(year, out.value.runId);
      return out;
    },
    startRun: (year, { whatIfs = [], text = '', edits = {} } = {}) =>
      call('/runs', StartedRunSchema, { year, whatIfs, text, edits }),
    run: (runId) => call(`/runs/${id(runId)}`, RunStatusSchema),
    stopRun: async (runId) => {
      const out = await call(`/runs/${id(runId)}/cancel`, CancelledSchema, {});
      return out.kind === 'ok' ? { kind: 'ok', value: null } : out;
    },
    voter: (year, slice, runId) =>
      call(`/elections/${year}/voters/${id(slice)}${runId ? `?run=${id(runId)}` : ''}`, VoterSchema),
  };
}
