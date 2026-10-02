// The key that lets typed what-ifs be modelled (POST /runs sends it, api.ts).
// It arrives once in a link's hash (#key=<value>), is kept for the tab in
// sessionStorage, and leaves the address bar at once, so it isn't passed on
// with a copied link. Without one the page works as before; the server says
// why typed words weren't modelled.
import { z } from 'zod';

export const ACCESS_KEY_STORAGE = 'simulacra.accessKey';

const AccessKeySchema = z.string().regex(/^[A-Za-z0-9_-]{16,128}$/);

/** The parts of sessionStorage this reads and writes. */
export type KeyStorage = Pick<Storage, 'getItem' | 'setItem'>;

export interface FoundKey {
  /** The key for this tab, or null. */
  readonly key: string | null;
  /** The hash without its `key=` part ('' when nothing else is left), or null when there was none to take out. */
  readonly hash: string | null;
}

/** The hash with any `key=` part taken out, and that part's value. Other parts are kept as written. */
export function splitHash(hash: string): { readonly value: string | null; readonly rest: string } {
  const parts = hash.replace(/^#/, '').split('&');
  const at = parts.findIndex((p) => p.startsWith('key='));
  if (at < 0) return { value: null, rest: hash };
  const value = parts[at]?.slice('key='.length) ?? '';
  const others = parts.filter((p, i) => i !== at && p !== '');
  return { value, rest: others.length ? `#${others.join('&')}` : '' };
}

/**
 * The tab's access key: a well-formed one in the hash (stored for the tab),
 * else the stored one. Any `key=` part leaves the hash, well formed or not.
 * `storage` is a getter: sessionStorage itself can throw (storage blocked),
 * as can each read and write; a key that can't be stored still serves this load.
 */
export function findAccessKey(hash: string, storage: () => KeyStorage): FoundKey {
  const { value, rest } = splitHash(hash);
  const given = AccessKeySchema.safeParse(value);
  if (given.success) {
    try {
      storage().setItem(ACCESS_KEY_STORAGE, given.data);
    } catch {
      // Not kept: this load still has it.
    }
    return { key: given.data, hash: rest };
  }
  let stored: string | null = null;
  try {
    stored = storage().getItem(ACCESS_KEY_STORAGE);
  } catch {
    // No storage: no key.
  }
  const kept = AccessKeySchema.safeParse(stored);
  return { key: kept.success ? kept.data : null, hash: value === null ? null : rest };
}
