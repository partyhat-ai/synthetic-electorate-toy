// The narrator: ChatPro (character atlas-09) in its Americana model. The values
// are the ones the original harness used for the small framed robot, baked in.
// Paths are relative to ASSET_BASE (assets.ts).

/** Flat lighting values over the scene. Colours are CSS hex strings. */
export interface Lighting {
  readonly exposure: number;
  readonly environment: number;
  readonly hemi: number;
  readonly hemiSky: string;
  readonly hemiGround: string;
  readonly key: number;
  readonly keyColor: string;
  readonly rim: number;
  readonly rimColor: string;
  readonly fill: number;
  readonly fillColor: string;
}

/** A bone that plays the idle on its own clock: multipliers on the idle's intensity and speed. */
export interface IdleBone {
  readonly intensity: number;
  readonly speed: number;
}

export interface Character {
  readonly id: string;
  /** The Americana GLB: rig, clips and paint. */
  readonly model: string;
  /** Lighting over the scene: the original harness look. */
  readonly lighting: Lighting;
  /** Every model is scaled to this height (scene units) and stood on the origin. */
  readonly height: number;
  /** Multiplier on the layout's camera distance. */
  readonly zoom: number;
  /** Vertical field of view, degrees. */
  readonly fov: number;
  /** Camera moved this far in world space, target with it (a truck, not a swing). Mirrored in x with the stage. */
  readonly camOffset: readonly [number, number, number];
  /** [azimuth, polar] degrees to swing the camera round to, or null to keep the fitted direction. */
  readonly orbit: readonly [number, number] | null;
  readonly idleClip: string;
  readonly walkClip: string;
  /** How much of the idle's motion plays (1 = as authored). */
  readonly idleIntensity: number;
  /** How fast the idle plays (1 = as authored). */
  readonly idleSpeed: number;
  readonly idleBones: Readonly<Record<string, IdleBone>>;
  /** The chest reactor's point light, before the power factor. */
  readonly reactorLight: number;
}

export const ATLAS: Character = {
  id: 'atlas-09',
  model: 'models/atlas-09-americana.glb?v=2',
  lighting: {
    exposure: 1.18,
    environment: 0.45,
    hemi: 1.3,
    hemiSky: '#dfe6de',
    hemiGround: '#303926',
    key: 4.5,
    keyColor: '#fff2d9',
    rim: 3.2,
    rimColor: '#a3cad2',
    fill: 0.8,
    fillColor: '#d7e1b8',
  },
  height: 6.5,
  zoom: 1.71,
  fov: 29.5,
  camOffset: [3.3, 0, 0],
  orbit: null,
  idleClip: 'Sentinel',
  walkClip: 'Walk',
  idleIntensity: 8.4,
  idleSpeed: 2.1,
  // The head at a third of the body's travel and pace.
  idleBones: { head: { intensity: 1 / 3, speed: 1 / 3 } },
  reactorLight: 3,
};
