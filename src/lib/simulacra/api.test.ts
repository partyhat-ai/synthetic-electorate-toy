import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, test } from 'vitest';
import { createSimulacraApi, type Fetch } from './api';
import { BundleSchema } from './schemas';

const ROOT = fileURLToPath(new URL('../../..', import.meta.url));
const FIXTURE = join(ROOT, 'tests', 'fixtures', 'bundle.example.json');
const BUNDLES = join(ROOT, 'serve', 'bundles');

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

/** A fake server: answers each call from `reply`, and records what was asked. */
function fakeFetch(reply: (url: string, init?: RequestInit) => Response | Promise<Response>) {
  const calls: { url: string; init?: RequestInit | undefined }[] = [];
  const fetch: Fetch = async (url, init) => {
    calls.push({ url, init });
    return reply(url, init);
  };
  return { fetch, calls };
}

const SLICE = { key: 'women', label: 'Women', adults: 27.1, barred: 0.92, home: 0.04, A: 0.02, B: 0.01, O: 0.01 };
const ELECTION = {
  slices: [SLICE],
  whatIfs: [{ key: 'women', label: 'Women Vote', kind: 'franchise', detail: 'Every woman can vote.', slices: ['women'] }],
  simulated: true,
};

describe('createSimulacraApi', () => {
  test('a valid election parses to ok', async () => {
    const { fetch, calls } = fakeFetch(() => json(ELECTION));
    const api = createSimulacraApi({ fetch });
    const out = await api.election(1912);
    expect(calls[0]?.url).toBe('/api/simulacra/elections/1912');
    expect(out.kind).toBe('ok');
    if (out.kind === 'ok') {
      expect(out.value.slices[0]?.label).toBe('Women');
      expect(out.value.whatIfs[0]?.kind).toBe('franchise');
    }
  });

  test('a year without a bundle answers empty lists, not an error', async () => {
    const { fetch } = fakeFetch(() => json({ slices: [], whatIfs: [], simulated: false }));
    const out = await createSimulacraApi({ fetch }).election(1789);
    expect(out).toEqual({ kind: 'ok', value: { slices: [], whatIfs: [], simulated: false } });
  });

  test('malformed JSON is an error', async () => {
    const { fetch } = fakeFetch(() => new Response('{"slices": [', { status: 200 }));
    const out = await createSimulacraApi({ fetch }).election(1912);
    expect(out.kind).toBe('error');
    if (out.kind === 'error') expect(out.reason).toBe('malformed');
  });

  test('JSON outside the contract is an error', async () => {
    const { fetch } = fakeFetch(() => json({ slices: [{ key: 'women' }], whatIfs: [] }));
    const out = await createSimulacraApi({ fetch }).election(1912);
    expect(out.kind).toBe('error');
    if (out.kind === 'error') expect(out.reason).toBe('malformed');
  });

  test('a first 404 means no simulation service; a later one is just missing', async () => {
    let answered = false;
    const { fetch } = fakeFetch((url) => {
      if (url.endsWith('/elections/1912') && answered) return json(ELECTION);
      answered = true;
      return json({ error: 'not found' }, 404);
    });
    const api = createSimulacraApi({ fetch });
    expect((await api.election(1912)).kind).toBe('unsupported');
    expect((await api.election(1912)).kind).toBe('ok');
    const later = await api.voter(1912, 'nobody');
    expect(later.kind).toBe('error');
    if (later.kind === 'error') expect([later.reason, later.status]).toEqual(['missing', 404]);
  });

  test('a POST that times out is indeterminate: the run may have started', async () => {
    // Answers nothing until the caller gives up, like a server that took the write and hung.
    const { fetch } = fakeFetch(
      (_url, init) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
        }),
    );
    const out = await createSimulacraApi({ fetch, timeoutMs: 10 }).startRun(1912, { whatIfs: ['women'] });
    expect(out.kind).toBe('indeterminate');
  });

  test('a GET that times out is an error, not indeterminate', async () => {
    const { fetch } = fakeFetch(
      (_url, init) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
        }),
    );
    const out = await createSimulacraApi({ fetch, timeoutMs: 10 }).election(1912);
    expect(out.kind).toBe('error');
    if (out.kind === 'error') expect(out.reason).toBe('offline');
  });

  test('an unreachable server is offline', async () => {
    const { fetch } = fakeFetch(() => Promise.reject(new TypeError('fetch failed')));
    const out = await createSimulacraApi({ fetch }).startRun(1912);
    expect(out.kind).toBe('error');
    if (out.kind === 'error') expect(out.reason).toBe('offline');
  });

  test('startRun posts the ask and returns the run id; run parses each status', async () => {
    const statuses = [
      { status: 'running', done: 0, total: 0, error: null },
      { status: 'failed', error: 'That combination has not been computed.' },
    ];
    const { fetch, calls } = fakeFetch((url) => (url.endsWith('/runs') ? json({ id: 'r1' }) : json(statuses.shift())));
    const api = createSimulacraApi({ fetch, base: 'http://localhost:8787/api/simulacra' });
    const started = await api.startRun(1912, { whatIfs: ['women'], text: 'taft out', edits: { women: { A: 0.02, home: -0.02 } } });
    expect(started).toEqual({ kind: 'ok', value: { id: 'r1' } });
    expect(calls[0]?.url).toBe('http://localhost:8787/api/simulacra/runs');
    expect(calls[0]?.init?.method).toBe('POST');
    expect(JSON.parse(String(calls[0]?.init?.body))).toEqual({
      year: 1912,
      whatIfs: ['women'],
      text: 'taft out',
      edits: { women: { A: 0.02, home: -0.02 } },
    });
    const running = await api.run('r1');
    expect(running.kind === 'ok' && running.value.status).toBe('running');
    const failed = await api.run('r1');
    expect(failed.kind === 'ok' && failed.value.status === 'failed' && failed.value.error).toContain('not been computed');
  });

  test('401 asks for sign-in', async () => {
    const { fetch } = fakeFetch(() => json({ error: 'no' }, 401));
    const out = await createSimulacraApi({ fetch }).election(1912);
    expect(out.kind === 'error' && out.reason).toBe('auth');
  });
});

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

  const files = existsSync(BUNDLES) ? readdirSync(BUNDLES).filter((f) => /^\d{4}\.json$/.test(f)) : [];
  test.skipIf(files.length === 0)('parses every served bundle (skips when serve/bundles is absent)', () => {
    const bad = files.filter((f) => !BundleSchema.safeParse(JSON.parse(readFileSync(join(BUNDLES, f), 'utf8'))).success);
    expect(bad).toEqual([]);
  });
});
