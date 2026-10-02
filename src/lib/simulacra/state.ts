// The page's state, the pure parts: what the URL asks for, what a rerun of a
// year would send (askOf), whether there's anything new to run, and the
// types the page keeps per year. The reactive holder is state.svelte.ts.
import type { ApiOptions, Edits, ErrorReason, SliceEdit } from './api';
import { ELECTION_YEARS } from './geo';
import { type Election, electionOf, FEATURED } from './history';
import type { RunResult, Slice, WhatIf } from './schemas';

/** History is light; the Rerun view (the switch, with or without a rerun) is dark. */
export type View = 'history' | 'whatif';

/** Where the simulation service stands: no answer yet, answering, or why not. */
export type Server = 'connecting' | 'online' | 'offline' | 'unsupported' | 'limited';

/**
 * Where the service stands after a year's voters failed to load: unreachable
 * is offline; too many requests is `limited` until it has answered (then the
 * year's own message says so); any other answer leaves it as it was, except
 * that a first load that never got a usable answer counts as offline.
 */
export function serverAfter(now: Server, reason: ErrorReason): Server {
  switch (reason) {
    case 'offline':
      return 'offline';
    case 'limited':
      return now === 'online' ? now : 'limited';
    case 'missing':
    case 'failed':
    case 'malformed':
      return now === 'connecting' ? 'offline' : now;
    default:
      return reason satisfies never;
  }
}

/** A year's groups and what-ifs, as the server sent them. */
export interface Sim {
  readonly slices: readonly Slice[];
  readonly whatIfs: readonly WhatIf[];
}

/** A finished rerun as the page keeps it: the server's result and what was asked. */
export type ShownRun = RunResult & {
  readonly runId: string;
  /** The what-ifs chosen when it ran. */
  readonly keys: readonly string[];
  /** The typed words it ran with. */
  readonly text: string;
  /** Its steps, for the robot's bubble (narrator.ts traceOf). */
  readonly trace: readonly string[];
  /** The page's state right after it ran (askOf), so Rerun with nothing changed just shows it. */
  readonly ask: string;
  /** The what-ifs it applied that the year lists. */
  readonly ran: readonly string[];
};

export interface UrlParams {
  /** ?sample=1: the labelled stand-in (sample.ts). */
  readonly sample: boolean;
  /** Dev only, ?simapi=<origin>: a local harness server. */
  readonly simapi: string | null;
  /** ?year=, when it's an election year. */
  readonly year: number | null;
}

export function readParams(params: URLSearchParams, dev: boolean): UrlParams {
  const sample = params.get('sample');
  const asked = Number(params.get('year'));
  return {
    sample: sample === '1' || sample === 'true',
    simapi: dev ? params.get('simapi') : null,
    year: ELECTION_YEARS.includes(asked) ? asked : null,
  };
}

/** What the API is pointed at (?simapi=<url> reads <url>/api/simulacra), and the access key it sends (accessKey.ts). */
export const apiOptionsFor = (simapi: string | null, accessKey: string | null = null): ApiOptions => ({
  ...(simapi ? { base: `${simapi}/api/simulacra` } : {}),
  ...(accessKey ? { accessKey } : {}),
});

/** A featured year at random, other than `not`. */
export function randomStory(not?: number, random: () => number = Math.random): number {
  const pool = FEATURED.filter((y) => y !== not);
  return pool[Math.floor(random() * pool.length)] ?? FEATURED[0] ?? ELECTION_YEARS[0] ?? 1789;
}

/** The chip on the far left wherever the year has it, until a new chip is added. */
export const LEAD_CHIP = 'no-19th';

/**
 * What-ifs the page never shows as chips. Their data stays on the server (the
 * bundles are primary data); drop a key here to bring its chip back.
 */
export const HIDDEN_CHIPS: ReadonlySet<string> = new Set([
  'eisenhower-runs-as-a-democrat', // 1952
  'first-debate-on-radio-only', // 1960
  'no-call-to-mrs-king', // 1960
  'kennedy-survives-wins-nomination', // 1968
  'democratic-nominee-is-a-man', // 2016
  'no-october-comey-letter', // 2016
  'democratic-nominee-twenty-years-younger', // 2020
  'hunter-biden-laptop-story-spreads', // 2020
  'no-black-lives-matter-movement', // 2020
]);

/**
 * The year's what-ifs in chip order, HIDDEN_CHIPS left out: chips added this
 * visit first (newest first), then LEAD_CHIP, then the rest in the server's order.
 */
export function chipOrder(whatIfs: readonly WhatIf[], added: readonly string[] = []): WhatIf[] {
  const rank = (w: WhatIf): number => {
    const i = added.indexOf(w.key);
    if (i >= 0) return i;
    return w.key === LEAD_CHIP ? added.length : added.length + 1;
  };
  return whatIfs
    .filter((w) => !HIDDEN_CHIPS.has(w.key))
    .map((w, i) => ({ w, i }))
    .sort((a, b) => rank(a.w) - rank(b.w) || a.i - b.i)
    .map(({ w }) => w);
}

/** The year a visit opens on without ?year=. */
export const OPENING_YEAR = 1920;

/** The URL with `year` set, or null when it already has it. */
export function urlForYear(href: string, year: number): string | null {
  const url = new URL(href);
  url.searchParams.set('year', String(year));
  return url.href === href ? null : url.href;
}

/** One election as it happened. Every ELECTION_YEARS year has one (history.test.ts). */
export function electionFor(year: number): Election {
  const e = electionOf(year);
  if (!e) throw new Error(`No election in ${year}.`);
  return e;
}

/**
 * What a rerun would send: the what-ifs (in any order), the typed words
 * (trimmed) and the year's dragged dots. Equal strings, same rerun.
 */
export const askOf = (keys: readonly string[], text: string, edits: Edits | undefined): string =>
  JSON.stringify([[...keys].sort(), text.trim(), edits ?? {}]);

/**
 * Something to run since this year's rerun on show (or, with none yet, a
 * what-if, words or dots to run at all).
 */
export function isDirty(
  shown: Pick<ShownRun, 'ask'> | null,
  selected: readonly string[],
  typed: string,
  edits: Edits | undefined,
): boolean {
  if (typed.trim()) return true;
  if (!shown) return selected.length > 0 || !!edits;
  return askOf(selected, '', edits) !== shown.ask;
}

/** A drag on a group's dots added to the year's edits: each fraction's change summed over drags. */
export function addEdit(edits: Edits | undefined, slice: string, d: SliceEdit): Edits {
  const next: Record<string, SliceEdit> = { ...edits };
  const sum: Record<string, number> = { ...next[slice] };
  for (const [k, v] of Object.entries(d)) sum[k] = (sum[k] ?? 0) + (v ?? 0);
  next[slice] = sum;
  return next;
}

/** A what-if chosen or unchosen. */
export const toggled = (now: readonly string[], key: string): string[] =>
  now.includes(key) ? now.filter((k) => k !== key) : [...now, key];
