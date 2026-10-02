import { existsSync, readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, test } from 'vitest';
import { BundleSchema, RUN_LIMITS, RunRequestSchema } from './contract';

const ROOT = path.resolve(import.meta.dirname, '..');
const FIXTURE = path.join(ROOT, 'tests', 'fixtures', 'bundle.example.json');
const BUNDLES = path.join(ROOT, 'serve', 'bundles');

describe('BundleSchema', () => {
  test('parses the shared bundle example (tests/fixtures/bundle.example.json)', () => {
    const parsed = BundleSchema.safeParse(JSON.parse(readFileSync(FIXTURE, 'utf8')));
    expect(parsed.error?.issues ?? []).toEqual([]);
    // Published bundles write State.flipped as 0 / 1: parsed, it is a boolean.
    const flips = Object.values(parsed.data?.runs ?? {}).flatMap((r) => r.states.map((s) => s.flipped));
    expect(flips.length).toBeGreaterThan(0);
    expect(new Set(flips.map((f) => typeof f))).toEqual(new Set(['boolean']));
  });

  test('fields it does not name pass through, for the page', () => {
    const raw = JSON.parse(readFileSync(FIXTURE, 'utf8'));
    const run = BundleSchema.parse(raw).runs[''];
    expect(run && Object.keys(run).sort()).toEqual(Object.keys(raw.runs['']).sort());
  });

  const files = existsSync(BUNDLES) ? readdirSync(BUNDLES).filter((f) => /^\d{4}\.json$/.test(f)) : [];
  test.skipIf(files.length === 0)('parses every served bundle (skips when serve/bundles is absent)', () => {
    const bad = files.filter((f) => !BundleSchema.safeParse(JSON.parse(readFileSync(path.join(BUNDLES, f), 'utf8'))).success);
    expect(bad).toEqual([]);
  });
});

describe('RunRequestSchema', () => {
  const ok = (body: unknown) => RunRequestSchema.safeParse(body).success;

  test('a plain ask parses, with defaults and the words trimmed', () => {
    expect(RunRequestSchema.parse({ year: '1920', text: '  the league passes  ' })).toEqual({
      year: 1920,
      whatIfs: [],
      text: 'the league passes',
      edits: {}
    });
  });

  test('the year is an election year in range', () => {
    expect(ok({ year: RUN_LIMITS.firstYear })).toBe(true);
    expect(ok({ year: RUN_LIMITS.lastYear })).toBe(true);
    expect(ok({ year: 1788 })).toBe(false);
    expect(ok({ year: 2101 })).toBe(false);
    expect(ok({ year: 1920.5 })).toBe(false);
    expect(ok({ year: 'soon' })).toBe(false);
  });

  test('typed words: at most 300 characters once trimmed', () => {
    expect(ok({ year: 1920, text: 'x'.repeat(RUN_LIMITS.text) })).toBe(true);
    expect(ok({ year: 1920, text: ` ${'x'.repeat(RUN_LIMITS.text)} ` })).toBe(true);
    expect(ok({ year: 1920, text: 'x'.repeat(RUN_LIMITS.text + 1) })).toBe(false);
  });

  test('what-ifs: at most 32 keys of at most 80 characters', () => {
    const keys = (n: number, len = 8) => Array.from({ length: n }, (_, i) => `${i}`.padStart(len, 'k'));
    expect(ok({ year: 1920, whatIfs: keys(RUN_LIMITS.whatIfs) })).toBe(true);
    expect(ok({ year: 1920, whatIfs: keys(RUN_LIMITS.whatIfs + 1) })).toBe(false);
    expect(ok({ year: 1920, whatIfs: keys(1, RUN_LIMITS.key) })).toBe(true);
    expect(ok({ year: 1920, whatIfs: keys(1, RUN_LIMITS.key + 1) })).toBe(false);
  });

  test('edits: at most 64 groups, keys of at most 80 characters, each change within [-1, 1]', () => {
    const groups = (n: number) => Object.fromEntries(Array.from({ length: n }, (_, i) => [`g${i}`, { A: 0.1, home: -0.1 }]));
    expect(ok({ year: 1920, edits: groups(RUN_LIMITS.edits) })).toBe(true);
    expect(ok({ year: 1920, edits: groups(RUN_LIMITS.edits + 1) })).toBe(false);
    expect(ok({ year: 1920, edits: { ['k'.repeat(RUN_LIMITS.key + 1)]: { A: 0 } } })).toBe(false);
    expect(ok({ year: 1920, edits: { women: { A: 1, home: -1 } } })).toBe(true);
    expect(ok({ year: 1920, edits: { women: { A: 1.01 } } })).toBe(false);
    expect(ok({ year: 1920, edits: { women: { A: Number.POSITIVE_INFINITY } } })).toBe(false);
    expect(ok({ year: 1920, edits: { women: { nobody: 0.1 } } })).toBe(false);
  });
});
