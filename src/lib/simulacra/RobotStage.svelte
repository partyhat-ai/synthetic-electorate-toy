<script lang="ts" module>
  import type { Still } from './whatif';

  // Stills of the robot, one per paint, rendered from this page (paint,
  // lighting, 40° yaw, framing): shown in the slot the moment the page loads
  // and faded out when the live robot draws. dx/db/w: CSS px from the slot's
  // bottom-centre (see WhatIf `still`). Re-shoot if the framing or look changes.
  export const STILLS: Readonly<Record<'history' | 'rerun', Still>> = {
    history: { src: '/simulacra/chatpro-history.png?v=1', dx: -79, db: -11, w: 153.2 },
    rerun: { src: '/simulacra/chatpro-rerun.png?v=1', dx: -79, db: -11, w: 153.2 },
  };
</script>

<script lang="ts">
  // The robot's layer: the frame (RobotFrame) over the page's content,
  // scrolling with it, click-through. The page measures the WhatIf slot and
  // stands the robot in it; once drawn, the robot's anchors nudge its box
  // once, so its feet sit on the slot's floor. Until then (and SETTLE_MS
  // after the nudge) the layer stays invisible over the still, so its first
  // frames, drawn before the nudge, never show; then one cross-fade.
  //
  // Dragged across, the robot turns with the pointer and, let go, eases back;
  // tapped (pressed and let go without turning it), it calls `ontap`, and the
  // page fires its chest reactor with `blast`.
  import { onDestroy, untrack } from 'svelte';
  import type { Paint } from '$lib/robot/characters';
  import type { RobotAnchors, RobotStage } from '$lib/robot/messages';
  import RobotFrame from '$lib/robot/RobotFrame.svelte';
  import { dragTurn, easeToward, type Nudge, nudgeToSlot, ROBOT_YAW, sameStage, stageInSlot, YAW_EASE_RATE, yawForYear } from '$lib/robot/stage';
  import { ELECTION_YEARS } from './geo';

  interface Props {
    /** The WhatIf slot the robot stands in. */
    spot: HTMLElement | null;
    /** The time bar is being dragged: the robot holds still. */
    scrubbing: boolean;
    year: number;
    paint: Paint;
    walking: boolean;
    /** Re-measured whenever this resizes (the page's content). */
    observe?: HTMLElement | null;
    /** The robot is drawn, nudged and settled. */
    shown?: boolean;
    /** The robot was tapped (not dragged). */
    ontap?: () => void;
    /** Its resting turn, degrees, which the time bar sways around (stage.ts ROBOT_YAW). */
    restYaw?: number;
  }
  let { spot, scrubbing, year, paint, walking, observe = null, shown = $bindable(false), ontap, restYaw = ROBOT_YAW }: Props = $props();

  const SETTLE_MS = 150;
  let host = $state<HTMLElement | null>(null);
  let robotShown = $state(false);
  let robotReady = $state(false);
  let readyTimer: ReturnType<typeof setTimeout> | undefined;
  /** The robot's box, before its turn. */
  let box = $state<RobotStage | null>(null);
  let measureFrame = 0;
  let nudge: Nudge = { x: 0, y: 0 };
  let nudged = false;
  let frame = $state<ReturnType<typeof RobotFrame> | null>(null);
  /** The turn from a drag across the robot, degrees; 0 when let go. */
  let dragYaw = $state(0);
  let dragFrom: number | null = null;
  let dragged = false;
  /** The turn a new drag starts from (mid-way through a snap back). */
  let dragBase = 0;
  // Let go, the robot eases back three times slower than it follows the
  // time bar: the page eases the drag's turn to 0 at a third of the
  // renderer's rate, and the renderer follows that.
  const SNAP_RATE = YAW_EASE_RATE / 3;
  let snapFrame = 0;
  function snapBack(): void {
    cancelAnimationFrame(snapFrame);
    let last = performance.now();
    const step = (now: number) => {
      dragYaw = easeToward(dragYaw, 0, (now - last) / 1000, SNAP_RATE);
      last = now;
      if (Math.abs(dragYaw) < 0.05) {
        dragYaw = 0;
        snapFrame = 0;
        return;
      }
      snapFrame = requestAnimationFrame(step);
    };
    snapFrame = requestAnimationFrame(step);
  }

  // The robot turns a little with the time bar (yawForYear) and by hand,
  // eased in the renderer.
  const yawNow = $derived(yawForYear(ELECTION_YEARS.indexOf(year), ELECTION_YEARS.length, restYaw) + dragYaw);
  const stage = $derived(box ? { ...box, yaw: yawNow } : null);

  /** A shot from the robot's chest reactor in `color` (#rrggbb). */
  export function blast(color: string): void {
    frame?.blast(color);
  }

  // Turning the robot by hand. Listened for on the window and hit-tested
  // against the slot: the frame lets clicks through, and the slot is a
  // button that's disabled while a rerun runs.
  function robotDown(e: PointerEvent): void {
    if (!box || !spot || e.button !== 0) return;
    const r = spot.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) return;
    // A press on something drawn over the robot (the what-if's chips, field
    // or bubble, moved onto it) is that thing's, not the robot's.
    const t = e.target instanceof Element ? e.target : null;
    if (t && !spot.contains(t) && t.closest('button, input, a, label, [role="status"], [role="group"]')) return;
    dragFrom = e.clientX;
    dragged = false;
    cancelAnimationFrame(snapFrame);
    snapFrame = 0;
    dragBase = dragYaw;
    e.preventDefault(); // no text selection while turning
  }
  function robotMove(e: PointerEvent): void {
    if (dragFrom === null) return;
    const turn = dragTurn(e.clientX - dragFrom, dragged);
    if (turn === null) return;
    dragged = true;
    dragYaw = dragBase + turn;
  }
  function robotUp(): void {
    if (dragFrom === null) return;
    if (!dragged) ontap?.();
    dragFrom = null;
    snapBack();
    // The click (if any) lands before this; a drag released off the page leaves none.
    setTimeout(() => (dragged = false));
  }
  // A drag isn't a press: the click that ends one doesn't talk to the robot.
  function robotClick(e: MouseEvent): void {
    if (!dragged) return;
    dragged = false;
    e.stopPropagation();
    e.preventDefault();
  }

  $effect(() => {
    shown = robotReady && robotShown;
  });

  function measureStage(): void {
    measureFrame = 0;
    // Dragging the time bar: no restaging; it's placed once more on release.
    if (scrubbing && box) return;
    if (!spot) {
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
    if (on !== robotShown) robotShown = on;
    if (!anchors || nudged || !spot || !box) return;
    const d = nudgeToSlot(spot.getBoundingClientRect(), anchors);
    nudged = true;
    if (Math.abs(d.x) > 3 || Math.abs(d.y) > 3) {
      nudge = { x: nudge.x + d.x, y: nudge.y + d.y };
      measureStage();
    }
    // The nudged stage reaches the frame a frame or two later: show after that.
    clearTimeout(readyTimer);
    readyTimer = setTimeout(() => (robotReady = true), SETTLE_MS);
  }

  onDestroy(() => {
    clearTimeout(readyTimer);
    cancelAnimationFrame(measureFrame);
    cancelAnimationFrame(snapFrame);
  });
</script>

<svelte:head>
  <link rel="preload" as="image" href={STILLS.history.src} fetchpriority="high" />
  <link rel="preload" as="image" href={STILLS.rerun.src} />
</svelte:head>
<svelte:window onresize={measureSoon} onpointerdown={robotDown} onpointermove={robotMove} onpointerup={robotUp} onpointercancel={robotUp} onclickcapture={robotClick} />

<div class="robot-host" class:ready={robotReady && robotShown} bind:this={host} aria-hidden="true">
  <RobotFrame bind:this={frame} {stage} visible={!!stage} {walking} {paint} {onRobot} />
</div>

<style>
  .robot-host { opacity: 0; transition: opacity 0.18s ease; position: absolute; inset: 0 0 auto 0; height: 100%; z-index: 3; overflow: hidden; pointer-events: none; }
  .robot-host.ready { opacity: 1; }                /* one cross-fade with the still (WhatIf .still, same 0.18s) */
</style>
