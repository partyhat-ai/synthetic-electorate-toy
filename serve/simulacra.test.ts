// The real router and app, in process, over real HTTP, reading the real bundles in serve/bundles/.
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import type { AddressInfo } from 'node:net';
import { tmpdir } from 'node:os';
import path from 'node:path';
import type { Server } from 'node:http';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { z } from 'zod';
import { createApp } from './app';
import { Bundle } from './bundle';
import { IMMUTABLE, SHORT_CACHE, type SimulacraOptions } from './simulacra';

const ROOT = path.resolve(import.meta.dirname, '..');
const scratch = mkdtempSync(path.join(tmpdir(), 'simulacra-test-'));
const options: SimulacraOptions = {
  bundles: path.join(ROOT, 'serve', 'bundles'),
  sessions: path.join(scratch, 'sessions'),
  devLog: false,
  autorun: null,
  python: 'python3',
  root: ROOT
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
