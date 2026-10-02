// The robot's scene, drawn into a transparent canvas that fills the frame.
// The robot is framed into a stage box inside it (the page decides where);
// the canvas stays full-size so the box can sit anywhere in the frame.
import {
  ACESFilmicToneMapping,
  Box3,
  type BufferGeometry,
  Group,
  type Material,
  MathUtils,
  Mesh,
  MeshStandardMaterial,
  type Object3D,
  PCFShadowMap,
  PerspectiveCamera,
  Scene,
  Texture,
  Vector2,
  Vector3,
  WebGLRenderer,
} from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { assetUrl } from './assets';
import { createChestBlast } from './blast';
import { computeFraming, createFloat, type LensShift, stageRect, viewOffset } from './camera';
import { ATLAS, type Character, type Paint } from './characters';
import { createLighting, REACTOR_POWER } from './lighting';
import type { RobotAnchors, RobotStage } from './messages';
import { createMotion, type Motion } from './motion';
import { createPaintSwitch } from './paint';
import { easeToward } from './stage';

export interface MountOptions {
  readonly canvas: HTMLCanvasElement;
  /** The current stage box, read every frame. */
  readonly stage: () => RobotStage;
  readonly character?: Character;
}

export interface RobotApp {
  /** The stage changed: re-fit the renderer and lens at the start of the next frame. */
  restage(): void;
  /** Start or stop the render loop. Nothing draws or animates while stopped. */
  setRunning(on: boolean): void;
  setWalking(on: boolean): void;
  setPaint(paint: Paint): void;
  /**
   * A shot out of the chest reactor in `color` (#rrggbb), the way the robot
   * faces: mostly across the screen, a little toward the viewer, so it stays
   * in the picture. False before the model loads.
   */
  blast(color: string): boolean;
  /** Called every frame with the robot's anchors in canvas px, or null while it loads. */
  onAnchors(listener: (anchors: RobotAnchors | null) => void): () => void;
  dispose(): void;
}

function materialsOf(mesh: Mesh): Material[] {
  return Array.isArray(mesh.material) ? mesh.material : [mesh.material];
}

function disposeModel(root: Object3D): void {
  const geometries = new Set<BufferGeometry>();
  const materials = new Set<Material>();
  const textures = new Set<Texture>();
  root.traverse((o) => {
    if (!(o instanceof Mesh)) return;
    geometries.add(o.geometry);
    for (const m of materialsOf(o)) materials.add(m);
  });
  for (const m of materials) {
    for (const value of Object.values(m)) if (value instanceof Texture) textures.add(value);
    m.dispose();
  }
  for (const t of textures) t.dispose();
  for (const g of geometries) g.dispose();
}

export function mountRobot({ canvas, stage, character = ATLAS }: MountOptions): RobotApp {
  const width = () => canvas.clientWidth || innerWidth;
  const height = () => canvas.clientHeight || innerHeight;

  const renderer = new WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
  renderer.setSize(width(), height(), false);
  renderer.setClearColor(0x000000, 0);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFShadowMap;
  renderer.toneMapping = ACESFilmicToneMapping;

  // No background and no fog: the page shows through around the robot.
  const scene = new Scene();
  const initial = stage();
  const camera = new PerspectiveCamera(character.fov, initial.width / initial.height, 0.1, 400);
  const lights = createLighting(renderer, scene, character.reactorLight);
  const paint = createPaintSwitch(character, renderer.capabilities.getMaxAnisotropy());
  lights.apply(character.lighting[paint.current]);

  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  composer.addPass(new OutputPass());

  // The robot's turntable: mirrored and turned with the stage.
  const hero = new Group();
  scene.add(hero);
  // Shots from the chest reactor (blast()), and the robot rocking back from the last one.
  const chestBlast = createChestBlast(scene);
  const recoilDir = new Vector3();
  let recoilSize = 0;

  const target = new Vector3();
  const lens: LensShift = { x: 0, y: 0 };
  const float = createFloat();
  let model: Object3D | null = null;
  let chestBone: Object3D | null = null;
  let motion: Motion | null = null;
  let modelHeight = 0;
  let emitters: { mat: MeshStandardMaterial; intensity: number }[] = [];
  let walkWanted = false;
  let restagePending = false;
  let disposed = false;

  function applyLens(): void {
    camera.setViewOffset(...viewOffset(stageRect(stage(), width(), height()), lens, width(), height()));
  }

  function resetCamera(): void {
    const framing = computeFraming(character, camera.aspect, stage().mirror);
    target.copy(framing.target);
    camera.position.copy(framing.position);
    lens.x = framing.shift.x;
    lens.y = framing.shift.y;
    applyLens();
    camera.lookAt(target);
  }

  // The renderer at the canvas's size and the lens re-applied. setSize clears
  // the canvas, so it's skipped when the size hasn't changed.
  const sizeNow = new Vector2();
  function fitRenderer(): void {
    const w = width();
    const h = height();
    renderer.getSize(sizeNow);
    if (sizeNow.x !== w || sizeNow.y !== h) {
      renderer.setSize(w, h, false);
      composer.setSize(w, h);
    }
    const s = stage();
    camera.aspect = s.width / s.height;
    applyLens();
  }

  const anchorListeners = new Set<(anchors: RobotAnchors | null) => void>();
  const projected = new Vector3();
  const toScreen = (x: number, y: number, z: number) => {
    projected.set(x, y, z).project(camera);
    return { x: ((projected.x + 1) / 2) * width(), y: ((1 - projected.y) / 2) * height() };
  };
  // The body's centre line (head over feet, on the model's own vertical axis)
  // and the floor under it, from the camera as rendered, float included.
  function emitAnchors(): void {
    if (anchorListeners.size === 0) return;
    let anchors: RobotAnchors | null = null;
    if (model) {
      const head = toScreen(0, modelHeight, 0);
      const feet = toScreen(0, 0, 0);
      anchors = { centerX: (head.x + feet.x) / 2, feetY: feet.y };
    }
    for (const listener of anchorListeners) listener(anchors);
  }

  async function load(): Promise<void> {
    const gltf = await new GLTFLoader().loadAsync(assetUrl(character.model));
    if (disposed) {
      disposeModel(gltf.scene);
      return;
    }
    const root = gltf.scene;
    // Scaled to the character's height, centred on the vertical axis, feet on y = 0.
    const box = new Box3().setFromObject(root);
    const size = box.getSize(new Vector3());
    const scale = character.height / size.y;
    root.scale.setScalar(scale);
    const center = box.getCenter(new Vector3());
    root.position.set(-center.x * scale, -box.min.y * scale, -center.z * scale);
    hero.add(root);
    modelHeight = size.y * scale;

    const materials = new Set<Material>();
    const maxAnisotropy = Math.min(renderer.capabilities.getMaxAnisotropy(), 8);
    root.traverse((o) => {
      if (!(o instanceof Mesh)) return;
      o.castShadow = true;
      o.receiveShadow = true;
      o.frustumCulled = false;
      for (const m of materialsOf(o)) materials.add(m);
    });
    emitters = [];
    for (const m of materials) {
      if (!(m instanceof MeshStandardMaterial)) continue;
      if (m.map) m.map.anisotropy = maxAnisotropy;
      const name = m.name.toLowerCase();
      if (name.includes('reactor') || name.includes('emission')) emitters.push({ mat: m, intensity: m.emissiveIntensity || 1 });
    }
    paint.capture(materials);
    if (paint.current === 'history') paint.preload();
    else void paint.set(paint.current);

    model = root;
    chestBone = root.getObjectByName('chest') ?? null;
    motion = createMotion(root, gltf.animations, character);
    if (walkWanted) motion.setWalking(true);
    resetCamera();
  }

  let last = performance.now();
  let time = 0;
  function frame(now: number): void {
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now;
    time += dt;
    if (restagePending) {
      restagePending = false;
      fitRenderer();
    }
    const s = stage();
    const mirror = s.mirror ? -1 : 1;
    if (hero.scale.x !== mirror) {
      hero.scale.x = mirror;
      if (model) resetCamera();
    }
    hero.rotation.y = easeToward(hero.rotation.y, MathUtils.degToRad(s.yaw), dt);
    motion?.update(dt);
    chestBlast.update(dt);
    hero.position.copy(recoilDir).multiplyScalar(-chestBlast.recoil() * recoilSize * 0.025);
    const glow = REACTOR_POWER * (1 + Math.sin(time * 2.3) * 0.06);
    for (const { mat, intensity } of emitters) mat.emissiveIntensity = intensity * glow;
    camera.lookAt(target);
    float.apply(camera, target, time);
    emitAnchors();
    composer.render();
    float.restore(camera, target);
  }

  resetCamera();
  fitRenderer();
  renderer.setAnimationLoop(frame);
  load().catch((err: unknown) => {
    if (!disposed) console.error('[robot] the model did not load', err);
  });

  // With a stage the framing is the stage's, so a resize only re-fits the lens.
  const onResize = () => fitRenderer();
  window.addEventListener('resize', onResize);
  const resizeObserver = new ResizeObserver(onResize);
  resizeObserver.observe(canvas);

  return {
    restage() {
      restagePending = true;
    },
    setRunning(on) {
      if (on) last = performance.now();
      renderer.setAnimationLoop(on ? frame : null);
    },
    setWalking(on) {
      walkWanted = on;
      motion?.setWalking(on);
    },
    setPaint(next) {
      lights.apply(character.lighting[next]);
      void paint.set(next);
    },
    blast(color) {
      if (!model || !chestBone) return false;
      model.updateMatrixWorld(true);
      const box = new Box3().setFromObject(model);
      const size = box.max.y - box.min.y || 10;
      const fwd = new Vector3(0, 0, 1).transformDirection(model.matrixWorld);
      fwd.y = 0;
      fwd.normalize();
      const view = camera.getWorldDirection(new Vector3());
      const direction = fwd.clone().addScaledVector(view, -fwd.dot(view) * 0.75).normalize();
      // The chest bone sits below the reactor: the shot leaves 0.17 robot heights up.
      const origin = chestBone.getWorldPosition(new Vector3()).addScaledVector(fwd, size * 0.07);
      origin.y += size * 0.17;
      chestBlast.fire({ origin, direction, size, color });
      recoilDir.copy(direction);
      recoilSize = size;
      return true;
    },
    onAnchors(listener) {
      anchorListeners.add(listener);
      return () => anchorListeners.delete(listener);
    },
    dispose() {
      disposed = true;
      renderer.setAnimationLoop(null);
      window.removeEventListener('resize', onResize);
      resizeObserver.disconnect();
      anchorListeners.clear();
      chestBlast.dispose();
      motion?.dispose();
      if (model) disposeModel(model);
      paint.dispose();
      lights.dispose();
      composer.dispose();
      renderer.dispose();
    },
  };
}
