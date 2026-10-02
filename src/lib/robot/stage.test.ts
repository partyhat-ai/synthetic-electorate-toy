import { describe, expect, test } from 'vitest';
import { DEFAULT_STAGE, nudgeToSlot, sameStage, stageInSlot } from './stage';

const rect = (left: number, top: number, width: number, height: number) => ({
  left,
  top,
  width,
  right: left + width,
  bottom: top + height,
});

describe('stageInSlot', () => {
  test('centres the 200px box on the slot with its floor on the slot’s bottom', () => {
    const host = rect(0, 0, 1200, 900);
    const slot = rect(100, 500, 300, 200); // centre x 250, bottom 700
    const s = stageInSlot(host, slot, { x: 0, y: 0 });
    expect(s).toEqual({ right: 1200 - 250 - 100, bottom: 200, width: 200, height: 260 });
  });

  test('a nudge moves the box right and down', () => {
    const host = rect(0, 0, 1200, 900);
    const slot = rect(100, 500, 300, 200);
    const s = stageInSlot(host, slot, { x: 12, y: -5 });
    expect(s.right).toBe(850 - 12);
    expect(s.bottom).toBe(200 + 5);
  });
});

describe('nudgeToSlot', () => {
  test('is the gap between the robot and the slot’s centre and floor', () => {
    const slot = rect(100, 500, 300, 200);
    expect(nudgeToSlot(slot, { centerX: 240, feetY: 690 })).toEqual({ x: 10, y: 4 });
  });
});

describe('sameStage', () => {
  test('compares by value', () => {
    expect(sameStage(DEFAULT_STAGE, { ...DEFAULT_STAGE })).toBe(true);
    expect(sameStage(DEFAULT_STAGE, { ...DEFAULT_STAGE, right: 11 })).toBe(false);
    expect(sameStage(null, null)).toBe(true);
    expect(sameStage(null, DEFAULT_STAGE)).toBe(false);
  });
});
