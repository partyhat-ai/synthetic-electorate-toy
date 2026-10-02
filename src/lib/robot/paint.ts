// The robot's two paints on one loaded model. History is the GLB's own; Rerun
// is a folder of textures on the same UVs plus overrides.json. setPaint swaps
// maps and factors on the loaded materials: no reload, rig and clip untouched.
import {
  type Color,
  LinearSRGBColorSpace,
  type Material,
  MeshStandardMaterial,
  NoColorSpace,
  SRGBColorSpace,
  type Texture,
  TextureLoader,
} from 'three';
import { z } from 'zod';
import { assetUrl } from './assets';
import type { Character, Paint } from './characters';

const Vec3Schema = z.tuple([z.number(), z.number(), z.number()]).rest(z.number());

// One material's scalars, under glTF factor names or short ones.
const OverrideSchema = z
  .object({
    baseColorFactor: Vec3Schema.optional(),
    baseColor: Vec3Schema.optional(),
    emissiveFactor: Vec3Schema.optional(),
    emissive: Vec3Schema.optional(),
    roughnessFactor: z.number().optional(),
    roughness: z.number().optional(),
    metallicFactor: z.number().optional(),
    metalness: z.number().optional(),
    metal: z.number().optional(),
  })
  .transform((o) => ({
    color: o.baseColorFactor ?? o.baseColor,
    emissive: o.emissiveFactor ?? o.emissive,
    roughness: o.roughnessFactor ?? o.roughness,
    metalness: o.metallicFactor ?? o.metalness ?? o.metal,
  }));

/** overrides.json: material name (or 'Armor' for both armour materials) → scalars. */
export const PaintOverridesSchema = z.record(z.string(), OverrideSchema);
export type PaintOverrides = z.infer<typeof PaintOverridesSchema>;
export type PaintOverride = PaintOverrides[string];

/** overrides.json parsed, or no overrides when it is missing or malformed. */
export function parseOverrides(data: unknown): PaintOverrides {
  const result = PaintOverridesSchema.safeParse(data);
  return result.success ? result.data : {};
}

const ARMOR = /^armor_reactor_emission/i;
const JOINTS = /^weathered joints/i;

export type Part = 'armor' | 'joints' | null;

/** Which texture set a material takes, by its name in the GLB. */
export function partOf(materialName: string): Part {
  if (ARMOR.test(materialName)) return 'armor';
  if (JOINTS.test(materialName)) return 'joints';
  return null;
}

/** The override for a material: its own entry, else 'Armor' for armour materials. */
export function overrideFor(overrides: PaintOverrides, materialName: string): PaintOverride | undefined {
  return overrides[materialName] ?? (partOf(materialName) === 'armor' ? overrides.Armor : undefined);
}

interface PaintSet {
  readonly armor: { readonly map: Texture; readonly emissiveMap: Texture; readonly orm: Texture };
  readonly joints: { readonly map: Texture; readonly orm: Texture };
  readonly overrides: PaintOverrides;
}

interface Snapshot {
  readonly map: Texture | null;
  readonly emissiveMap: Texture | null;
  readonly roughnessMap: Texture | null;
  readonly metalnessMap: Texture | null;
  readonly aoMap: Texture | null;
  readonly color: Color;
  readonly emissive: Color;
  readonly roughness: number;
  readonly metalness: number;
}

export interface PaintSwitch {
  /** Note each material's own maps and factors (History), once the model is in. */
  capture(materials: Iterable<Material>): void;
  /** Start fetching Rerun in the background, so the first switch is instant. */
  preload(): void;
  /** Swap to a paint. Resolves once it's on (or once it's clear Rerun can't load). */
  set(paint: Paint): Promise<void>;
  readonly current: Paint;
  dispose(): void;
}

export function createPaintSwitch(character: Character, maxAnisotropy: number): PaintSwitch {
  let current: Paint = 'history';
  let base: Map<MeshStandardMaterial, Snapshot> | null = null;
  let rerun: Promise<PaintSet | null> | null = null;
  const textures: Texture[] = [];

  function load(): Promise<PaintSet | null> {
    if (rerun) return rerun;
    const { dir, version } = character.rerunPaint;
    const url = (file: string) => assetUrl(`${dir}${file}?v=${version}`);
    const loader = new TextureLoader();
    const tex = (file: string, srgb: boolean) =>
      loader.loadAsync(url(file)).then((t) => {
        t.flipY = false; // glTF's convention, as the GLB's own images
        t.colorSpace = srgb ? SRGBColorSpace : NoColorSpace;
        t.anisotropy = Math.min(maxAnisotropy, 8);
        textures.push(t);
        return t;
      });
    const overrides = fetch(url('overrides.json'))
      .then((r): Promise<unknown> => (r.ok ? r.json() : Promise.resolve({})))
      .then(parseOverrides)
      .catch((): PaintOverrides => ({}));
    const pending = Promise.all([
      tex('armor_basecolor.jpg', true),
      tex('armor_emissive.png', true),
      tex('armor_orm.png', false),
      tex('joints_basecolor.png', true),
      tex('joints_orm.png', false),
      overrides,
    ])
      .then(([armorMap, armorEmissive, armorOrm, jointsMap, jointsOrm, parsed]): PaintSet => ({
        armor: { map: armorMap, emissiveMap: armorEmissive, orm: armorOrm },
        joints: { map: jointsMap, orm: jointsOrm },
        overrides: parsed,
      }))
      .catch((err: unknown) => {
        console.warn("[robot] the Rerun paint didn't load; keeping the model's own.", err);
        rerun = null;
        return null;
      });
    rerun = pending;
    return pending;
  }

  function apply(set: PaintSet | null): void {
    if (!base) return;
    for (const [m, b] of base) {
      m.map = b.map;
      m.emissiveMap = b.emissiveMap;
      m.roughnessMap = b.roughnessMap;
      m.metalnessMap = b.metalnessMap;
      m.aoMap = b.aoMap;
      m.color.copy(b.color);
      m.emissive.copy(b.emissive);
      m.roughness = b.roughness;
      m.metalness = b.metalness;
      if (set) {
        const part = partOf(m.name);
        if (part === 'armor') {
          m.map = set.armor.map;
          m.emissiveMap = set.armor.emissiveMap;
        } else if (part === 'joints') {
          m.map = set.joints.map;
        }
        // ORM: R occlusion (where the GLB had one), G roughness, B metal.
        const orm = part === null ? null : set[part].orm;
        if (orm) {
          m.roughnessMap = orm;
          m.metalnessMap = orm;
          if (b.aoMap) m.aoMap = orm;
        }
        const o = overrideFor(set.overrides, m.name);
        if (o?.color) m.color.setRGB(o.color[0], o.color[1], o.color[2], LinearSRGBColorSpace);
        if (o?.emissive) m.emissive.setRGB(o.emissive[0], o.emissive[1], o.emissive[2], LinearSRGBColorSpace);
        if (o?.roughness !== undefined) m.roughness = o.roughness;
        if (o?.metalness !== undefined) m.metalness = o.metalness;
      }
      m.needsUpdate = true;
    }
  }

  return {
    capture(materials) {
      base = new Map();
      for (const m of materials) {
        if (!(m instanceof MeshStandardMaterial)) continue;
        base.set(m, {
          map: m.map,
          emissiveMap: m.emissiveMap,
          roughnessMap: m.roughnessMap,
          metalnessMap: m.metalnessMap,
          aoMap: m.aoMap,
          color: m.color.clone(),
          emissive: m.emissive.clone(),
          roughness: m.roughness,
          metalness: m.metalness,
        });
      }
    },
    preload() {
      void load();
    },
    async set(paint) {
      current = paint;
      if (!base) return; // applied once the model is in
      if (paint === 'history') {
        apply(null);
        return;
      }
      const set = await load();
      if (set && current === paint) apply(set);
    },
    get current() {
      return current;
    },
    dispose() {
      for (const t of textures) t.dispose();
      textures.length = 0;
      base = null;
      rerun = null;
    },
  };
}
