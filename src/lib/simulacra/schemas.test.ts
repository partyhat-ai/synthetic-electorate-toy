import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, test } from 'vitest';
import { BundleSchema } from './schemas';

const ROOT = fileURLToPath(new URL('../../..', import.meta.url));
const FIXTURE = join(ROOT, 'tests', 'fixtures', 'bundle.example.json');

describe('BundleSchema', () => {
  test('parses the shared bundle example (tests/fixtures/bundle.example.json)', () => {
    const raw: unknown = JSON.parse(readFileSync(FIXTURE, 'utf8'));
    const parsed = BundleSchema.safeParse(raw);
    expect(parsed.error?.issues ?? []).toEqual([]);
    // Published bundles write State.flipped as 0 / 1: parsed, it is a boolean.
    const flips = Object.values(parsed.data?.runs ?? {}).flatMap((r) => r.states.map((s) => s.flipped));
    expect(flips.length).toBeGreaterThan(0);
    expect(new Set(flips.map((f) => typeof f))).toEqual(new Set(['boolean']));
  });
});
