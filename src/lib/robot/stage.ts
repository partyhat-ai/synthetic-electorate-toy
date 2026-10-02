// Pure placement math: the robot's box, and the page-side measuring that
// stands it in a slot.
import type { RobotAnchors, RobotStage } from './messages';

/** The box the frame uses until the page sends one. */
export const DEFAULT_STAGE: RobotStage = { right: 10, bottom: 26, width: 200, height: 260 };

/** The robot's size on the page, CSS px. */
export const STAGE_SIZE = { width: 200, height: 260 } as const;

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
 * floor, less any nudge.
 */
export function stageInSlot(host: Rect, slot: Rect, nudge: Nudge): RobotStage {
  return {
    right: Math.round(host.right - (slot.left + slot.width / 2) - STAGE_SIZE.width / 2 - nudge.x),
    bottom: Math.round(host.bottom - slot.bottom - nudge.y),
    width: STAGE_SIZE.width,
    height: STAGE_SIZE.height,
  };
}

/** Pixels the robot must move to be centred on the slot with its feet `floorGap` px above its floor. */
export function nudgeToSlot(slot: Rect, anchors: RobotAnchors, floorGap = 6): Nudge {
  return { x: slot.left + slot.width / 2 - anchors.centerX, y: slot.bottom - floorGap - anchors.feetY };
}

export function sameStage(a: RobotStage | null, b: RobotStage | null): boolean {
  if (a === null || b === null) return a === b;
  return a.right === b.right && a.bottom === b.bottom && a.width === b.width && a.height === b.height;
}
