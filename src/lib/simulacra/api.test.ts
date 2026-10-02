import { describe, expect, test } from 'vitest';
import { createSimulacraApi, type Fetch, SimError } from './api';

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

/** The reason a call threw, or null if it didn't. */
async function reasonOf(call: Promise<unknown>): Promise<string | null> {
  try {
    await call;
    return null;
  } catch (err) {
    return err instanceof SimError ? err.reason : 'not a SimError';
  }
}

const SLICE = { key: 'women', label: 'Women', adults: 27.1, barred: 0.92, home: 0.04, A: 0.02, B: 0.01, O: 0.01 };
const ELECTION = {
  slices: [SLICE],
  whatIfs: [{ key: 'women', label: 'Women Vote', kind: 'franchise', detail: 'Every woman can vote.', slices: ['women'] }],
};

describe('createSimulacraApi', () => {
  test('a valid election parses', async () => {
    const { fetch, calls } = fakeFetch(() => json(ELECTION));
    const api = createSimulacraApi({ fetch });
    const out = await api.election(1912);
    expect(calls[0]?.url).toBe('/api/simulacra/elections/1912');
    expect(out.slices[0]?.label).toBe('Women');
    expect(out.whatIfs[0]?.kind).toBe('franchise');
  });

  test('malformed JSON is an error', async () => {
    const { fetch } = fakeFetch(() => new Response('{"slices": [', { status: 200 }));
    expect(await reasonOf(createSimulacraApi({ fetch }).election(1912))).toBe('malformed');
  });

  test('JSON outside the contract is an error', async () => {
    const { fetch } = fakeFetch(() => json({ slices: [{ key: 'women' }], whatIfs: [] }));
    expect(await reasonOf(createSimulacraApi({ fetch }).election(1912))).toBe('malformed');
  });

  test('a first 404 means no simulation service; a later one is just missing', async () => {
    let answered = false;
    const { fetch } = fakeFetch((url) => {
      if (url.endsWith('/elections/1912') && answered) return json(ELECTION);
      answered = true;
      return json({ error: 'not found' }, 404);
    });
    const api = createSimulacraApi({ fetch });
    expect(await reasonOf(api.election(1912))).toBe('unsupported');
    expect(await reasonOf(api.election(1912))).toBeNull();
    expect(await reasonOf(api.voter(1912, 'nobody'))).toBe('missing');
  });

  test('an unreachable server is offline', async () => {
    const { fetch } = fakeFetch(() => Promise.reject(new TypeError('fetch failed')));
    expect(await reasonOf(createSimulacraApi({ fetch }).startRun(1912))).toBe('offline');
  });

  test('startRun posts the ask and returns the run id; run parses each status', async () => {
    const statuses = [
      { status: 'running', done: 0, total: 0 },
      { status: 'failed', error: 'That combination has not been computed.' },
    ];
    const { fetch, calls } = fakeFetch((url) => (url.endsWith('/runs') ? json({ id: 'r1' }) : json(statuses.shift())));
    const api = createSimulacraApi({ fetch, base: 'http://localhost:8787/api/simulacra' });
    const started = await api.startRun(1912, { whatIfs: ['women'], text: 'taft out' });
    expect(started).toEqual({ id: 'r1' });
    expect(calls[0]?.url).toBe('http://localhost:8787/api/simulacra/runs');
    expect(calls[0]?.init?.method).toBe('POST');
    expect(JSON.parse(String(calls[0]?.init?.body))).toEqual({ year: 1912, whatIfs: ['women'], text: 'taft out' });
    expect((await api.run('r1')).status).toBe('running');
    const failed = await api.run('r1');
    expect(failed.status === 'failed' && failed.error).toContain('not been computed');
  });

  test('401 asks for sign-in', async () => {
    const { fetch } = fakeFetch(() => json({ error: 'no' }, 401));
    expect(await reasonOf(createSimulacraApi({ fetch }).election(1912))).toBe('auth');
  });
});
