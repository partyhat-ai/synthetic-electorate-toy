// Pure placement math: the robot's box, its turn with the time bar, and the
// page-side measuring that stands it in a slot.
import type { RobotAnchors, RobotStage } from './messages';

/** The box the frame uses until the page sends one. */
export const DEFAULT_STAGE: RobotStage = { right: 10, bottom: 26, width: 200, height: 260, mirror: false, yaw: 0 };

/** The robot's size on the page, CSS px. */
export const STAGE_SIZE = { width: 200, height: 260 } as const;

/** The robot's resting turn, degrees. */
export const ROBOT_YAW = 40;
/** It turns ±this many degrees from the first election to the last. */
export const YAW_SWAY = 8;
/** How quickly the renderer eases toward a new yaw, per second. */
export const YAW_EASE_RATE = 5;

/**
 * The robot's yaw for the election at `index` of `count` (the time bar),
 * rounded to a tenth of a degree. Out-of-range input keeps the resting yaw.
 */
export function yawForYear(index: number, count: number, base: number = ROBOT_YAW, sway: number = YAW_SWAY): number {
  if (count < 2 || index < 0 || index >= count) return base;
  const fraction = index / (count - 1);
  return Math.round((base + (fraction - 0.5) * 2 * sway) * 10) / 10;
}

/** One frame of the yaw easing: `current` moves toward `target` (radians) by dt seconds' worth. */
export function easeToward(current: number, target: number, dt: number, rate: number = YAW_EASE_RATE): number {
  return current + (target - current) * Math.min(1, Math.max(0, dt) * rate);
}

export interface Rect {
  readonly left: number;
  readonly top: number;
  readonly right: number;
  readonly bottom: number;
  readonly width: number;
}

export interface Nudge {
  readonly x: number;
  readonly y: number;
}

/**
 * The stage that stands the robot in `slot`, measured from the frame's host
 * element (`host`, the frame fills it): centred on the slot, feet on its
 * floor, less any nudge, facing into the page (mirrored).
 */
export function stageInSlot(host: Rect, slot: Rect, nudge: Nudge, yaw: number): RobotStage {
  return {
    right: Math.round(host.right - (slot.left + slot.width / 2) - STAGE_SIZE.width / 2 - nudge.x),
    bottom: Math.round(host.bottom - slot.bottom - nudge.y),
    width: STAGE_SIZE.width,
    height: STAGE_SIZE.height,
    mirror: true,
    yaw,
  };
}

/** Pixels the robot must move to be centred on the slot with its feet `floorGap` px above its floor. */
export function nudgeToSlot(slot: Rect, anchors: RobotAnchors, floorGap = 6): Nudge {
  return { x: slot.left + slot.width / 2 - anchors.centerX, y: slot.bottom - floorGap - anchors.feetY };
}

export function sameStage(a: RobotStage | null, b: RobotStage | null): boolean {
  if (a === null || b === null) return a === b;
  return (
    a.right === b.right &&
    a.bottom === b.bottom &&
    a.width === b.width &&
    a.height === b.height &&
    a.mirror === b.mirror &&
    a.yaw === b.yaw
  );
}
