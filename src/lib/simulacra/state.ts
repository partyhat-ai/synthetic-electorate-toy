// The page's state, the pure parts: what the URL asks for, whether there's
// anything new to run, and the types the page keeps. The reactive holder is
// state.svelte.ts.
import type { Edits, SliceEdit } from './api';
import { ELECTION_YEARS } from './geo';
import { type Election, electionOf, FEATURED } from './history';
import type { RunResult, Slice, WhatIf } from './schemas';

/** History is light; the Rerun view (the switch, with or without a rerun) is dark. */
export type View = 'history' | 'whatif';

/** Where the simulation service stands: no answer yet, answering, or why not. */
export type Server = 'connecting' | 'online' | 'offline' | 'unsupported' | 'auth';

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
  /** The what-ifs it ran. */
  readonly ran: readonly string[];
};

export interface UrlParams {
  /** ?sample=1: the labelled stand-in (sample.ts). */
  readonly sample: boolean;
  /** ?year=, when it's an election year. */
  readonly year: number | null;
}

export function readParams(params: URLSearchParams): UrlParams {
  const sample = params.get('sample');
  const asked = Number(params.get('year'));
  return {
    sample: sample === '1' || sample === 'true',
    year: ELECTION_YEARS.includes(asked) ? asked : null,
  };
}

/** A featured year at random, other than `not`. */
export function randomStory(not?: number, random: () => number = Math.random): number {
  const pool = FEATURED.filter((y) => y !== not);
  return pool[Math.floor(random() * pool.length)] ?? FEATURED[0] ?? ELECTION_YEARS[0] ?? 1789;
}

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
 * Something to run since the rerun on show (or, with none yet, a what-if,
 * words or dots to run at all).
 */
export function isDirty(
  shown: Pick<ShownRun, 'ran'> | null,
  selected: readonly string[],
  typed: string,
  edits: Edits | undefined,
): boolean {
  if (typed.trim()) return true;
  if (!shown) return selected.length > 0 || !!edits;
  return selected.length !== shown.ran.length || selected.some((k) => !shown.ran.includes(k));
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
