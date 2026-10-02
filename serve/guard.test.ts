import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { capsFromEnv, checkCaps, parseKeyRing, pruneJsonl, RateLimiter, spent } from './guard';

const dir = mkdtempSync(path.join(tmpdir(), 'simulacra-guard-'));
const DAY = 86_400_000;

describe('parseKeyRing', () => {
  const ring = parseKeyRing(JSON.stringify({ ana: 'a'.repeat(24), ben: 'b'.repeat(40) }));

  it('names the key a bearer header carries', () => {
    expect(ring.size).toBe(2);
    expect(ring.identify(`Bearer ${'a'.repeat(24)}`)).toBe('ana');
    expect(ring.identify(`Bearer ${'b'.repeat(40)}`)).toBe('ben');
  });

  it('names nobody for a missing, wrong or malformed header', () => {
    for (const h of [undefined, '', 'Bearer ', `Basic ${'a'.repeat(24)}`, `Bearer ${'a'.repeat(23)}`, `Bearer ${'a'.repeat(24)} `]) {
      expect(ring.identify(h)).toBeNull();
    }
  });

  it('is empty when unset, and refuses short keys or bad names at startup', () => {
    expect(parseKeyRing(undefined).size).toBe(0);
    expect(parseKeyRing('  ').identify(`Bearer ${'a'.repeat(24)}`)).toBeNull();
    expect(() => parseKeyRing(JSON.stringify({ ana: 'short' }))).toThrow();
    expect(() => parseKeyRing(JSON.stringify({ 'Bad Name': 'a'.repeat(24) }))).toThrow();
    expect(() => parseKeyRing('{not json')).toThrow();
  });
});

describe('RateLimiter', () => {
  it('admits max per window, then says when to retry', () => {
    let t = 0;
    const rl = new RateLimiter({ max: 2, windowMs: 10_000 }, () => t);
    expect(rl.admit('ip').ok).toBe(true);
    expect(rl.admit('ip').ok).toBe(true);
    t = 4_000;
    expect(rl.admit('ip')).toEqual({ ok: false, retryAfterS: 6 });
    expect(rl.admit('other').ok).toBe(true);
    t = 10_000;
    expect(rl.admit('ip').ok).toBe(true);
  });

  it('holds at most maxKeys windows', () => {
    let t = 0;
    const rl = new RateLimiter({ max: 1, windowMs: 1_000_000 }, () => t, 3);
    for (const ip of ['a', 'b', 'c', 'd', 'e']) {
      t += 1;
      rl.admit(ip);
    }
    // The oldest windows were dropped: 'a' starts afresh, 'e' is still limited.
    expect(rl.admit('a').ok).toBe(true);
    expect(rl.admit('e').ok).toBe(false);
  });
});

describe('dollar caps', () => {
  const now = Date.parse('2026-10-01T12:00:00Z');
  const ledger = path.join(dir, 'spend.jsonl');
  writeFileSync(
    ledger,
    `${[
      { day: '2026-10-01', dollars: 15, who: 'ana' },
      { day: '2026-09-30', dollars: 40, who: 'ana' },
      { day: '2026-10-01', dollars: 5, who: 'ben' },
      { day: '2026-10-01', dollars: 500, who: null },
      { day: '2026-10-01', dollars: 500 },
      { day: '2026-10-01', dollars: 'x', who: 'ana' }
    ]
      .map((r) => JSON.stringify(r))
      .join('\n')}\nnot json\n`
  );

  it('counts keyed spend: all time in all, and today (UTC) for one key; unkeyed lines count toward neither', () => {
    expect(spent(ledger, 'ana', now)).toEqual({ total: 60, mineToday: 15 });
    expect(spent(ledger, 'ben', now)).toEqual({ total: 60, mineToday: 5 });
    expect(spent(path.join(dir, 'missing.jsonl'), 'ana', now)).toEqual({ total: 0, mineToday: 0 });
  });

  it("is over when the key's day or the all-time total is reached", () => {
    expect(checkCaps(ledger, 'ana', { perKeyDaily: 100, total: 150 }, now)).toEqual({ kind: 'ok' });
    expect(checkCaps(ledger, 'ana', { perKeyDaily: 15, total: 150 }, now)).toEqual({ kind: 'over', which: 'key' });
    expect(checkCaps(ledger, 'ben', { perKeyDaily: 100, total: 60 }, now)).toEqual({ kind: 'over', which: 'total' });
  });

  it('defaults to $100 a key a day and $150 in all, and refuses a bad value', () => {
    expect(capsFromEnv({})).toEqual({ perKeyDaily: 100, total: 150 });
    expect(capsFromEnv({ SIMULACRA_KEY_DAILY_USD: '5', SIMULACRA_TOTAL_USD: '50' })).toEqual({ perKeyDaily: 5, total: 50 });
    expect(() => capsFromEnv({ SIMULACRA_KEY_DAILY_USD: 'lots' })).toThrow();
  });
});

describe('pruneJsonl', () => {
  it('keeps lines inside the retention, whatever their timestamp style', () => {
    const now = Date.parse('2026-10-01T12:00:00Z');
    const f = path.join(dir, 'log.jsonl');
    const rows = [
      { ts: '2026-09-20T00:00:00Z', text: 'old iso' },
      { ts: '2026-09-30T10:00:00', text: 'new, no zone' },
      { ts: '2026-09-30T10:00:00+00:00', text: 'new, offset' },
      { at: (now - 9 * DAY) / 1000, text: 'old epoch' },
      { at: (now - DAY) / 1000, text: 'new epoch' },
      { text: 'no stamp' }
    ];
    writeFileSync(f, `${rows.map((r) => JSON.stringify(r)).join('\n')}\n`);
    expect(pruneJsonl(f, 7 * DAY, now)).toBe(3);
    expect(readFileSync(f, 'utf8').trim().split('\n').map((l) => JSON.parse(l).text)).toEqual(['new, no zone', 'new, offset', 'new epoch']);
    expect(pruneJsonl(f, 7 * DAY, now)).toBe(0);
    expect(pruneJsonl(path.join(dir, 'missing.jsonl'), DAY, now)).toBe(0);
  });

  it('with scrub, keeps old lines without the named fields', () => {
    const now = Date.parse('2026-10-01T12:00:00Z');
    const f = path.join(dir, 'spend.jsonl');
    writeFileSync(
      f,
      `${[
        { ts: '2026-09-01T00:00:00Z', day: '2026-09-01', dollars: 1.5, note: 'a visitor typed this' },
        { ts: '2026-09-01T00:00:00Z', day: '2026-09-01', dollars: 0.5 },
        { ts: '2026-09-30T00:00:00Z', day: '2026-09-30', dollars: 2, note: 'recent' }
      ]
        .map((r) => JSON.stringify(r))
        .join('\n')}\n`
    );
    expect(pruneJsonl(f, 7 * DAY, now, ['note'])).toBe(1);
    expect(readFileSync(f, 'utf8').trim().split('\n').map((l) => JSON.parse(l))).toEqual([
      { ts: '2026-09-01T00:00:00Z', day: '2026-09-01', dollars: 1.5 },
      { ts: '2026-09-01T00:00:00Z', day: '2026-09-01', dollars: 0.5 },
      { ts: '2026-09-30T00:00:00Z', day: '2026-09-30', dollars: 2, note: 'recent' }
    ]);
  });
});
