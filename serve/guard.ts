// What stands between a visitor and money: access keys, per-IP rate limits,
// the intake's dollar caps, and how long session logs keep visitors' words.
//
// Only typed text the page doesn't already know costs anything (the intake
// worker's compile, research and interviews). That path needs an access key
// (SIMULACRA_ACCESS_KEYS), and runs only while recorded spend
// (sessions/spend.jsonl) is under both caps: SIMULACRA_KEY_DAILY_USD per key per
// UTC day (default 100) and SIMULACRA_TOTAL_USD across every key, all time
// (default 150). The worker
// (simharness/intake.py) checks the same ledger again before each text and
// stops a text at the stage that crosses what is left.
import { createHash, timingSafeEqual } from 'node:crypto';
import { readFileSync, renameSync, statSync, truncateSync, writeFileSync } from 'node:fs';
import { z } from 'zod';

// ── Access keys ──

/** SIMULACRA_ACCESS_KEYS: a JSON object of key name → key. Names are what the spend ledger records. */
const AccessKeys = z.record(z.string().regex(/^[a-z0-9][a-z0-9_-]{0,39}$/), z.string().regex(/^[A-Za-z0-9_-]{24,128}$/));

const digest = (s: string): Buffer => createHash('sha256').update(s).digest();

export interface KeyRing {
  /** The name of the key a request's Authorization header carries, or null. */
  identify(authorization: string | undefined): string | null;
  readonly size: number;
}

/** Parses SIMULACRA_ACCESS_KEYS; unset is an empty ring (nobody may queue), malformed throws at startup. */
export function parseKeyRing(raw: string | undefined): KeyRing {
  const keys = raw?.trim() ? Object.entries(AccessKeys.parse(JSON.parse(raw))) : [];
  const hashed = keys.map(([name, key]) => ({ name, hash: digest(key) }));
  return {
    size: hashed.length,
    identify(authorization) {
      const m = /^Bearer ([A-Za-z0-9_-]{1,256})$/.exec(authorization ?? '');
      if (!m?.[1]) return null;
      const h = digest(m[1]);
      // Every key is compared, in constant time, whichever matches.
      let found: string | null = null;
      for (const k of hashed) if (timingSafeEqual(h, k.hash)) found = k.name;
      return found;
    }
  };
}

// ── Rate limits ──

export interface Limit {
  /** Requests allowed per window. */
  readonly max: number;
  readonly windowMs: number;
}

export type Admit = { readonly ok: true } | { readonly ok: false; readonly retryAfterS: number };

/** A fixed window per key (an IP). Memory is bounded: expired windows are dropped as new keys arrive. */
export class RateLimiter {
  private readonly windows = new Map<string, { start: number; count: number }>();

  constructor(
    private readonly limit: Limit,
    private readonly now: () => number = Date.now,
    private readonly maxKeys = 50_000
  ) {}

  admit(key: string): Admit {
    const t = this.now();
    const w = this.windows.get(key);
    if (w && t - w.start < this.limit.windowMs) {
      if (w.count >= this.limit.max) return { ok: false, retryAfterS: Math.ceil((w.start + this.limit.windowMs - t) / 1000) };
      w.count += 1;
      return { ok: true };
    }
    // A new window goes to the back, so the oldest windows are at the front.
    this.windows.delete(key);
    this.windows.set(key, { start: t, count: 1 });
    for (const [k, old] of this.windows) {
      if (t - old.start < this.limit.windowMs && this.windows.size <= this.maxKeys) break;
      this.windows.delete(k);
    }
    return { ok: true };
  }
}

// ── Dollar caps ──

export interface Caps {
  /** Dollars per access key per UTC day. */
  readonly perKeyDaily: number;
  /** Dollars across every key, all time. */
  readonly total: number;
}

export function capsFromEnv(env: NodeJS.ProcessEnv = process.env): Caps {
  const usd = z.coerce.number().finite().nonnegative();
  return {
    perKeyDaily: env.SIMULACRA_KEY_DAILY_USD ? usd.parse(env.SIMULACRA_KEY_DAILY_USD) : 100,
    total: env.SIMULACRA_TOTAL_USD ? usd.parse(env.SIMULACRA_TOTAL_USD) : 150
  };
}

const SpendLine = z.looseObject({ day: z.string(), dollars: z.number(), who: z.string().nullish() });

export const utcDay = (t: number): string => new Date(t).toISOString().slice(0, 10);

/**
 * Spend from the ledger: every dollar recorded against an access key, ever,
 * and `who`'s dollars today (UTC). Lines without a key (before keys, or a run
 * started by hand) count toward neither, as in simharness/llm.py `spent`.
 */
export function spent(ledger: string, who: string, now: number = Date.now()): { total: number; mineToday: number } {
  const day = utcDay(now);
  let text = '';
  try {
    text = readFileSync(ledger, 'utf8');
  } catch {
    return { total: 0, mineToday: 0 };
  }
  let total = 0;
  let mineToday = 0;
  for (const line of text.split('\n')) {
    if (!line) continue;
    let row: unknown;
    try {
      row = JSON.parse(line);
    } catch {
      continue;
    }
    const r = SpendLine.safeParse(row);
    if (!r.success || !r.data.who) continue;
    total += r.data.dollars;
    if (r.data.who === who && r.data.day === day) mineToday += r.data.dollars;
  }
  return { total, mineToday };
}

export type CapCheck = { readonly kind: 'ok' } | { readonly kind: 'over'; readonly which: 'key' | 'total' };

export function checkCaps(ledger: string, who: string, caps: Caps, now: number = Date.now()): CapCheck {
  const s = spent(ledger, who, now);
  if (s.total >= caps.total) return { kind: 'over', which: 'total' };
  if (s.mineToday >= caps.perKeyDaily) return { kind: 'over', which: 'key' };
  return { kind: 'ok' };
}

// ── Session log retention ──

const Stamped = z.looseObject({ ts: z.string().optional(), at: z.number().optional() });

function stampOf(line: string): number | null {
  let row: unknown;
  try {
    row = JSON.parse(line);
  } catch {
    return null;
  }
  const r = Stamped.safeParse(row);
  if (!r.success) return null;
  if (r.data.at !== undefined) return r.data.at * 1000;
  if (r.data.ts === undefined) return null;
  // Timestamps without a zone were written in the container's zone, UTC.
  const t = Date.parse(/[zZ]|[+-]\d\d:\d\d$/.test(r.data.ts) ? r.data.ts : `${r.data.ts}Z`);
  return Number.isNaN(t) ? null : t;
}

/**
 * Drops lines older than `maxAgeMs` (and unreadable ones) from a JSONL log, by
 * writing a copy and renaming it over the original; with `scrub`, an old line
 * is kept without the named fields instead. Only call it while no worker is
 * running: the worker appends to these files. Returns lines dropped or scrubbed.
 */
export function pruneJsonl(file: string, maxAgeMs: number, now: number = Date.now(), scrub?: readonly string[]): number {
  let text: string;
  try {
    text = readFileSync(file, 'utf8');
  } catch {
    return 0;
  }
  const lines = text.split('\n').filter(Boolean);
  let changed = 0;
  const keep = lines.flatMap((l) => {
    const t = stampOf(l);
    if (t !== null && now - t <= maxAgeMs) return [l];
    if (t === null || !scrub) {
      changed += 1;
      return [];
    }
    const row = Stamped.parse(JSON.parse(l));
    if (!scrub.some((k) => k in row)) return [l];
    changed += 1;
    return [JSON.stringify(Object.fromEntries(Object.entries(row).filter(([k]) => !scrub.includes(k))))];
  });
  if (!changed) return 0;
  const tmp = `${file}.${process.pid}.tmp`;
  writeFileSync(tmp, keep.length ? `${keep.join('\n')}\n` : '');
  renameSync(tmp, file);
  return changed;
}

/** Empties a plain-text log past `maxBytes` (the worker's log; CloudWatch keeps its own copy). */
export function capLog(file: string, maxBytes: number): boolean {
  try {
    if (statSync(file).size <= maxBytes) return false;
    truncateSync(file, 0);
    return true;
  } catch {
    return false;
  }
}
