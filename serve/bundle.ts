// The bundle contract and the session files, parsed once with zod where they
// enter the server. The bundle mirrors simharness.serialize.Bundle; both sides
// test against tests/fixtures/bundle.example.json.
import { z } from 'zod';

const fraction = z.number();

export const PageKey = z.enum(['A', 'B', 'O']);
export type PageKey = z.infer<typeof PageKey>;

/** The five shares every slice and table row splits its adults into. */
export const FIELDS = ['barred', 'home', 'A', 'B', 'O'] as const;
export type Field = (typeof FIELDS)[number];

export const Slice = z.looseObject({
  key: z.string(),
  label: z.string(),
  adults: z.number(), // millions
  barred: fraction,
  home: fraction,
  A: fraction,
  B: fraction,
  O: fraction,
  source: z.unknown()
});
export type Slice = z.infer<typeof Slice>;

export const WhatIf = z.looseObject({
  key: z.string(),
  label: z.string(),
  kind: z.string(),
  detail: z.string(),
  slices: z.array(z.string()),
  assumption: z.string()
});

export const StateResult = z.looseObject({
  code: z.string(),
  won: PageKey,
  // serialize writes a numpy bool through json's default=float: 0.0 / 1.0 in published bundles.
  flipped: z.union([z.boolean(), z.number()]),
  margin: z.number(),
  marginRange: z.array(z.number()).optional(),
  pFlip: z.number().optional()
});
export type StateResult = z.infer<typeof StateResult>;

const byKey = z.record(z.string(), z.unknown());

/** One what-if combination's result. Loose: additive fields pass through to the page. */
export const Result = z.looseObject({
  ev: z.record(z.string(), z.number()),
  winner: PageKey.nullable(),
  states: z.array(StateResult),
  slices: z.array(Slice),
  summary: z.string(),
  confidence: z.string(),
  applied: z.array(z.looseObject({ key: z.string(), label: z.string(), kind: z.string() })),
  unknown: z.string().nullable(),
  range: byKey.optional(),
  drawsWon: byKey.optional(),
  howIGotThis: z.array(z.string()).optional()
});
export type Result = z.infer<typeof Result>;

export const TableRow = z.object({
  state: z.string(),
  slice: z.string(),
  adults: z.number(),
  barred: fraction,
  home: fraction,
  A: fraction,
  B: fraction,
  O: fraction
});
export type TableRow = z.infer<typeof TableRow>;

export const Interviews = z.object({
  questions: z.array(z.string()).optional(),
  byWhatIf: z.record(z.string(), z.array(z.unknown())).optional()
});

/** What a what-if's voters were told: settled facts, news on a nominee's line, planks added and
 *  dropped, and (staged what-ifs, D33) in-world items and how many real items the change made false. */
export const Told = z.looseObject({
  facts: z.array(z.string()).optional(),
  news: z.array(z.string()).optional(),
  added: z.array(z.string()).optional(),
  dropped: z.array(z.string()).optional(),
  items: z.array(z.object({ date: z.string(), text: z.string() })).optional(),
  removed: z.number().optional()
});
export type Told = z.infer<typeof Told>;

export const Bundle = z.object({
  year: z.number().int(),
  runId: z.string(),
  election: z.object({ slices: z.array(Slice), whatIfs: z.array(WhatIf) }),
  runs: z.record(z.string(), Result),
  tables: z.record(z.string(), z.array(TableRow)),
  voters: z.record(z.string(), z.record(z.string(), z.record(z.string(), z.unknown()))),
  interviews: Interviews,
  ev: z.record(z.string(), z.number()),
  historyWinner: z.record(z.string(), PageKey),
  words: z.array(z.object({ key: z.string(), words: z.array(z.string()) })),
  // Bundles published before the briefs record (1916, 1924) lack these three.
  pre: z.record(z.string(), z.unknown()).nullable().optional(),
  told: z.record(z.string(), Told).optional(),
  reading: z.array(z.record(z.string(), z.unknown())).optional()
});
export type Bundle = z.infer<typeof Bundle>;

// ── Request bodies ──

/** Hand edits: per slice, changes in fractions of its adults (summing to 0). */
export const Edits = z.record(z.string(), z.partialRecord(z.enum(FIELDS), z.number()));
export type Edits = z.infer<typeof Edits>;

export const RunRequest = z.object({
  year: z.coerce.number().int(),
  whatIfs: z.array(z.string()).default([]),
  text: z.string().default(''),
  edits: Edits.default({})
});
export type RunRequest = z.infer<typeof RunRequest>;

// ── Session files the intake worker writes (dev only) ──

export const QueueDone = z.looseObject({
  text: z.string(),
  year: z.number().nullish(),
  status: z.string(),
  key: z.string().nullish(),
  why: z.string().nullish()
});
export type QueueDone = z.infer<typeof QueueDone>;

export const QueueFailed = z.looseObject({
  text: z.string(),
  year: z.number().nullish(),
  at: z.number(),
  why: z.string().nullish()
});
export type QueueFailed = z.infer<typeof QueueFailed>;

export const Step = z.object({ text: z.string(), state: z.string() });
export type Step = z.infer<typeof Step>;

export const IntakeStatus = z.looseObject({ text: z.string().nullable(), steps: z.array(Step) });
