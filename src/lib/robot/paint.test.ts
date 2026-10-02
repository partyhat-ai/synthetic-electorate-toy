import { describe, expect, test } from 'vitest';
import { normalizeAssetBase, DEFAULT_ASSET_BASE } from './assets';
import { overrideFor, parseOverrides, partOf } from './paint';

// The shape of the Rerun paint's overrides.json as published.
const published = {
  Armor: { roughnessFactor: 1, metallicFactor: 1, emissiveFactor: [1, 1, 1] },
  'Joint housings — navy': { baseColor: [0.0704, 0.0561, 0.0331], roughness: 0.917, metal: 0.12 },
  'Actuator collars — navy': { baseColor: [0.18, 0.14, 0.065], roughness: 0.5, metal: 0.8 },
};

describe('parseOverrides', () => {
  test('reads glTF factor names and short names alike', () => {
    const o = parseOverrides(published);
    expect(o.Armor).toEqual({ color: undefined, emissive: [1, 1, 1], roughness: 1, metalness: 1 });
    expect(o['Joint housings — navy']).toEqual({
      color: [0.0704, 0.0561, 0.0331],
      emissive: undefined,
      roughness: 0.917,
      metalness: 0.12,
    });
  });

  test('takes an RGBA factor', () => {
    expect(parseOverrides({ Visor: { baseColorFactor: [0.1, 0.2, 0.3, 1] } }).Visor?.color).toEqual([0.1, 0.2, 0.3, 1]);
  });

  test('malformed or missing overrides mean none', () => {
    expect(parseOverrides({ Armor: { baseColor: [1, 1] } })).toEqual({});
    expect(parseOverrides({ Armor: { roughness: 'high' } })).toEqual({});
    expect(parseOverrides(null)).toEqual({});
    expect(parseOverrides('{}')).toEqual({});
  });
});

describe('partOf / overrideFor', () => {
  test('armour and joints materials by name', () => {
    expect(partOf('Armor_Reactor_Emission')).toBe('armor');
    expect(partOf('armor_reactor_emission.001')).toBe('armor');
    expect(partOf('Weathered joints')).toBe('joints');
    expect(partOf('Joint housings — navy')).toBeNull();
  });

  test("armour without its own entry takes 'Armor'; others only their own", () => {
    const o = parseOverrides(published);
    expect(overrideFor(o, 'Armor_Reactor_Emission.001')?.metalness).toBe(1);
    expect(overrideFor(o, 'Actuator collars — navy')?.metalness).toBe(0.8);
    expect(overrideFor(o, 'Weathered joints')).toBeUndefined();
  });
});

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
