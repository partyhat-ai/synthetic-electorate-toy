// Types shared by the sample model (sample.ts) and its written stories
// (stories.ts). Nothing here is read from outside the page.
import type { Choice, Kind } from './schemas';

/** How a group's voters split: [winner, runner-up, everyone else], summing to 1. */
export type Lean = readonly [number, number, number];

/**
 * Where a group lives, as the sample model spreads its votes over the
 * states: a region, a demographic spread, or every state by its electors.
 */
export type Region =
  | 'all'
  | 'north'
  | 'south'
  | 'new-england'
  | 'middle'
  | 'midwest'
  | 'plains'
  | 'industrial'
  | 'immigrant'
  | 'latino'
  | 'felony'
  | 'black'
  | 'black-south'
  | 'black-north';

/** Explicit weights by state code, overriding a region. */
export type StateWeights = Readonly<Record<string, number>>;

/** One written person: [name, who they are, what they did in history, what they do once a what-if reaches them, quote]. */
export type VoterSpec = readonly [name: string, line: string, history: Choice, then: Choice, quote: string];

/** A group of voters as written (a story) or as an era has it. */
export interface SliceSpec {
  readonly key: string;
  readonly label: string;
  /** Share of all adults. */
  readonly share: number;
  /** Share of the group that couldn't vote. */
  readonly barred: number;
  /** Turnout of those who could. */
  readonly turnout: number;
  /** How its voters split. */
  readonly lean: Lean;
  /** How its barred members would vote. */
  readonly leanIf?: Lean;
  readonly where: Region;
  /** Explicit state weights, used instead of `where` when present. */
  readonly states?: StateWeights;
  /** Enfranchised, it votes like its own state… */
  readonly mirror?: boolean;
  /** …with this lean toward A. */
  readonly tilt?: number;
  readonly voter?: VoterSpec;
}

/** Vote-share changes keyed by candidate bucket, for drop(). */
export interface DropTo {
  readonly A?: number;
  readonly B?: number;
}

/** The levers a what-if pulls (sample.ts implements them). */
export interface SampleContext {
  /** The election's year. */
  readonly year: number;
  /** Whether this election has a group with this key. */
  has(key: string): boolean;
  /** Some of a group's barred members (or all) can vote. */
  enfranchise(key: string, opts?: { barred?: number; turnout?: number; lean?: Lean }): void;
  /** A group's voters swing `pts` points to `to`. */
  swing(key: string, pts: number, to: 'A' | 'B'): void;
  /** Everyone in `region` (or everywhere) swings `pts` points to `to`. */
  swingAll(pts: number, to: 'A' | 'B', region: Region | null, text: string): void;
  /** A share of the other candidates' voters (in `region`) choose A or B instead; the rest stay home. */
  drop(frac: number, to: DropTo, text: string, region?: Region): void;
  /** The runner-up absorbs most of the others' voters (1860's Democrats). */
  unite(frac: number, text: string): void;
  /** Votes moved straight to `to` from the others, in given states. */
  shift(states: StateWeights, to: 'A' | 'B', text: string): void;
  /** A share of a group lives where another group does, and fares like it. */
  move(key: string, frac: number, toKey: string): void;
  /** A group turns out at `t`. */
  turnout(key: string, t: number): void;
  /** Every adult can vote, and does. */
  everyone(): void;
  /** The slave states lose their three-fifths bonus in electors. */
  apportion(): void;
  /** Black Southerners vote, where the story has no group for them (1912). */
  enfranchiseBlackSouth(opts: { lean: Lean }): void;
}

/** [key, label, kind, detail, the groups it reaches, how it changes the election]. */
export type WhatIfSpec = readonly [
  key: string,
  label: string,
  kind: Kind,
  detail: string,
  slices: readonly string[],
  apply: (c: SampleContext) => void,
];

/** One written election. `states`: a few states' real vote shares [A, B]. */
export interface Story {
  readonly slices: readonly SliceSpec[];
  readonly whatIfs: readonly WhatIfSpec[];
  readonly states: Readonly<Record<string, readonly [number, number]>>;
}

/** Votes or shares for the winner (A), the runner-up (B) and everyone else (O). */
export interface Votes {
  A: number;
  B: number;
  O: number;
}

/** A group's make-up, as fractions of its adults: barred (couldn't vote), home (could, didn't), A / B / O (voted for). */
export interface Fractions extends Votes {
  barred: number;
  home: number;
}
