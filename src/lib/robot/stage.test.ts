import { describe, expect, test } from 'vitest';
import {
  DEFAULT_STAGE,
  easeToward,
  nudgeToSlot,
  ROBOT_YAW,
  sameStage,
  stageInSlot,
  YAW_SWAY,
  yawForYear,
} from './stage';

const rect = (left: number, top: number, width: number, height: number) => ({
  left,
  top,
  width,
  right: left + width,
  bottom: top + height,
});

describe('yawForYear', () => {
  test('the first and last elections turn the full sway either side of the resting yaw', () => {
    expect(yawForYear(0, 60)).toBe(ROBOT_YAW - YAW_SWAY);
    expect(yawForYear(59, 60)).toBe(ROBOT_YAW + YAW_SWAY);
  });

  test('the middle of the time bar is the resting yaw', () => {
    expect(yawForYear(2, 5)).toBe(40);
  });

  test('rounds to a tenth of a degree', () => {
    // 40 + (1/58 - 0.5) * 16 = 32.2758…
    expect(yawForYear(1, 59)).toBe(32.3);
  });

  test('an unknown year keeps the resting yaw', () => {
    expect(yawForYear(-1, 60)).toBe(ROBOT_YAW);
    expect(yawForYear(60, 60)).toBe(ROBOT_YAW);
    expect(yawForYear(0, 1)).toBe(ROBOT_YAW);
  });
});

describe('easeToward', () => {
  test('moves a fifth of the way per 1/25 s at the default rate', () => {
    expect(easeToward(0, 1, 0.04)).toBeCloseTo(0.2, 10);
  });

  test('never overshoots on a long frame', () => {
    expect(easeToward(0, 1, 0.5)).toBe(1);
  });

  test('converges on the target', () => {
    let yaw = 0;
    for (let i = 0; i < 120; i++) yaw = easeToward(yaw, 0.7, 1 / 60);
    expect(yaw).toBeCloseTo(0.7, 4);
  });

  test('a zero or negative frame leaves it where it is', () => {
    expect(easeToward(0.3, 1, 0)).toBe(0.3);
    expect(easeToward(0.3, 1, -1)).toBe(0.3);
  });
});

describe('stageInSlot', () => {
  test('centres the 200px box on the slot with its floor on the slot’s bottom', () => {
    const host = rect(0, 0, 1200, 900);
    const slot = rect(100, 500, 300, 200); // centre x 250, bottom 700
    const s = stageInSlot(host, slot, { x: 0, y: 0 }, 40);
    expect(s).toEqual({ right: 1200 - 250 - 100, bottom: 200, width: 200, height: 260, mirror: true, yaw: 40 });
  });

  test('a nudge moves the box right and down', () => {
    const host = rect(0, 0, 1200, 900);
    const slot = rect(100, 500, 300, 200);
    const s = stageInSlot(host, slot, { x: 12, y: -5 }, 40);
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
    expect(sameStage(DEFAULT_STAGE, { ...DEFAULT_STAGE, yaw: 1 })).toBe(false);
    expect(sameStage(null, null)).toBe(true);
    expect(sameStage(null, DEFAULT_STAGE)).toBe(false);
  });
});
