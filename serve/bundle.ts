// What enters the server, parsed once with zod: the bundle contract and the
// request bodies (one definition, shared with the page: ./contract.ts), and
// the session files the intake worker writes. The names here are the
// server's: each value is also its parsed type.
import { z } from 'zod';
import {
  BucketSchema,
  BundleResultSchema,
  BundleSchema,
  EditsSchema,
  RunRequestSchema,
  SliceSchema,
  StepSchema,
  TableRowSchema,
  ToldSchema
} from './contract';

export { FIELDS, type Field, RUN_LIMITS } from './contract';

export const PageKey = BucketSchema;
export type PageKey = z.infer<typeof PageKey>;

export const Slice = SliceSchema;
export type Slice = z.infer<typeof Slice>;

/** One what-if combination's result, as the bundle holds it. Loose: additive fields pass through to the page. */
export const Result = BundleResultSchema;
export type Result = z.infer<typeof Result>;

export const TableRow = TableRowSchema;
export type TableRow = z.infer<typeof TableRow>;

export const Told = ToldSchema;
export type Told = z.infer<typeof Told>;

export const Bundle = BundleSchema;
export type Bundle = z.infer<typeof Bundle>;

// ── Request bodies ──

/** Hand edits: per slice, changes in fractions of its adults (summing to 0). */
export const Edits = EditsSchema;
export type Edits = z.infer<typeof Edits>;

/** POST /runs, within RUN_LIMITS. */
export const RunRequest = RunRequestSchema;
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

export const Step = StepSchema;
export type Step = z.infer<typeof Step>;

export const IntakeStatus = z.looseObject({ text: z.string().nullable(), steps: z.array(Step) });
