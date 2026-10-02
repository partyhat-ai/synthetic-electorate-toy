import { PerspectiveCamera, Vector3 } from 'three';
import { describe, expect, test } from 'vitest';
import { BASE_SHOT, biasFraming, createFloat, orbitDirection, stageRect, viewOffset } from './camera';

const ASPECT = 200 / 260;

describe('orbitDirection', () => {
  test('azimuth 0 at the horizon looks from the front (+Z)', () => {
    const d = orbitDirection(0, 90);
    expect(d.x).toBeCloseTo(0, 10);
    expect(d.y).toBeCloseTo(0, 10);
    expect(d.z).toBeCloseTo(1, 10);
  });

  test('azimuth 90 looks from +X; polar 0 from overhead', () => {
    expect(orbitDirection(90, 90).x).toBeCloseTo(1, 10);
    expect(orbitDirection(45, 0).y).toBeCloseTo(1, 10);
  });
});

describe('biasFraming', () => {
  test('an identity layout on a target on the axis keeps the shot and needs no lens shift', () => {
    const position = new Vector3(8, 6, 15);
    const target = new Vector3(0, 3, 0);
    const f = biasFraming(position, target, { x: 0, y: 0, zoom: 1 }, 30, ASPECT);
    expect(f.position.distanceTo(position)).toBeCloseTo(0, 10);
    expect(f.target.distanceTo(target)).toBeCloseTo(0, 10);
    expect(f.shift.x).toBeCloseTo(0, 10);
    expect(f.shift.y).toBeCloseTo(0, 10);
  });

  test('zoom backs the camera off along its line', () => {
    const position = new Vector3(8, 6, 15);
    const target = new Vector3(0, 3, 0);
    const f = biasFraming(position, target, { x: 0, y: 0, zoom: 2 }, 30, ASPECT);
    expect(f.position.distanceTo(f.target)).toBeCloseTo(2 * position.distanceTo(target), 8);
  });

  test('the target always lands on the character’s vertical axis', () => {
    const f = biasFraming(new Vector3(...BASE_SHOT.position), new Vector3(...BASE_SHOT.target), { x: 0.1, y: 0.2, zoom: 1 }, 30, ASPECT);
    expect(f.target.x).toBe(0);
    expect(f.target.z).toBe(0);
  });

  test('the lens shift lands the axis point where the unpivoted shot had it', () => {
    const position = new Vector3(...BASE_SHOT.position);
    const target = new Vector3(...BASE_SHOT.target);
    const f = biasFraming(position, target, { x: 0, y: 0, zoom: 1 }, 30, ASPECT);
    // The shot as authored: from `position`, looking at `target` (off the axis).
    const authored = new PerspectiveCamera(30, ASPECT, 0.1, 400);
    authored.position.copy(position);
    authored.lookAt(target);
    authored.updateMatrixWorld();
    const p = f.target.clone().project(authored);
    expect(f.shift.x).not.toBe(0);
    expect(f.shift.x).toBeCloseTo(p.x, 6);
    expect(f.shift.y).toBeCloseTo(p.y, 6);
  });
});

describe('stage box and lens', () => {
  const stage = { right: 300, bottom: 40, width: 200, height: 260 };

  test('stageRect measures from the canvas’s bottom-right', () => {
    expect(stageRect(stage, 1200, 900)).toEqual({ left: 700, top: 600, width: 200, height: 260 });
  });

  test('viewOffset makes the stage the full view inside the canvas', () => {
    const box = stageRect(stage, 1200, 900);
    expect(viewOffset(box, { x: 0, y: 0 }, 1200, 900)).toEqual([200, 260, -700, -600, 1200, 900]);
    expect(viewOffset(box, { x: 0.5, y: -0.5 }, 1200, 900)).toEqual([200, 260, -750, -665, 1200, 900]);
  });
});

describe('createFloat', () => {
  test('restores the camera exactly after the float', () => {
    const camera = new PerspectiveCamera(30, ASPECT, 0.1, 400);
    const target = new Vector3(0, 3, 0);
    camera.position.set(5, 6, 14);
    camera.lookAt(target);
    const before = camera.position.clone();
    const float = createFloat(() => 0.25);
    float.apply(camera, target, 12.5);
    expect(camera.position.distanceTo(before)).toBeGreaterThan(0);
    float.restore(camera, target);
    expect(camera.position.distanceTo(before)).toBe(0);
  });

  test('the float stays a small swing about the target', () => {
    const camera = new PerspectiveCamera(30, ASPECT, 0.1, 400);
    const target = new Vector3(0, 3, 0);
    camera.position.set(5, 6, 14);
    const distance = camera.position.distanceTo(target);
    const float = createFloat(() => 0.5);
    for (const t of [0, 10, 100, 1000]) {
      float.apply(camera, target, t);
      expect(Math.abs(camera.position.distanceTo(target) / distance - 1)).toBeLessThan(0.005);
      float.restore(camera, target);
    }
  });
});
