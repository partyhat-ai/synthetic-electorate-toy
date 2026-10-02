<script lang="ts">
  // The robot's layer: the frame (RobotFrame) over the page's content,
  // scrolling with it, click-through. The page measures the WhatIf slot and
  // stands the robot in it; once drawn, the robot's anchors nudge its box
  // once, so its feet sit on the slot's floor.
  import { onDestroy, untrack } from 'svelte';
  import type { Paint } from '$lib/robot/characters';
  import type { RobotAnchors, RobotStage } from '$lib/robot/messages';
  import RobotFrame from '$lib/robot/RobotFrame.svelte';
  import { type Nudge, nudgeToSlot, sameStage, stageInSlot, yawForYear } from '$lib/robot/stage';
  import { ELECTION_YEARS } from './geo';

  interface Props {
    /** The WhatIf slot the robot stands in. */
    spot: HTMLElement | null;
    /** A browser tab wide enough to draw the robot. */
    stageMode: boolean;
    /** The time bar is being dragged: the robot holds still. */
    scrubbing: boolean;
    year: number;
    paint: Paint;
    walking: boolean;
    /** Re-measured whenever this resizes (the page's content). */
    observe?: HTMLElement | null;
    /** The robot is drawn. */
    shown?: boolean;
  }
  let { spot, stageMode, scrubbing, year, paint, walking, observe = null, shown = $bindable(false) }: Props = $props();

  let host = $state<HTMLElement | null>(null);
  /** The robot's box, before its turn. */
  let box = $state<RobotStage | null>(null);
  let measureFrame = 0;
  let nudge: Nudge = { x: 0, y: 0 };
  let nudged = false;

  // The robot turns a little with the time bar (yawForYear), eased in the renderer.
  const yawNow = $derived(yawForYear(ELECTION_YEARS.indexOf(year), ELECTION_YEARS.length));
  const stage = $derived(box ? { ...box, yaw: yawNow } : null);

  function measureStage(): void {
    measureFrame = 0;
    // Dragging the time bar: no restaging; it's placed once more on release.
    if (scrubbing && box) return;
    if (!stageMode || !spot) {
      box = null;
      return;
    }
    const r = spot.getBoundingClientRect();
    // The layer ends just under the robot's slot, not at the page's bottom:
    // a taller bubble or chip row then never resizes the robot's frame (which
    // clears its canvas) or shifts the stage's bottom, so the robot holds still.
    const page = host?.parentElement?.getBoundingClientRect();
    if (host && page) {
      const want = `${Math.ceil(r.bottom - page.top + 40)}px`;
      if (host.style.height !== want) host.style.height = want;
    }
    // From the robot's layer's bottom-right, not the window's: the layer
    // scrolls with the page, so scrolling never moves the stage.
    const h = host?.getBoundingClientRect() ?? new DOMRect(0, 0, innerWidth, innerHeight);
    const next = stageInSlot(h, r, nudge, 0);
    if (!sameStage(box, next)) box = next;
  }

  /** Measures on the next frame (once, however often it's asked). */
  export function measureSoon(): void {
    if (!measureFrame) measureFrame = requestAnimationFrame(measureStage);
  }

  $effect(() => {
    void stageMode;
    void spot;
    untrack(measureSoon);
  });
  $effect(() => {
    if (!observe) return;
    const ro = new ResizeObserver(measureSoon);
    ro.observe(observe);
    return () => ro.disconnect();
  });

  function onRobot(anchors: RobotAnchors | null): void {
    const on = !!anchors;
    if (on !== shown) shown = on;
    if (!anchors || nudged || !spot || !box) return;
    const d = nudgeToSlot(spot.getBoundingClientRect(), anchors);
    nudged = true;
    if (Math.abs(d.x) > 3 || Math.abs(d.y) > 3) {
      nudge = { x: nudge.x + d.x, y: nudge.y + d.y };
      measureStage();
    }
  }

  onDestroy(() => cancelAnimationFrame(measureFrame));
</script>

<svelte:window onresize={measureSoon} />

<div class="robot-host" bind:this={host} aria-hidden="true">
  <RobotFrame {stage} visible={stageMode && !!stage} {walking} {paint} {onRobot} />
</div>

<style>
  .robot-host { position: absolute; inset: 0 0 auto 0; height: 100%; z-index: 3; overflow: hidden; pointer-events: none; }
</style>
