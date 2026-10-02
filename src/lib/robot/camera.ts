// The robot's camera: where it stands for the framed shot, the lens shift that
// puts the robot in its stage box, and the slow float that keeps the shot alive.
import { MathUtils, type PerspectiveCamera, Vector3 } from 'three';
import type { Character } from './characters';
import type { RobotStage } from './messages';

/** Where the robot sits in its box: pushed right / down by a fraction of the view, and a distance multiplier. */
export interface Layout {
  readonly x: number;
  readonly y: number;
  readonly zoom: number;
}

/** The small framed robot's layout, before the character's own zoom. */
export const DOCK_LAYOUT: Layout = { x: 0, y: 0.04, zoom: 0.6 };

/** The hand-set shot the idle and walk are framed from (world units; the model is 6.5 tall). */
export const BASE_SHOT = {
  position: [8.7, 5.8, 15.8],
  target: [-0.35, 3.05, 0],
} as const;

export interface LensShift {
  x: number;
  y: number;
}

export interface Framing {
  readonly position: Vector3;
  readonly target: Vector3;
  /** Lens shift as a fraction of the half-viewport (NDC). */
  readonly shift: LensShift;
}

export interface Box {
  readonly left: number;
  readonly top: number;
  readonly width: number;
  readonly height: number;
}

const UP = new Vector3(0, 1, 0);

/** Azimuth reflected with the stage: a mirrored shot swings the other way. */
export function mirroredAzimuth(azimuth: number, mirrored: boolean): number {
  return mirrored ? -azimuth : azimuth;
}

/** A world-space camera offset reflected with the stage (x only). */
export function mirroredOffset(offset: readonly [number, number, number], mirrored: boolean): [number, number, number] {
  const [x, y, z] = offset;
  return [mirrored ? -x : x, y, z];
}

/** Unit vector from the target to the camera: azimuth about world up from +Z, polar down from overhead (degrees). */
export function orbitDirection(azimuth: number, polar: number): Vector3 {
  const az = MathUtils.degToRad(azimuth);
  const pol = MathUtils.degToRad(polar);
  return new Vector3(Math.sin(pol) * Math.sin(az), Math.cos(pol), Math.sin(pol) * Math.cos(az));
}

/**
 * Orbit about the character's own vertical axis (x = 0, z = 0): the camera
 * slides, same direction and depth, until it looks straight at the axis, and
 * the lens shift moves the image back so that point lands where the framing had it.
 */
export function pivotOnAxis(
  position: Vector3,
  direction: Vector3,
  right: Vector3,
  up: Vector3,
  height: number,
  fov: number,
  aspect: number,
): Framing {
  const pivot = new Vector3(0, height, 0);
  const v = pivot.clone().sub(position);
  const depth = Math.max(1, -v.dot(direction));
  const tangent = Math.tan(MathUtils.degToRad(fov / 2));
  const shift = { x: v.dot(right) / (depth * tangent * aspect), y: v.dot(up) / (depth * tangent) };
  return { position: pivot.clone().addScaledVector(direction, depth), target: pivot, shift };
}

/**
 * Push a shot to where the layout wants the model: the target slides along the
 * camera's right / up by a fraction of the view, and the camera backs off by
 * the layout zoom. { x: 0, y: 0, zoom: 1 } leaves the shot as it was.
 */
export function biasFraming(position: Vector3, target: Vector3, layout: Layout, fov: number, aspect: number): Framing {
  const direction = position.clone().sub(target).normalize();
  const distance = position.distanceTo(target) * layout.zoom;
  const right = new Vector3().crossVectors(UP, direction).normalize();
  const up = new Vector3().crossVectors(direction, right).normalize();
  const tangent = Math.tan(MathUtils.degToRad(fov / 2));
  const biased = target
    .clone()
    .addScaledVector(right, -2 * distance * tangent * aspect * layout.x)
    .addScaledVector(up, 2 * distance * tangent * layout.y);
  return pivotOnAxis(biased.clone().addScaledVector(direction, distance), direction, right, up, target.y, fov, aspect);
}

/** The character's framed shot for a stage of the given aspect, mirrored or not. */
export function computeFraming(character: Character, aspect: number, mirrored: boolean): Framing {
  const layout = { ...DOCK_LAYOUT, zoom: DOCK_LAYOUT.zoom * character.zoom };
  const base = biasFraming(
    new Vector3(...BASE_SHOT.position),
    new Vector3(...BASE_SHOT.target),
    layout,
    character.fov,
    aspect,
  );
  let position = base.position;
  if (character.orbit) {
    const [azimuth, polar] = character.orbit;
    const depth = base.position.distanceTo(base.target);
    position = base.target.clone().addScaledVector(orbitDirection(mirroredAzimuth(azimuth, mirrored), polar), depth);
  }
  const [x, y, z] = mirroredOffset(character.camOffset, mirrored);
  const offset = new Vector3(x, y, z);
  return { position: position.clone().add(offset), target: base.target.clone().add(offset), shift: base.shift };
}

/** The stage's rect in canvas px: `right` / `bottom` measured from the canvas's bottom-right corner. */
export function stageRect(stage: RobotStage, canvasWidth: number, canvasHeight: number): Box {
  return {
    left: canvasWidth - stage.right - stage.width,
    top: canvasHeight - stage.bottom - stage.height,
    width: stage.width,
    height: stage.height,
  };
}

/**
 * setViewOffset arguments that make the stage box the camera's full view and
 * render the whole canvas around it, with the lens shift applied.
 */
export function viewOffset(
  box: Box,
  shift: LensShift,
  canvasWidth: number,
  canvasHeight: number,
): [number, number, number, number, number, number] {
  return [
    box.width,
    box.height,
    -box.left - (shift.x * box.width) / 2,
    -box.top + (shift.y * box.height) / 2,
    canvasWidth,
    canvasHeight,
  ];
}

// The idle float: each axis sums sines with incommensurable periods, so the
// drift never visibly loops. Amplitudes are angles (radians) and a dolly fraction.
const FLOAT = {
  azimuth: [
    { amplitude: 0.013, rate: 0.11 },
    { amplitude: 0.0062, rate: 0.191 },
  ],
  polar: [
    { amplitude: 0.0068, rate: 0.083 },
    { amplitude: 0.0031, rate: 0.149 },
  ],
  dolly: [{ amplitude: 0.0042, rate: 0.067 }],
} as const;

type Wave = readonly { readonly amplitude: number; readonly rate: number }[];

function waveAt(terms: Wave, phases: readonly number[], time: number): number {
  return terms.reduce((total, term, i) => total + term.amplitude * Math.sin(time * term.rate + (phases[i] ?? 0)), 0);
}

/**
 * The float, layered on the camera for one render and taken off after, so it
 * never feeds back into the framing. Phases are random per mount, so two tabs
 * never drift in lockstep.
 */
export function createFloat(random: () => number = Math.random) {
  const phases = (terms: Wave) => terms.map(() => random() * Math.PI * 2);
  const phase = { azimuth: phases(FLOAT.azimuth), polar: phases(FLOAT.polar), dolly: phases(FLOAT.dolly) };
  const basePosition = new Vector3();
  const offset = new Vector3();
  const right = new Vector3();
  return {
    /** Swing the camera about `target` for this frame's render. */
    apply(camera: PerspectiveCamera, target: Vector3, time: number): void {
      basePosition.copy(camera.position);
      offset.subVectors(camera.position, target);
      offset.applyAxisAngle(UP, waveAt(FLOAT.azimuth, phase.azimuth, time));
      right.crossVectors(offset, UP).normalize();
      offset.applyAxisAngle(right, waveAt(FLOAT.polar, phase.polar, time));
      offset.multiplyScalar(1 + waveAt(FLOAT.dolly, phase.dolly, time));
      camera.position.addVectors(target, offset);
      camera.lookAt(target);
      camera.updateMatrixWorld();
    },
    /** Put the camera back where the framing has it. */
    restore(camera: PerspectiveCamera, target: Vector3): void {
      camera.position.copy(basePosition);
      camera.lookAt(target);
    },
  };
}
