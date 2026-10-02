// The simulation server's answers, parsed once where they enter the page
// (api.ts). Every type the page uses for them derives from these schemas.
// Candidate keys follow history.ts: A is the winner, B the runner-up, O
// everyone else.
//
// GET  /elections/:year → ElectionResponse { slices, whatIfs, simulated }
// POST /runs { year, whatIfs: [key], text, edits } → StartedRun { id }
// GET  /runs/:id → RunStatus (running | done with a RunResult | failed)
// POST /runs/:id/cancel → { ok }
// GET  /elections/:year/voters/:slice?run=:id → Voter
import { z } from 'zod';

/** A what-if's kind: who can vote, who lives where, what people care about, who is on the ballot. */
export const KindSchema = z.enum(['franchise', 'population', 'issue', 'candidate']);
export type Kind = z.infer<typeof KindSchema>;

/** What one person did: voted for A, B or someone else, stayed home, or couldn't vote. */
export const ChoiceSchema = z.enum(['A', 'B', 'O', 'home', 'barred']);
export type Choice = z.infer<typeof ChoiceSchema>;

export const BucketSchema = z.enum(['A', 'B', 'O']);

/** One group of adults; the five fractions are of the group's adults. `adults` is in millions. */
export const SliceSchema = z.object({
  key: z.string(),
  label: z.string(),
  adults: z.number(),
  barred: z.number(),
  home: z.number(),
  A: z.number(),
  B: z.number(),
  O: z.number(),
  source: z.string().optional(),
});
export type Slice = z.infer<typeof SliceSchema>;

export const WhatIfSchema = z.object({
  key: z.string(),
  label: z.string(),
  kind: KindSchema,
  detail: z.string(),
  /** The groups it reaches. */
  slices: z.array(z.string()).default([]),
  assumption: z.string().optional(),
  confidenceTier: z.string().optional(),
  evidence: z.string().optional(),
  exploratory: z.boolean().optional(),
});
export type WhatIf = z.infer<typeof WhatIfSchema>;

/** GET /elections/:year. A year without a simulation answers empty lists and `simulated: false`. */
export const ElectionResponseSchema = z.object({
  slices: z.array(SliceSchema),
  whatIfs: z.array(WhatIfSchema),
  simulated: z.boolean().optional(),
});
export type ElectionResponse = z.infer<typeof ElectionResponseSchema>;

const EvSchema = z.object({ A: z.number(), B: z.number(), O: z.number() });
const PairSchema = z.tuple([z.number(), z.number()]);

export const StateResultSchema = z.object({
  code: z.string(),
  /** A candidate key ('A', 'B', 'C', …) or 'O'. */
  won: z.string(),
  // Bundles write 0 / 1; the sample writes a boolean.
  flipped: z.union([z.boolean(), z.number()]).transform((v) => v !== false && v !== 0),
  margin: z.number(),
  marginRange: PairSchema.optional(),
  pFlip: z.number().optional(),
});
export type StateResult = z.infer<typeof StateResultSchema>;

export const AppliedSchema = z.object({ key: z.string(), label: z.string(), kind: KindSchema });
export type Applied = z.infer<typeof AppliedSchema>;

export const RunResultSchema = z.object({
  ev: EvSchema,
  /** null: no one has a majority. */
  winner: BucketSchema.nullable(),
  states: z.array(StateResultSchema),
  slices: z.array(SliceSchema),
  summary: z.string(),
  /** null: nothing was applied. */
  confidence: z.enum(['high', 'medium', 'low']).nullable(),
  applied: z.array(AppliedSchema),
  /** The part of the typed text the server couldn't use. */
  unknown: z.string().nullable(),
  confidenceTier: z.string().optional(),
  confidenceFlags: z.array(z.string()).optional(),
  confidenceReasons: z.array(z.string()).optional(),
  range: z.object({ A: PairSchema, B: PairSchema, O: PairSchema }).optional(),
  drawsWon: z.record(z.string(), z.number()).optional(),
  popular: EvSchema.optional(),
  assumptions: z.array(z.string()).optional(),
  mode: z.string().optional(),
  runId: z.string().optional(),
});
export type RunResult = z.infer<typeof RunResultSchema>;

/** GET /runs/:id. */
export const RunStatusSchema = z.discriminatedUnion('status', [
  z.object({
    status: z.literal('running'),
    done: z.number(),
    total: z.number(),
  }),
  z.object({ status: z.literal('done'), done: z.number(), total: z.number(), result: RunResultSchema }),
  z.object({ status: z.literal('failed'), error: z.string().nullable() }),
]);
export type RunStatus = z.infer<typeof RunStatusSchema>;

/** POST /runs. */
export const StartedRunSchema = z.object({ id: z.string() });
export type StartedRun = z.infer<typeof StartedRunSchema>;

/** POST /runs/:id/cancel. */
export const CancelledSchema = z.object({ ok: z.boolean().optional() });

/** One simulated person from a group: what they did in history, and in the run. */
export const VoterSchema = z.object({
  name: z.string(),
  line: z.string(),
  quote: z.string(),
  history: ChoiceSchema,
  now: ChoiceSchema,
  cohort: z.string().optional(),
});
export type Voter = z.infer<typeof VoterSchema>;

// ── The published bundle (serve/bundles/<year>.json) ──
// What the server holds for a year; it answers the page from it.
export const BundleSchema = z.object({
  year: z.number(),
  runId: z.string(),
  election: ElectionResponseSchema,
  /** Each precomputed combination of what-ifs ('' is history), by key. */
  runs: z.record(z.string(), RunResultSchema),
  /** run key → slice key → one person. */
  voters: z.record(z.string(), z.record(z.string(), VoterSchema)),
  /** Electoral votes and history's winner by state. */
  ev: z.record(z.string(), z.number()),
  historyWinner: z.record(z.string(), z.string()),
  /** Keywords that read typed text as a what-if. */
  words: z.array(z.object({ key: z.string(), words: z.array(z.string()) })).default([]),
});
export type Bundle = z.infer<typeof BundleSchema>;
