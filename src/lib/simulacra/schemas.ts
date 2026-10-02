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

const SourceSchema = z.object({ title: z.string(), url: z.string().optional(), tier: z.string().optional() });

const FindingSchema = z.object({
  claim: z.string(),
  when: z.string().optional(),
  match: z.string().optional(),
  tier: z.string().optional(),
  sources: z.array(SourceSchema).default([]),
});

export const EvidenceSchema = z.object({
  whatIf: z.string(),
  strength: z.string().optional(),
  summary: z.string().optional(),
  agreement: z.string().optional(),
  agreementDetail: z.string().nullable().optional(),
  findings: z.array(FindingSchema).default([]),
  caveats: z.array(z.string()).optional(),
  researchedAt: z.string().optional(),
});
export type Evidence = z.infer<typeof EvidenceSchema>;

export const CohortEffectSchema = z.object({
  whatIf: z.string(),
  cohort: z.string(),
  n: z.number(),
  bias: z.number().optional(),
  weight: z.number().optional(),
  exposed: z.boolean().optional(),
  dr: z.number().optional(),
  dt: z.number().optional(),
});
export type CohortEffect = z.infer<typeof CohortEffectSchema>;

/** The interviews before any change: the baseline, and the leakage probes when the run had them. */
export const PreSchema = z.object({
  voters: z.number(),
  interviews: z.number(),
  items: z.array(z.number()).optional(),
  asOf: z.string().optional(),
  wordings: z.number().optional(),
  recall: z.object({ n: z.number(), winnerRate: z.number() }).optional(),
  swap: z.object({ platformRate: z.number() }).optional(),
});
export type Pre = z.infer<typeof PreSchema>;

/** What the voters were told for one what-if. */
export const ToldSchema = z.object({
  facts: z.array(z.string()).optional(),
  news: z.array(z.string()).optional(),
  added: z.array(z.string()).optional(),
  dropped: z.array(z.string()).optional(),
});
export type Told = z.infer<typeof ToldSchema>;

/** A dated newspaper item in the voters' briefs. */
export const ReadingSchema = z.object({
  date: z.string(),
  newspaper: z.string(),
  place: z.string(),
  summary: z.string().optional(),
});
export type Reading = z.infer<typeof ReadingSchema>;

const AnswerSideSchema = z.object({
  choice: z.string(),
  pVote: z.number().nullable().optional(),
  quote: z.string(),
  reason: z.string().optional(),
});

export const InterviewAnswerSchema = z.object({
  /** Index into the interview's questions. */
  question: z.number(),
  name: z.string(),
  cohort: z.string(),
  line: z.string(),
  misread: z.boolean().optional(),
  before: AnswerSideSchema,
  after: AnswerSideSchema,
});
export type InterviewAnswer = z.infer<typeof InterviewAnswerSchema>;

/** The interviews behind a rerun: the questions once, each person's answers per applied what-if. */
export const InterviewSchema = z.object({
  questions: z.array(z.string()),
  byWhatIf: z.array(z.object({ whatIf: z.string(), answers: z.array(InterviewAnswerSchema) })),
});
export type Interview = z.infer<typeof InterviewSchema>;

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
  unknownWhy: z.string().optional(),
  confidenceTier: z.string().optional(),
  confidenceLabel: z.string().optional(),
  confidenceFlags: z.array(z.string()).optional(),
  confidenceReasons: z.array(z.string()).optional(),
  range: z.object({ A: PairSchema, B: PairSchema, O: PairSchema }).optional(),
  drawsWon: z.record(z.string(), z.number()).optional(),
  popular: EvSchema.optional(),
  assumptions: z.array(z.string()).optional(),
  howIGotThis: z.array(z.string()).optional(),
  sources: z.array(SourceSchema).optional(),
  evidence: z.array(EvidenceSchema).optional(),
  cohortEffects: z.array(CohortEffectSchema).optional(),
  pre: PreSchema.optional(),
  told: z.record(z.string(), ToldSchema).optional(),
  reading: z.array(ReadingSchema).optional(),
  interview: InterviewSchema.optional(),
  queued: z.object({ text: z.string(), worker: z.boolean() }).optional(),
  mode: z.string().optional(),
  runId: z.string().optional(),
});
export type RunResult = z.infer<typeof RunResultSchema>;

export const StepSchema = z.object({ text: z.string(), state: z.enum(['done', 'doing']) });
export type Step = z.infer<typeof StepSchema>;

/** GET /runs/:id. */
export const RunStatusSchema = z.discriminatedUnion('status', [
  z.object({
    status: z.literal('running'),
    done: z.number(),
    total: z.number(),
    /** New words being modelled on the server: its working so far. */
    steps: z.array(StepSchema).optional(),
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
  pre: PreSchema.optional(),
  told: z.record(z.string(), ToldSchema).optional(),
  reading: z.array(ReadingSchema).optional(),
  interviews: z
    .object({ questions: z.array(z.string()), byWhatIf: z.record(z.string(), z.array(InterviewAnswerSchema)) })
    .optional(),
});
export type Bundle = z.infer<typeof BundleSchema>;
