import { describe, expect, test } from 'vitest';
import { ACCESS_KEY_STORAGE, findAccessKey, type KeyStorage, splitHash } from './accessKey';

const KEY = 'abcDEF0123456789_-xy';

/** sessionStorage's two calls over a Map. */
function memoryStorage(initial: Record<string, string> = {}) {
  const items = new Map(Object.entries(initial));
  const storage: KeyStorage = {
    getItem: (k) => items.get(k) ?? null,
    setItem: (k, v) => {
      items.set(k, v);
    },
  };
  return { items, storage: () => storage };
}

const blocked = (): KeyStorage => {
  throw new DOMException('The operation is insecure.', 'SecurityError');
};

describe('splitHash', () => {
  test('takes out the key= part and keeps the rest as written', () => {
    expect(splitHash(`#key=${KEY}`)).toEqual({ value: KEY, rest: '' });
    expect(splitHash(`#a=1&key=${KEY}&b`)).toEqual({ value: KEY, rest: '#a=1&b' });
    expect(splitHash('#about')).toEqual({ value: null, rest: '#about' });
    expect(splitHash('')).toEqual({ value: null, rest: '' });
  });
});

describe('findAccessKey', () => {
  test('a key in the hash is kept for the tab and leaves the hash', () => {
    const { items, storage } = memoryStorage();
    expect(findAccessKey(`#key=${KEY}`, storage)).toEqual({ key: KEY, hash: '' });
    expect(items.get(ACCESS_KEY_STORAGE)).toBe(KEY);
  });

  test('without one in the hash, the stored key; the hash is left alone', () => {
    const { storage } = memoryStorage({ [ACCESS_KEY_STORAGE]: KEY });
    expect(findAccessKey('', storage)).toEqual({ key: KEY, hash: null });
    expect(findAccessKey('#about', storage)).toEqual({ key: KEY, hash: null });
  });

  test('a malformed key is never used or stored, but still leaves the hash', () => {
    const { items, storage } = memoryStorage();
    for (const bad of ['short', `${KEY}!`, 'x'.repeat(129), '']) {
      expect(findAccessKey(`#key=${bad}&a`, storage)).toEqual({ key: null, hash: '#a' });
    }
    expect(items.size).toBe(0);
  });

  test('a stored value that is not a key is ignored', () => {
    expect(findAccessKey('', memoryStorage({ [ACCESS_KEY_STORAGE]: 'nope' }).storage).key).toBeNull();
  });

  test('blocked storage: the hash key still serves this load; nothing stored is nothing', () => {
    expect(findAccessKey(`#key=${KEY}`, blocked)).toEqual({ key: KEY, hash: '' });
    expect(findAccessKey('', blocked)).toEqual({ key: null, hash: null });
  });
});
