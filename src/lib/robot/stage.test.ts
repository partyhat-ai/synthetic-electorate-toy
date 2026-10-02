import { describe, expect, test } from 'vitest';
import {
  boxMoved,
  DEFAULT_STAGE,
  dragTurn,
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

describe('dragTurn', () => {
  test('a press that hasn’t moved 4px is still a tap', () => {
    expect(dragTurn(0, false)).toBeNull();
    expect(dragTurn(3, false)).toBeNull();
    expect(dragTurn(-3.9, false)).toBeNull();
  });
  test('past 4px it turns 0.6° per px, to the whole degree', () => {
    expect(dragTurn(4, false)).toBe(2);
    expect(dragTurn(-10, false)).toBe(-6);
    expect(dragTurn(101, false)).toBe(61);
  });
  test('once a drag, back under 4px still turns (and back to zero is zero)', () => {
    expect(dragTurn(2, true)).toBe(1);
    expect(dragTurn(0, true)).toBe(0);
    expect(Object.is(dragTurn(-0.4, true), 0)).toBe(true);
  });
  test('held to half a turn either way', () => {
    expect(dragTurn(1000, true)).toBe(180);
    expect(dragTurn(-1000, true)).toBe(-180);
  });
  test('let go, the renderer eases the turn back to rest', () => {
    const rest = (ROBOT_YAW * Math.PI) / 180;
    let yaw = ((ROBOT_YAW + (dragTurn(300, true) ?? 0)) * Math.PI) / 180;
    const start = Math.abs(yaw - rest);
    for (let i = 0; i < 15; i++) yaw = easeToward(yaw, rest, 1 / 60);
    // A quarter second in, most of the way back, never past rest.
    expect(Math.abs(yaw - rest)).toBeLessThan(start * 0.3);
    expect(yaw).toBeGreaterThan(rest);
    for (let i = 0; i < 240; i++) yaw = easeToward(yaw, rest, 1 / 60);
    expect(yaw).toBeCloseTo(rest, 6);
  });
});

describe('boxMoved', () => {
  test('a turn alone is not a move', () => {
    expect(boxMoved(DEFAULT_STAGE, { ...DEFAULT_STAGE, yaw: 123 })).toBe(false);
    expect(boxMoved(DEFAULT_STAGE, { ...DEFAULT_STAGE })).toBe(false);
  });
  test.each(['right', 'bottom', 'width', 'height'] as const)('a changed %s is', (k) => {
    expect(boxMoved(DEFAULT_STAGE, { ...DEFAULT_STAGE, [k]: DEFAULT_STAGE[k] + 1 })).toBe(true);
  });
  test('a flip is', () => {
    expect(boxMoved(DEFAULT_STAGE, { ...DEFAULT_STAGE, mirror: !DEFAULT_STAGE.mirror })).toBe(true);
  });
});
