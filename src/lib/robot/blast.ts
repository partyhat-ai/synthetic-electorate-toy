// Shots from the robot's chest reactor, on demand (a tap on the robot): one
// streamlined bolt in the shot's colour inside a soft sheath of the same
// shape, a flash and a light at the chest as it leaves, and a small recoil of
// the whole robot. Sizes are in robot heights, so it fires to its own scale.
import {
  AdditiveBlending,
  Color,
  DoubleSide,
  Group,
  IcosahedronGeometry,
  LatheGeometry,
  Mesh,
  MeshBasicMaterial,
  PointLight,
  type Scene,
  ShaderMaterial,
  Vector2,
  Vector3,
} from 'three';

/** Seconds a shot lives; it fades over the last FADE_S. */
export const SHOT_LIFE_S = 1.6;
const FADE_S = 0.25;
/** The muzzle flash's burst, seconds. */
export const FLASH_S = 0.22;
/** The shot stretches from compressed to full length over this, seconds. */
const STRETCH_S = 0.1;
/** The recoil eases out at this rate, per second (1 → 0 in 0.2s). */
const RECOIL_RATE = 5;

/** The bolt's radius at `t` along it (0 the tail's point, 1 the nose), as a fraction of its widest. */
export function boltProfile(t: number): number {
  return Math.sin(Math.PI * t ** 1.6) ** 0.8;
}

/** How far a shot fired at `speed` has gone after `t` seconds: fast off the chest, easing a touch. */
export function shotTravel(speed: number, t: number): number {
  return speed * (t - 0.08 * t * t);
}

/** A shot's opacity factor at `t`: whole until the last FADE_S of its life. */
export function shotFade(t: number, life: number = SHOT_LIFE_S): number {
  return Math.max(0, Math.min(1, (life - t) / FADE_S));
}

/** The recoil left after `dt` seconds from `kick` (0..1). */
export function recoilAfter(kick: number, dt: number): number {
  return Math.max(0, kick - dt * RECOIL_RATE);
}

/** A streamlined bolt along +Y: a rounded nose tapering to a point at the tail. */
function boltGeometry(radius: number, length: number): LatheGeometry {
  const pts: Vector2[] = [];
  for (let i = 0; i <= 24; i++) {
    const t = i / 24;
    pts.push(new Vector2(Math.max(radius * boltProfile(t), 1e-4), (t - 0.62) * length));
  }
  return new LatheGeometry(pts, 20);
}

/**
 * The muzzle flash's material: additive, in the shot's colour, and faded out
 * through the half of the sphere farther from the camera (measured from its
 * centre in view space), so where it sinks into the chest it dissolves
 * instead of being cut by the robot's geometry.
 */
function flashMaterial(color: string, radius: number): ShaderMaterial {
  return new ShaderMaterial({
    uniforms: { uColor: { value: new Color(color) }, uOpacity: { value: 1 }, uRadius: { value: radius } },
    vertexShader: `
      uniform float uRadius;
      varying float vDepth;
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        vec4 centre = modelViewMatrix * vec4(0.0, 0.0, 0.0, 1.0);
        float r = uRadius * length((modelViewMatrix * vec4(1.0, 0.0, 0.0, 0.0)).xyz);
        vDepth = (mv.z - centre.z) / r;   // +1 nearest the camera, -1 farthest
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: `
      uniform vec3 uColor;
      uniform float uOpacity;
      varying float vDepth;
      void main() {
        gl_FragColor = vec4(uColor, uOpacity * smoothstep(-0.05, 0.6, vDepth));
      }`,
    transparent: true,
    blending: AdditiveBlending,
    depthWrite: false,
    side: DoubleSide,
  });
}

const glowMaterial = (color: string, opacity: number) =>
  new MeshBasicMaterial({ color, transparent: true, opacity, blending: AdditiveBlending, depthWrite: false });

interface Shot {
  readonly shot: Group;
  readonly parts: readonly { readonly mesh: Mesh<LatheGeometry, MeshBasicMaterial>; readonly opacity: number }[];
  readonly flash: Mesh<IcosahedronGeometry, ShaderMaterial>;
  readonly light: PointLight;
  readonly origin: Vector3;
  readonly dir: Vector3;
  readonly speed: number;
  t: number;
}

export interface FireOptions {
  /** World space. */
  readonly origin: Vector3;
  readonly direction: Vector3;
  /** The robot's height in world units. */
  readonly size: number;
  /** #rrggbb. */
  readonly color: string;
}

export interface ChestBlast {
  fire(options: FireOptions): void;
  /** Advance every shot by dt seconds; whether any is still flying. */
  update(dt: number): boolean;
  /** The recoil (1 just after firing, easing to 0), for the robot to rock back by. */
  recoil(): number;
  dispose(): void;
}

export function createChestBlast(scene: Scene): ChestBlast {
  const group = new Group();
  group.name = 'Chest blasts';
  scene.add(group);
  const up = new Vector3(0, 1, 0);
  const shots: Shot[] = [];
  let kick = 0;

  function remove(s: Shot): void {
    group.remove(s.shot, s.flash, s.light);
    for (const { mesh } of s.parts) {
      mesh.geometry.dispose();
      mesh.material.dispose();
    }
    s.flash.geometry.dispose();
    s.flash.material.dispose();
    s.light.dispose();
  }

  return {
    fire({ origin, direction, size, color }) {
      const r = size * 0.03;
      const dir = direction.clone().normalize();
      const shot = new Group();
      // The bolt and its sheath: one shape, the sheath wider and longer and fainter.
      const parts = [
        { mesh: new Mesh(boltGeometry(r * 1.3, r * 11), glowMaterial(color, 0.9)), opacity: 0.9 },
        { mesh: new Mesh(boltGeometry(r * 2.2, r * 13), glowMaterial(color, 0.3)), opacity: 0.3 },
      ];
      for (const { mesh } of parts) shot.add(mesh);
      shot.quaternion.setFromUnitVectors(up, dir);
      shot.position.copy(origin);
      const flash = new Mesh(new IcosahedronGeometry(r * 1.5, 2), flashMaterial(color, r * 1.5));
      flash.position.copy(origin);
      const light = new PointLight(color, 0, size * 1.2);
      light.position.copy(origin);
      group.add(shot, flash, light);
      shots.push({ shot, parts, flash, light, origin: origin.clone(), dir, speed: size * 4.5, t: 0 });
      kick = 1;
    },
    update(dt) {
      kick = recoilAfter(kick, dt);
      for (let i = shots.length - 1; i >= 0; i--) {
        const s = shots[i];
        if (!s) continue;
        s.t += dt;
        s.shot.position.copy(s.origin).addScaledVector(s.dir, shotTravel(s.speed, s.t));
        // It leaves the chest compressed and stretches to full length.
        s.shot.scale.set(1, 0.55 + 0.45 * Math.min(1, s.t / STRETCH_S), 1);
        const fade = shotFade(s.t);
        for (const { mesh, opacity } of s.parts) mesh.material.opacity = opacity * fade;
        // The muzzle flash: a burst at the chest.
        const f = Math.min(1, s.t / FLASH_S);
        s.flash.visible = f < 1;
        s.flash.scale.setScalar(1 + f * 1.6);
        const uOpacity = s.flash.material.uniforms.uOpacity;
        if (uOpacity) uOpacity.value = 1 - f;
        s.light.intensity = 30 * Math.max(0, 1 - s.t / 0.3);
        s.light.position.copy(s.shot.position);
        if (s.t >= SHOT_LIFE_S) {
          remove(s);
          shots.splice(i, 1);
        }
      }
      return shots.length > 0;
    },
    recoil: () => kick * kick,
    dispose() {
      for (const s of shots) remove(s);
      shots.length = 0;
      scene.remove(group);
    },
  };
}
