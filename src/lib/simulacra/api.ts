// Simulacra Americana's connection to the simulation server, under
// /api/simulacra (pnpm serve in development, proxied by Vite). The page
// shows each election as it happened (history.ts) with none of it; the
// groups of voters, the what-ifs and every rerun come from here, or from the
// labelled stand-in in sample.ts, which has the same shape.
//
// Every answer is parsed once here (schemas.ts). A call that fails throws a
// SimError saying why.
import type { z } from 'zod';
import {
  CancelledSchema,
  type ElectionResponse,
  ElectionResponseSchema,
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
  /** No answer: the network. */
  | 'offline'
  /** 401 / 403. */
  | 'auth'
  /** A 404 after the service has answered before. */
  | 'missing'
  /** A 404 before any answer: there is no simulation service. */
  | 'unsupported'
  /** Any other non-2xx. */
  | 'failed'
  /** A 2xx whose body isn't the contract. */
  | 'malformed';

export class SimError extends Error {
  readonly reason: ErrorReason;
  readonly status: number;

  constructor(reason: ErrorReason, message: string, status = 0) {
    super(message);
    this.reason = reason;
    this.status = status;
  }
}

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
  election(year: number): Promise<ElectionResponse>;
  startRun(year: number, ask?: RunAsk): Promise<StartedRun>;
  run(runId: string): Promise<RunStatus>;
  stopRun(runId: string): Promise<void>;
  voter(year: number, slice: string, runId?: string | null): Promise<Voter>;
}

export type Fetch = (input: string, init?: RequestInit) => Promise<Response>;

export interface ApiOptions {
  /** Defaults to the global fetch. */
  readonly fetch?: Fetch;
  /** Defaults to the same-origin /api/simulacra. */
  readonly base?: string;
}

export const DEFAULT_BASE = '/api/simulacra';

export function createSimulacraApi(options: ApiOptions = {}): SimulacraApi {
  const doFetch: Fetch = options.fetch ?? ((input, init) => globalThis.fetch(input, init));
  const root = options.base ?? DEFAULT_BASE;
  // A 404 before the service has ever answered means there's no service.
  let answered = false;

  async function call<S extends z.ZodType>(path: string, schema: S, body?: unknown): Promise<z.output<S>> {
    const init: RequestInit | undefined =
      body === undefined ? undefined : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
    let res: Response;
    try {
      res = await doFetch(root + path, init);
    } catch {
      throw new SimError('offline', 'Can’t reach the simulation server.');
    }
    if (res.status === 404 && !answered) throw new SimError('unsupported', 'This server has no simulation service yet.', 404);
    if (res.status === 404) throw new SimError('missing', 'Not found.', 404);
    if (res.status === 401 || res.status === 403) throw new SimError('auth', 'Sign in to rerun elections.', res.status);
    if (!res.ok) throw new SimError('failed', `The simulation server answered ${res.status}.`, res.status);
    answered = true;
    let json: unknown;
    try {
      json = await res.json();
    } catch {
      throw new SimError('malformed', 'The simulation server sent an unreadable answer.', res.status);
    }
    const parsed = schema.safeParse(json);
    if (!parsed.success) throw new SimError('malformed', 'The simulation server sent an answer this page can’t read.', res.status);
    return parsed.data;
  }

  const id = encodeURIComponent;
  return {
    sample: false,
    election: (year) => call(`/elections/${year}`, ElectionResponseSchema),
    startRun: (year, { whatIfs = [], text = '', edits = {} } = {}) =>
      call('/runs', StartedRunSchema, { year, whatIfs, text, edits }),
    run: (runId) => call(`/runs/${id(runId)}`, RunStatusSchema),
    stopRun: async (runId) => {
      await call(`/runs/${id(runId)}/cancel`, CancelledSchema, {});
    },
    voter: (year, slice, runId) =>
      call(`/elections/${year}/voters/${id(slice)}${runId ? `?run=${id(runId)}` : ''}`, VoterSchema),
  };
}
