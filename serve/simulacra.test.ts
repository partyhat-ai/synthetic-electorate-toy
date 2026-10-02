// The real router and app, in process, over real HTTP, reading the real bundles in serve/bundles/.
import { appendFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import type { AddressInfo } from 'node:net';
import { tmpdir } from 'node:os';
import path from 'node:path';
import type { Server } from 'node:http';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { z } from 'zod';
import { createApp } from './app';
import { Bundle } from './bundle';
import { parseKeyRing } from './guard';
import { DEFAULT_LIMITS, IMMUTABLE, NEEDS_KEY, OVER_KEY_CAP, OVER_TOTAL_CAP, SHORT_CACHE, type SimulacraOptions } from './simulacra';

const ROOT = path.resolve(import.meta.dirname, '..');
const scratch = mkdtempSync(path.join(tmpdir(), 'simulacra-test-'));
const options: SimulacraOptions = {
  bundles: path.join(ROOT, 'serve', 'bundles'),
  sessions: path.join(scratch, 'sessions'),
  devLog: false,
  autorun: null,
  python: 'python3',
  root: ROOT,
  keys: parseKeyRing(undefined),
  caps: { perKeyDaily: 100, total: 150 },
  retainDays: 7,
  limits: DEFAULT_LIMITS
};

let server: Server;
let base = '';

beforeAll(async () => {
  const build = path.join(scratch, 'build');
  mkdirSync(build, { recursive: true });
  writeFileSync(path.join(build, 'index.html'), '<!doctype html><title>page</title>');
  server = createApp({ simulacra: options, build }).listen(0);
  await new Promise<void>((resolve) => server.once('listening', resolve));
  // SAFETY: listen(0) on a TCP port always reports an AddressInfo, never a pipe name.
  const { port } = server.address() as AddressInfo;
  base = `http://127.0.0.1:${port}`;
});

afterAll(async () => {
  await new Promise<void>((resolve) => server.close(() => resolve()));
  rmSync(scratch, { recursive: true, force: true });
});

const Election = z.object({ simulated: z.boolean(), slices: z.array(z.object({ key: z.string() })), whatIfs: z.array(z.object({ key: z.string() })) });
const RunId = z.object({ id: z.string() });
const Done = z.object({
  status: z.literal('done'),
  result: z.looseObject({
    applied: z.array(z.object({ key: z.string() })),
    unknown: z.string().nullable(),
    range: z.unknown().optional(),
    howIGotThis: z.array(z.string())
  })
});

async function run(body: unknown) {
  const posted = await fetch(`${base}/api/simulacra/runs`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body)
  });
  expect(posted.status).toBe(200);
  const { id } = RunId.parse(await posted.json());
  const got = await fetch(`${base}/api/simulacra/runs/${id}`);
  return Done.parse(await got.json()).result;
}

describe('/api/simulacra', () => {
  it('a simulated year answers simulated: true with its slices and what-ifs', async () => {
    const res = await fetch(`${base}/api/simulacra/elections/1920`);
    expect(res.status).toBe(200);
    const e = Election.parse(await res.json());
    expect(e.simulated).toBe(true);
    expect(e.slices.map((s) => s.key)).toContain('women');
    expect(e.whatIfs.map((w) => w.key)).toContain('league');
  });

  it('a year with no bundle answers 200 with simulated: false', async () => {
    const res = await fetch(`${base}/api/simulacra/elections/1999`);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ slices: [], whatIfs: [], simulated: false });
  });

  it('the manifest names each published year and its run', async () => {
    const res = await fetch(`${base}/api/simulacra/manifest`);
    expect(res.headers.get('cache-control')).toBe(SHORT_CACHE);
    const { years } = z.object({ years: z.record(z.string(), z.string()) }).parse(await res.json());
    const runId = readFileSync(path.join(ROOT, 'serve', 'bundles', '1920.json'), 'utf8').match(/"runId": ?"([^"]+)"/)?.[1];
    expect(years['1920']).toBe(runId);
    expect(years['1999']).toBeUndefined();
  });

  it("a year's answer carries its run and is immutable only at its versioned URL", async () => {
    const plain = await fetch(`${base}/api/simulacra/elections/1920`);
    expect(plain.headers.get('cache-control')).toBe(SHORT_CACHE);
    const { runId } = z.object({ runId: z.string() }).parse(await plain.json());
    const pinned = await fetch(`${base}/api/simulacra/elections/1920?v=${encodeURIComponent(runId)}`);
    expect(pinned.headers.get('cache-control')).toBe(IMMUTABLE);
    const stale = await fetch(`${base}/api/simulacra/elections/1920?v=not-this-run`);
    expect(stale.headers.get('cache-control')).toBe(SHORT_CACHE);
    const missing = await fetch(`${base}/api/simulacra/elections/1999?v=${encodeURIComponent(runId)}`);
    expect(missing.headers.get('cache-control')).toBe(SHORT_CACHE);
  });

  it('matches keywords as whole words: "flu" is not in "influence"', async () => {
    const miss = await run({ year: 1920, text: 'the influence of the press' });
    expect(miss.applied).toEqual([]);
    expect(miss.unknown).toBe('the influence of the press');
    const hit = await run({ year: 1920, text: 'the flu comes back' });
    expect(hit.applied.map((a) => a.key)).toEqual(['influenza-returns-in-october-1920']);
    expect(hit.unknown).toBeNull();
  });

  it('hand edits re-tally one run with no range', async () => {
    const r = await run({ year: '1920', whatIfs: ['league', 'not-a-what-if'], edits: { women: { home: -0.1, B: 0.1 } } });
    expect(r.applied.map((a) => a.key)).toEqual(['league']);
    expect(r.range).toBeUndefined();
    expect(r.howIGotThis.at(-1)).toMatch(/by hand/);
  });

  it('rejects a malformed body at the boundary', async () => {
    const res = await fetch(`${base}/api/simulacra/runs`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ year: 'soon' })
    });
    expect(res.status).toBe(400);
  });

  it('serves the static build with an SPA fallback', async () => {
    const res = await fetch(`${base}/some/page`);
    expect(res.status).toBe(200);
    expect(await res.text()).toContain('<title>page</title>');
  });

  it('parses the shared bundle example', () => {
    const raw: unknown = JSON.parse(readFileSync(path.join(ROOT, 'tests/fixtures/bundle.example.json'), 'utf8'));
    const b = Bundle.parse(raw);
    expect(Object.keys(b.runs)).toContain('');
    expect(Object.keys(b.tables).sort()).toEqual(Object.keys(b.runs).sort());
  });
});

// The intake path: SIMULACRA_LOG on, an access key, today's spend, per-IP limits.
describe('/api/simulacra intake guard', () => {
  const KEY = 'k'.repeat(32);
  const sessions = path.join(scratch, 'intake-sessions');
  const today = new Date().toISOString().slice(0, 10);
  let guarded: Server;
  let url = '';

  beforeAll(async () => {
    mkdirSync(sessions, { recursive: true });
    const old = new Date(Date.now() - 30 * 86_400_000).toISOString();
    writeFileSync(path.join(sessions, 'requests.jsonl'), `${JSON.stringify({ ts: old, text: 'a month ago' })}\n${JSON.stringify({ ts: new Date().toISOString(), text: 'today' })}\n`);
    writeFileSync(path.join(sessions, 'spend.jsonl'), `${JSON.stringify({ ts: new Date().toISOString(), day: today, dollars: 25, who: 'spent' })}\n`);
    const opts: SimulacraOptions = {
      ...options,
      sessions,
      devLog: true,
      keys: parseKeyRing(JSON.stringify({ ana: KEY, spent: 's'.repeat(32) })),
      caps: { perKeyDaily: 20, total: 150 },
      limits: { ...DEFAULT_LIMITS, intake: { max: 2, windowMs: 60_000 } }
    };
    guarded = createApp({ simulacra: opts, build: path.join(scratch, 'none') }).listen(0);
    await new Promise<void>((resolve) => guarded.once('listening', resolve));
    // SAFETY: listen(0) on a TCP port always reports an AddressInfo, never a pipe name.
    url = `http://127.0.0.1:${(guarded.address() as AddressInfo).port}/api/simulacra`;
  });

  afterAll(async () => {
    await new Promise<void>((resolve) => guarded.close(() => resolve()));
  });

  const Unknown = z.looseObject({ unknown: z.string().nullable(), unknownWhy: z.string().optional(), queued: z.unknown().optional() });

  async function ask(text: string, key?: string): Promise<{ status: number; result: z.infer<typeof Unknown> | null }> {
    const posted = await fetch(`${url}/runs`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', ...(key ? { authorization: `Bearer ${key}` } : {}) },
      body: JSON.stringify({ year: 1920, text })
    });
    if (posted.status !== 200) return { status: posted.status, result: null };
    const { id } = RunId.parse(await posted.json());
    const got = z.object({ result: Unknown }).parse(await (await fetch(`${url}/runs/${id}`)).json());
    return { status: 200, result: got.result };
  }

  const queue = (): string[] => {
    try {
      return readFileSync(path.join(sessions, 'queue.jsonl'), 'utf8').split('\n').filter(Boolean);
    } catch {
      return [];
    }
  };

  it('drops session lines older than the retention at startup', () => {
    const lines = readFileSync(path.join(sessions, 'requests.jsonl'), 'utf8');
    expect(lines).not.toContain('a month ago');
    expect(lines).toContain('today');
  });

  it('queues nothing without a valid key, and says why', async () => {
    for (const key of [undefined, 'x'.repeat(32), `${KEY}x`]) {
      const r = await ask('the moon votes', key);
      expect(r.result?.unknown).toBe('the moon votes');
      expect(r.result?.unknownWhy).toBe(NEEDS_KEY);
    }
    expect(queue()).toEqual([]);
  });

  it("queues with a valid key, under the key's name", async () => {
    const r = await ask('the moon votes', KEY);
    expect(r.result?.queued).toBeDefined();
    expect(queue().map((l) => JSON.parse(l))).toEqual([expect.objectContaining({ text: 'the moon votes', who: 'ana' })]);
  });

  it('queues nothing for a key over its daily cap', async () => {
    const r = await ask('mars votes', 's'.repeat(32));
    expect(r.result?.unknownWhy).toBe(OVER_KEY_CAP);
    expect(queue()).toHaveLength(1);
  });

  it('limits how often one IP may queue', async () => {
    expect((await ask('venus votes', KEY)).status).toBe(200);
    expect((await ask('jupiter votes', KEY)).status).toBe(429);
  });

  it('queues nothing for any key once the all-time total is spent', async () => {
    const yesterday = new Date(Date.now() - 86_400_000).toISOString();
    appendFileSync(path.join(sessions, 'spend.jsonl'), `${JSON.stringify({ ts: yesterday, day: yesterday.slice(0, 10), dollars: 125, who: 'old' })}\n`);
    const r = await ask('saturn votes', KEY);
    expect(r.result?.unknownWhy).toBe(OVER_TOTAL_CAP);
  });

  it('answers a year outside any election without caching it', async () => {
    const res = await fetch(`${url}/elections/123456`);
    expect(await res.json()).toEqual({ slices: [], whatIfs: [], simulated: false });
  });
});
