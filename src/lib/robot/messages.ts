// Every postMessage between the page (RobotFrame) and the robot's frame
// (/robot). Both ends are same-origin and check `event.source` before parsing;
// anything that doesn't parse is someone else's message and is ignored quietly.
//
// Page → frame
//   robot:stage    { stage: RobotStage | null }  where the robot stands (null: the default box)
//   robot:running  { on }                        draw (true) or stop the render loop (false)
//   robot:walk     { on }                        walk (working) or idle
//   robot:paint    { paint: 'history' | 'rerun' }
//   robot:blast    { color }                     a shot from the chest reactor, in #rrggbb
// Frame → page
//   robot:ready                                  the frame is listening; send the state
//   robot:anchors  { anchors: RobotAnchors | null }  every frame; null while the model loads
import { z } from 'zod';

const finite = z.number();

/**
 * The box the robot is framed into, in CSS px inside the frame: `right` and
 * `bottom` from the frame's bottom-right corner. `mirror` reflects the robot
 * (and the camera's sideways moves) left-right; `yaw` turns it about its
 * vertical axis in degrees, eased toward in the renderer.
 */
export const RobotStageSchema = z.object({
  right: finite,
  bottom: finite,
  width: finite.positive(),
  height: finite.positive(),
  mirror: z.boolean(),
  yaw: finite,
});
export type RobotStage = z.infer<typeof RobotStageSchema>;

/** Where the robot stands on screen, CSS px: its body's centre line and the floor under its feet. */
export const RobotAnchorsSchema = z.object({
  centerX: finite,
  feetY: finite,
});
export type RobotAnchors = z.infer<typeof RobotAnchorsSchema>;

export const PaintSchema = z.enum(['history', 'rerun']);

/** A CSS colour as #rrggbb. */
export const HexColorSchema = z.string().regex(/^#[0-9a-f]{6}$/i);

export const HostMessageSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('robot:stage'), stage: RobotStageSchema.nullable() }),
  z.object({ type: z.literal('robot:running'), on: z.boolean() }),
  z.object({ type: z.literal('robot:walk'), on: z.boolean() }),
  z.object({ type: z.literal('robot:paint'), paint: PaintSchema }),
  z.object({ type: z.literal('robot:blast'), color: HexColorSchema }),
]);
export type HostMessage = z.infer<typeof HostMessageSchema>;

export const FrameMessageSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('robot:ready') }),
  z.object({ type: z.literal('robot:anchors'), anchors: RobotAnchorsSchema.nullable() }),
]);
export type FrameMessage = z.infer<typeof FrameMessageSchema>;

/** A message for the frame, or null for anything else. */
export function parseHostMessage(data: unknown): HostMessage | null {
  const result = HostMessageSchema.safeParse(data);
  return result.success ? result.data : null;
}

/** A message from the frame, or null for anything else. */
export function parseFrameMessage(data: unknown): FrameMessage | null {
  const result = FrameMessageSchema.safeParse(data);
  return result.success ? result.data : null;
}
