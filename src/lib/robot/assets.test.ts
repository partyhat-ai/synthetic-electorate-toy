import { describe, expect, test } from 'vitest';
import { DEFAULT_ASSET_BASE, normalizeAssetBase } from './assets';

describe('normalizeAssetBase', () => {
  test('defaults when unset or blank', () => {
    expect(normalizeAssetBase(undefined)).toBe(DEFAULT_ASSET_BASE);
    expect(normalizeAssetBase('  ')).toBe(DEFAULT_ASSET_BASE);
  });

  test('ends in exactly one slash', () => {
    expect(normalizeAssetBase('https://cdn.example/robot')).toBe('https://cdn.example/robot/');
    expect(normalizeAssetBase('https://cdn.example/robot/')).toBe('https://cdn.example/robot/');
  });
});
