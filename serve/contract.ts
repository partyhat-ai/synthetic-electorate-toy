// The page's contract with the simulation server, one definition for both
// sides: serve/bundle.ts parses the published bundles and request bodies with
// these, and the page (src/lib/simulacra/schemas.ts) parses every answer with
// them. It lives under serve/ because the server's image is built from serve/
// alone (Dockerfile); it imports nothing but zod, so the page can import it too.
// The bundle mirrors simharness.serialize.Bundle; both sides test against
// tests/fixtures/bundle.example.json (serve/contract.test.ts, tests/test_contract.py).
//
// Objects that come from a bundle are loose: fields added on the Python side
// pass through the server to the page, which reads only what's named here.
// Candidate keys follow history.ts: A is the winner, B the runner-up, O
// everyone else.
//
// GET  /manifest → Manifest { years: { [year]: runId } }
// GET  /elections/:year → ElectionResponse { slices, whatIfs, simulated, runId }
// POST /runs RunRequest { year, whatIfs: [key], text, edits } → StartedRun { id }
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

/** Where a vote is counted: the winner, the runner-up, or everyone else. */
export const BucketSchema = z.enum(['A', 'B', 'O']);
export type Bucket = z.infer<typeof BucketSchema>;

/** The five shares every slice and table row splits its adults into. */
export const FIELDS = ['barred', 'home', 'A', 'B', 'O'] as const;
export type Field = (typeof FIELDS)[number];

/** One group of adults; the five fractions are of the group's adults. `adults` is in millions. */
export const SliceSchema = z.looseObject({
  key: z.string(),
  label: z.string(),
  adults: z.number(),
  barred: z.number(),
  home: z.number(),
  A: z.number(),
  B: z.number(),
  O: z.number(),
  source: z.string().optional()
});
export type Slice = z.infer<typeof SliceSchema>;

export const WhatIfSchema = z.looseObject({
  key: z.string(),
  label: z.string(),
  kind: KindSchema,
  detail: z.string(),
  /** The groups it reaches. */
  slices: z.array(z.string()).default([]),
  assumption: z.string().optional(),
  confidenceTier: z.string().optional(),
  evidence: z.string().optional(),
  exploratory: z.boolean().optional()
});
export type WhatIf = z.infer<typeof WhatIfSchema>;

/** A year's groups and what-ifs, as its bundle holds them. */
export const ElectionSchema = z.looseObject({
  slices: z.array(SliceSchema),
  whatIfs: z.array(WhatIfSchema)
});

/** GET /elections/:year. A year without a simulation answers empty lists and `simulated: false`. */
export const ElectionResponseSchema = ElectionSchema.extend({
  simulated: z.boolean().optional(),
  /** The run this year's bundle came from; absent when there's no bundle. */
  runId: z.string().optional()
});
export type ElectionResponse = z.infer<typeof ElectionResponseSchema>;

/** GET /manifest: every published year and its run. */
export const ManifestSchema = z.object({ years: z.record(z.string(), z.string()) });

const EvSchema = z.object({ A: z.number(), B: z.number(), O: z.number() });
const PairSchema = z.tuple([z.number(), z.number()]);

export const StateResultSchema = z.looseObject({
  code: z.string(),
  /** A candidate key ('A', 'B', 'C', …) or 'O'. */
  won: z.string(),
  // serialize writes a numpy bool through json's default=float, 0.0 / 1.0, in
  // published bundles; the sample and hand-edited runs write a boolean.
  flipped: z.union([z.boolean(), z.number()]).transform((v) => v !== false && v !== 0),
  margin: z.number(),
  marginRange: PairSchema.optional(),
  pFlip: z.number().optional()
});
export type StateResult = z.infer<typeof StateResultSchema>;

export const AppliedSchema = z.looseObject({ key: z.string(), label: z.string(), kind: KindSchema });
export type Applied = z.infer<typeof AppliedSchema>;

const SourceSchema = z.looseObject({ title: z.string(), url: z.string().optional(), tier: z.string().optional() });

const FindingSchema = z.looseObject({
  claim: z.string(),
  when: z.string().optional(),
  match: z.string().optional(),
  tier: z.string().optional(),
  sources: z.array(SourceSchema).default([])
});

export const EvidenceSchema = z.looseObject({
  whatIf: z.string(),
  strength: z.string().optional(),
  summary: z.string().optional(),
  agreement: z.string().optional(),
  agreementDetail: z.string().nullable().optional(),
  findings: z.array(FindingSchema).default([]),
  caveats: z.array(z.string()).optional(),
  researchedAt: z.string().optional()
});
export type Evidence = z.infer<typeof EvidenceSchema>;

export const CohortEffectSchema = z.looseObject({
  whatIf: z.string(),
  cohort: z.string(),
  n: z.number(),
  bias: z.number().optional(),
  weight: z.number().optional(),
  exposed: z.boolean().optional(),
  dr: z.number().optional(),
  dt: z.number().optional()
});
export type CohortEffect = z.infer<typeof CohortEffectSchema>;

/** The interviews before any change: the baseline, and the leakage probes when the run had them. */
export const PreSchema = z.looseObject({
  voters: z.number(),
  interviews: z.number(),
  items: z.array(z.number()).optional(),
  asOf: z.string().optional(),
  wordings: z.number().optional(),
  recall: z.object({ n: z.number(), winnerRate: z.number() }).optional(),
  swap: z.object({ platformRate: z.number() }).optional()
});
export type Pre = z.infer<typeof PreSchema>;

/** What a what-if's voters were told: settled facts, news on a nominee's line, planks added and dropped. */
export const ToldSchema = z.looseObject({
  facts: z.array(z.string()).optional(),
  news: z.array(z.string()).optional(),
  added: z.array(z.string()).optional(),
  dropped: z.array(z.string()).optional(),
  /** A staged what-if: news from the changed world, added to the voters' newspapers. */
  items: z.array(z.object({ date: z.string(), text: z.string() })).optional(),
  /** A staged what-if: how many real newspaper items the change makes false, taken out. */
  removed: z.number().int().nonnegative().optional()
});
export type Told = z.infer<typeof ToldSchema>;

/** A dated newspaper item in the voters' briefs. */
export const ReadingSchema = z.looseObject({
  date: z.string(),
  newspaper: z.string(),
  place: z.string(),
  summary: z.string().optional()
});
export type Reading = z.infer<typeof ReadingSchema>;

const AnswerSideSchema = z.looseObject({
  choice: z.string(),
  pVote: z.number().nullable().optional(),
  quote: z.string(),
  reason: z.string().optional()
});

export const InterviewAnswerSchema = z.looseObject({
  /** Index into the interview's questions. */
  question: z.number(),
  name: z.string(),
  cohort: z.string(),
  line: z.string(),
  misread: z.boolean().optional(),
  before: AnswerSideSchema,
  after: AnswerSideSchema
});
export type InterviewAnswer = z.infer<typeof InterviewAnswerSchema>;

/** The interviews behind a rerun: the questions once, each person's answers per applied what-if. */
export const InterviewSchema = z.object({
  questions: z.array(z.string()),
  byWhatIf: z.array(z.object({ whatIf: z.string(), answers: z.array(InterviewAnswerSchema) }))
});
export type Interview = z.infer<typeof InterviewSchema>;

/** One combination of what-ifs as a bundle holds it (serialize.Result). */
export const BundleResultSchema = z.looseObject({
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
  mode: z.string().optional(),
  runId: z.string().optional()
});
export type BundleResult = z.infer<typeof BundleResultSchema>;

/** A rerun as the page receives it: the bundle's result plus what the server adds from the rest of the bundle. */
export const RunResultSchema = BundleResultSchema.extend({
  /** Why `unknown` wasn't modelled (no access key, a budget spent, the worker's reason). */
  unknownWhy: z.string().optional(),
  pre: PreSchema.optional(),
  told: z.record(z.string(), ToldSchema).optional(),
  reading: z.array(ReadingSchema).optional(),
  interview: InterviewSchema.optional(),
  queued: z.object({ text: z.string(), worker: z.boolean() }).optional()
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
    steps: z.array(StepSchema).optional()
  }),
  z.object({ status: z.literal('done'), done: z.number(), total: z.number(), result: RunResultSchema }),
  z.object({ status: z.literal('failed'), error: z.string().nullable() })
]);
export type RunStatus = z.infer<typeof RunStatusSchema>;

/** POST /runs. */
export const StartedRunSchema = z.object({ id: z.string() });
export type StartedRun = z.infer<typeof StartedRunSchema>;

/** POST /runs/:id/cancel. */
export const CancelledSchema = z.object({ ok: z.boolean().optional() });

/** One simulated person from a group: what they did in history, and in the run. */
export const VoterSchema = z.looseObject({
  name: z.string(),
  line: z.string(),
  quote: z.string(),
  history: ChoiceSchema,
  now: ChoiceSchema,
  cohort: z.string().optional()
});
export type Voter = z.infer<typeof VoterSchema>;

// ── The published bundle (serve/bundles/<year>.json) ──

/** One state × group cell of a run: what hand edits are applied to (serve/simulacra.ts applyEdits). */
export const TableRowSchema = z.object({
  state: z.string(),
  slice: z.string(),
  adults: z.number(),
  barred: z.number(),
  home: z.number(),
  A: z.number(),
  B: z.number(),
  O: z.number()
});
export type TableRow = z.infer<typeof TableRowSchema>;

/** What the server holds for a year; it answers the page from it. */
export const BundleSchema = z.object({
  year: z.number().int(),
  runId: z.string(),
  election: ElectionSchema,
  /** Each precomputed combination of what-ifs ('' is history; 'a+b' sorted), by key. */
  runs: z.record(z.string(), BundleResultSchema),
  /** The same keys as runs. */
  tables: z.record(z.string(), z.array(TableRowSchema)),
  /** Run key → slice key → one person. */
  voters: z.record(z.string(), z.record(z.string(), VoterSchema)),
  /** {} when the run had no interviews. */
  interviews: z.object({
    questions: z.array(z.string()).optional(),
    byWhatIf: z.record(z.string(), z.array(InterviewAnswerSchema)).optional()
  }),
  /** Electoral votes and history's winner by state. */
  ev: z.record(z.string(), z.number()),
  historyWinner: z.record(z.string(), BucketSchema),
  /** Keywords that read typed text as a what-if. */
  words: z.array(z.object({ key: z.string(), words: z.array(z.string()) })),
  // Bundles published before the briefs record (1916, 1924) lack these three.
  pre: PreSchema.nullable().optional(),
  told: z.record(z.string(), ToldSchema).optional(),
  reading: z.array(ReadingSchema).optional()
});
export type Bundle = z.infer<typeof BundleSchema>;

// ── POST /runs ──

/** What one rerun may ask for. The page's field stops at `text` (WhatIfComposer). */
export const RUN_LIMITS = {
  firstYear: 1789,
  lastYear: 2100,
  /** Characters of typed words, trimmed. */
  text: 300,
  /** What-if keys, and characters in each. */
  whatIfs: 32,
  key: 80,
  /** Groups edited by hand. */
  edits: 64
} as const;

/** Hand edits: per slice, changes in fractions of its adults (summing to 0). */
export const EditsSchema = z
  .record(z.string().max(RUN_LIMITS.key), z.partialRecord(z.enum(FIELDS), z.number().min(-1).max(1)))
  .refine((e) => Object.keys(e).length <= RUN_LIMITS.edits, { message: `At most ${RUN_LIMITS.edits} groups.` });
export type Edits = z.infer<typeof EditsSchema>;

export const RunRequestSchema = z.object({
  year: z.coerce.number().int().min(RUN_LIMITS.firstYear).max(RUN_LIMITS.lastYear),
  whatIfs: z.array(z.string().max(RUN_LIMITS.key)).max(RUN_LIMITS.whatIfs).default([]),
  text: z.string().trim().max(RUN_LIMITS.text).default(''),
  edits: EditsSchema.default({})
});
export type RunRequest = z.infer<typeof RunRequestSchema>;
