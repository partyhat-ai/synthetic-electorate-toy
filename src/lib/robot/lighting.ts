// The robot's lights: the room environment, a hemisphere fill and three
// directional lights, plus the chest reactor's point light.
import {
  DirectionalLight,
  HemisphereLight,
  PMREMGenerator,
  PointLight,
  type Scene,
  type Texture,
  type WebGLRenderer,
} from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import type { Lighting } from './characters';

/** The reactor's output, 0–1 (the original harness's slider default). */
export const REACTOR_POWER = 0.84;

export interface Rig {
  /** Set every light, the environment and the exposure from the character's values. */
  apply(values: Lighting): void;
  dispose(): void;
}

export function createLighting(renderer: WebGLRenderer, scene: Scene, reactorLight: number): Rig {
  const pmrem = new PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  const environment: Texture = pmrem.fromScene(room, 0.025).texture;
  room.dispose();
  pmrem.dispose();
  scene.environment = environment;

  const hemisphere = new HemisphereLight('#ffffff', '#000000', 1);
  const key = new DirectionalLight('#ffffff', 1);
  key.position.set(-5, 10, 6);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, { left: -7, right: 7, top: 10, bottom: -6, near: 0.1, far: 35 });
  key.shadow.normalBias = 0.03;
  key.shadow.bias = -0.0002;
  const rim = new DirectionalLight('#ffffff', 1);
  rim.position.set(5, 7, -4);
  const fill = new DirectionalLight('#ffffff', 1);
  fill.position.set(4, 3, 5);
  // The chest reactor's glow on the armour around it.
  const reactor = new PointLight('#63f4ff', REACTOR_POWER * reactorLight, 3, 2);
  reactor.position.set(0, 4.35, 0.8);
  scene.add(hemisphere, key, rim, fill, reactor);

  return {
    apply(v) {
      renderer.toneMappingExposure = v.exposure;
      scene.environmentIntensity = v.environment;
      hemisphere.intensity = v.hemi;
      hemisphere.color.set(v.hemiSky);
      hemisphere.groundColor.set(v.hemiGround);
      key.intensity = v.key;
      key.color.set(v.keyColor);
      rim.intensity = v.rim;
      rim.color.set(v.rimColor);
      fill.intensity = v.fill;
      fill.color.set(v.fillColor);
    },
    dispose() {
      key.shadow.dispose();
      environment.dispose();
      scene.remove(hemisphere, key, rim, fill, reactor);
    },
  };
}
