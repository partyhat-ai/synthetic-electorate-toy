import { describe, expect, test } from 'vitest';
import { boltProfile, recoilAfter, SHOT_LIFE_S, shotFade, shotTravel } from './blast';

describe('the bolt', () => {
  test('comes to a point at the tail and the nose, widest just past the middle', () => {
    expect(boltProfile(0)).toBe(0);
    expect(boltProfile(1)).toBeCloseTo(0, 6);
    const samples = Array.from({ length: 101 }, (_, i) => boltProfile(i / 100));
    const widest = samples.indexOf(Math.max(...samples)) / 100;
    expect(widest).toBeGreaterThan(0.6);
    expect(widest).toBeLessThan(0.7);
    expect(Math.max(...samples)).toBeCloseTo(1, 2);
  });
});

describe('a shot', () => {
  test('flies out fast and eases only a touch over its life', () => {
    expect(shotTravel(10, 0)).toBe(0);
    expect(shotTravel(10, 1)).toBeCloseTo(9.2);
    // Still moving outward at the end of its life.
    expect(shotTravel(10, SHOT_LIFE_S)).toBeGreaterThan(shotTravel(10, SHOT_LIFE_S - 0.01));
  });
  test('stays whole until its last quarter second, then fades out', () => {
    expect(shotFade(0)).toBe(1);
    expect(shotFade(SHOT_LIFE_S - 0.25)).toBe(1);
    expect(shotFade(SHOT_LIFE_S - 0.125)).toBeCloseTo(0.5);
    expect(shotFade(SHOT_LIFE_S)).toBe(0);
    expect(shotFade(SHOT_LIFE_S + 1)).toBe(0);
  });
});

describe('the recoil', () => {
  test('is gone a fifth of a second after a shot', () => {
    expect(recoilAfter(1, 0.1)).toBeCloseTo(0.5);
    expect(recoilAfter(1, 0.2)).toBe(0);
    expect(recoilAfter(0, 0.016)).toBe(0);
  });
});
