// The robot's motion: its idle, exaggerated and sped up for the small framed
// robot (the head on a slower clock of its own), and a walk it crossfades into
// while the page is working.
import {
  type AnimationAction,
  type AnimationClip,
  AnimationMixer,
  Interpolant,
  type KeyframeTrack,
  LoopRepeat,
  type Object3D,
  PropertyBinding,
  Quaternion,
  Vector3,
} from 'three';
import type { Character, IdleBone } from './characters';

/** Seconds of crossfade between the idle and the walk. */
export const WALK_FADE = 0.7;

export interface Motion {
  /** Advance by dt seconds: the mixer, then the idle edits on top. */
  update(dt: number): void;
  /** Walk (true) or go back to the idle it walked out of (false). */
  setWalking(on: boolean): void;
  dispose(): void;
}

// three assigns `createInterpolant` per track at runtime (glTF cubic splines
// bring their own), and its type declarations leave it out.
function interpolantOf(track: KeyframeTrack): Interpolant | null {
  const factory: unknown = Reflect.get(track, 'createInterpolant');
  if (typeof factory !== 'function') return null;
  const made: unknown = factory.call(track);
  return made instanceof Interpolant ? made : null;
}

function sample(interpolant: Interpolant, t: number): ArrayLike<number> {
  const values: ArrayLike<number> = interpolant.evaluate(t);
  return values;
}

interface IdleClock {
  readonly spec: IdleBone;
  t: number;
}

interface BoneRef {
  readonly bone: Object3D;
  q: Quaternion | null;
  qi: Interpolant | null;
  p: Vector3 | null;
  pi: Interpolant | null;
  clock: IdleClock | null;
}

export function createMotion(model: Object3D, clips: readonly AnimationClip[], character: Character): Motion {
  const mixer = new AnimationMixer(model);
  const actions = new Map<string, AnimationAction>();
  for (const clip of clips) actions.set(clip.name, mixer.clipAction(clip));

  let active: AnimationAction | null = null;
  let clipName = '';
  // While walking: the idle it walked out of, so the idle edits fade out with
  // that idle's weight instead of landing on the walk.
  let heldIdle: AnimationAction | null = null;
  let walking = false;
  let walkedFrom: string | null = null;

  const idle = actions.get(character.idleClip);
  if (idle) {
    idle.setLoop(LoopRepeat, Number.POSITIVE_INFINITY);
    idle.clampWhenFinished = false;
    idle.reset().setEffectiveWeight(1).setEffectiveTimeScale(1).play();
    active = idle;
    clipName = character.idleClip;
  }

  const idleTarget = (): AnimationAction | null => {
    if (heldIdle) return heldIdle;
    return active && active.loop === LoopRepeat ? active : null;
  };

  // The idle edits work on bones AFTER the mixer, and the mixer skips writes
  // for constant tracks, so an edit left in place would build on itself frame
  // after frame. Every edited bone goes back to the mixer's pose first.
  const saved = new Map<Object3D, { q: Quaternion; p: Vector3 }>();
  const keep = (bone: Object3D) => {
    if (!saved.has(bone)) saved.set(bone, { q: bone.quaternion.clone(), p: bone.position.clone() });
  };
  const restore = () => {
    for (const [bone, v] of saved) {
      bone.quaternion.copy(v.q);
      bone.position.copy(v.p);
    }
    saved.clear();
  };

  // Idle speed: the idle plays this much faster than authored.
  function applyIdleSpeed(): void {
    const target = idleTarget();
    if (target && target.getEffectiveTimeScale() !== character.idleSpeed) target.setEffectiveTimeScale(character.idleSpeed);
  }

  // Idle intensity: each animated bone's travel away from the idle's first
  // keyframe, scaled. Read off the clip's tracks (not the live bones), so it
  // stays right through a crossfade, and weighted by the idle's weight.
  let refAction: AnimationAction | null = null;
  let refs: BoneRef[] = [];
  let clocks: IdleClock[] = [];
  function captureRefs(target: AnimationAction | null): void {
    refAction = target;
    refs = [];
    clocks = [];
    if (!target) return;
    const byBone = new Map<Object3D, BoneRef>();
    const byName = new Map<string, IdleClock>();
    for (const track of target.getClip().tracks) {
      const { nodeName, propertyName } = PropertyBinding.parseTrackName(track.name);
      if (propertyName !== 'quaternion' && propertyName !== 'position') continue;
      const bone = model.getObjectByName(nodeName);
      if (!bone) continue;
      const ref = byBone.get(bone) ?? { bone, q: null, qi: null, p: null, pi: null, clock: null };
      if (propertyName === 'quaternion') {
        ref.q = new Quaternion().fromArray(track.values, 0);
        ref.qi = interpolantOf(track);
      } else {
        ref.p = new Vector3().fromArray(track.values, 0);
        ref.pi = interpolantOf(track);
      }
      const spec = character.idleBones[bone.name];
      if (spec) {
        let clock = byName.get(bone.name);
        if (!clock) {
          clock = { spec, t: target.time };
          byName.set(bone.name, clock);
        }
        ref.clock = clock;
      }
      byBone.set(bone, ref);
    }
    refs = [...byBone.values()];
    clocks = [...byName.values()];
  }

  const sampleQ = new Quaternion();
  const atIdleQ = new Quaternion();
  const deltaQ = new Quaternion();
  const stepQ = new Quaternion();
  const sampleP = new Vector3();
  const stepP = new Vector3();
  function applyIdleIntensity(dt: number): void {
    const target = idleTarget();
    if (target !== refAction) captureRefs(target);
    if (!target) return;
    const w = target.getEffectiveWeight();
    if (w <= 0) return;
    const k = character.idleIntensity;
    const duration = target.getClip().duration || 0;
    if (duration > 0) {
      for (const c of clocks) c.t = (c.t + dt * target.getEffectiveTimeScale() * c.spec.speed) % duration;
    }
    for (const r of refs) {
      const clock = duration > 0 ? r.clock : null;
      const e = ((clock ? k * clock.spec.intensity : k) - 1) * w;
      if (!clock && e === 0) continue;
      const t = clock ? clock.t : target.time;
      keep(r.bone);
      if (r.qi && r.q) {
        sampleQ.fromArray(sample(r.qi, t));
        if (clock) {
          // The bone on its own clock: the step from the idle's time to its clock's.
          atIdleQ.fromArray(sample(r.qi, target.time));
          r.bone.quaternion.multiply(stepQ.identity().slerp(deltaQ.copy(atIdleQ).invert().multiply(sampleQ), w));
        }
        if (e) r.bone.quaternion.multiply(stepQ.identity().slerp(deltaQ.copy(r.q).invert().multiply(sampleQ), e));
      }
      if (r.pi && r.p) {
        sampleP.fromArray(sample(r.pi, t));
        if (clock) r.bone.position.addScaledVector(stepP.fromArray(sample(r.pi, target.time)).negate().add(sampleP), w);
        if (e) r.bone.position.addScaledVector(stepP.copy(sampleP).sub(r.p), e);
      }
    }
  }

  // A crossfade that can reverse halfway: each side fades from the weight it
  // has now, and a clip still fading out is picked back up where it is.
  function blendTo(name: string, fade: number): boolean {
    const next = actions.get(name);
    if (!next || !active || next === active) return false;
    const prev = active;
    const live = next.enabled && next.isRunning() && next.getEffectiveWeight() > 0;
    const from = live ? next.getEffectiveWeight() : 0;
    const out = prev.getEffectiveWeight();
    if (!live) next.reset();
    next.setLoop(LoopRepeat, Number.POSITIVE_INFINITY);
    next.clampWhenFinished = false;
    next.setEffectiveTimeScale(1).setEffectiveWeight(1).play();
    next._scheduleFading(Math.max(0.05, fade * (1 - from)), from, 1);
    prev.stopFading();
    prev._scheduleFading(Math.max(0.05, fade * out), out, 0);
    active = next;
    clipName = name;
    heldIdle = null;
    return true;
  }

  return {
    update(dt) {
      restore();
      applyIdleSpeed();
      mixer.update(dt);
      applyIdleIntensity(dt);
    },
    setWalking(on) {
      const walkName = character.walkClip;
      if (!actions.has(walkName) || on === walking) return;
      if (on) {
        const from = active;
        if (!from || from.loop !== LoopRepeat || clipName === walkName) return;
        walkedFrom = clipName;
        if (!blendTo(walkName, WALK_FADE)) return;
        heldIdle = from;
        walking = true;
        return;
      }
      walking = false;
      if (clipName === walkName && walkedFrom) blendTo(walkedFrom, WALK_FADE);
      walkedFrom = null;
    },
    dispose() {
      restore();
      mixer.stopAllAction();
      mixer.uncacheRoot(model);
      actions.clear();
    },
  };
}
