<script lang="ts">
  // The narrator robot, framed into the page. Mount it inside the element the
  // robot should scroll with (the page's `robot-host`, position: relative or
  // absolute): the frame fills that element, is click-through, and never moves
  // once it has started loading (moving an iframe reloads it).
  //
  // Props
  //   stage    RobotStage | null  The box the robot stands in, CSS px from the
  //                               host element's bottom-right corner, with
  //                               mirror and yaw (degrees, eased in the frame).
  //                               null: the frame's default corner box.
  //                               See stageInSlot in ./stage.ts.
  //   visible  boolean = true      false hides the frame and stops its render loop.
  //   walking  boolean = false     The robot walks (the page is working) or idles.
  //   paint    'history' | 'rerun' History is the Americana model's own paint;
  //                               Rerun the original paint with the stars.
  //                               Each paint brings its own lighting.
  //   onRobot  (anchors) => void   Called every frame while visible with
  //                               { centerX, feetY } in window CSS px: the
  //                               robot's centre line and the floor under its
  //                               feet. null while it loads or while hidden.
  //
  // Methods
  //   blast(color)                 A shot from the chest reactor in #rrggbb.
  //                               Nothing before the frame is ready.
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import type { Paint } from './characters';
  import { type HostMessage, parseFrameMessage, type RobotAnchors, type RobotStage } from './messages';

  interface Props {
    stage: RobotStage | null;
    visible?: boolean;
    walking?: boolean;
    paint: Paint;
    onRobot?: (anchors: RobotAnchors | null) => void;
  }

  let { stage, visible = true, walking = false, paint, onRobot }: Props = $props();

  let frame: HTMLIFrameElement | undefined = $state();
  // Bumped on every robot:ready, so a reloaded frame is sent the state again.
  let readyCount = $state(0);

  function post(message: HostMessage): void {
    frame?.contentWindow?.postMessage(message, location.origin);
  }

  export function blast(color: string): void {
    if (readyCount > 0 && visible) post({ type: 'robot:blast', color });
  }

  // $state.snapshot: a reactive proxy can't be structured-cloned.
  $effect(() => {
    if (readyCount > 0) post({ type: 'robot:stage', stage: $state.snapshot(stage) });
  });
  $effect(() => {
    if (readyCount > 0) post({ type: 'robot:running', on: visible });
  });
  $effect(() => {
    if (readyCount > 0) post({ type: 'robot:walk', on: walking });
  });
  $effect(() => {
    if (readyCount > 0) post({ type: 'robot:paint', paint });
  });
  $effect(() => {
    if (!visible) onRobot?.(null);
  });

  onMount(() => {
    function onMessage(event: MessageEvent): void {
      if (!frame || event.origin !== location.origin || event.source !== frame.contentWindow) return;
      const message = parseFrameMessage(event.data);
      if (!message) return;
      switch (message.type) {
        case 'robot:ready':
          readyCount += 1;
          break;
        case 'robot:anchors': {
          const a = message.anchors;
          if (!a || !visible) {
            onRobot?.(null);
            break;
          }
          // Frame px to window px.
          const r = frame.getBoundingClientRect();
          onRobot?.({ centerX: a.centerX + r.left, feetY: a.feetY + r.top });
          break;
        }
        default:
          message satisfies never;
      }
    }
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  });
</script>

<iframe
  bind:this={frame}
  class="robot-frame"
  class:hidden={!visible}
  src={resolve('/robot')}
  title="Narrator"
  tabindex="-1"
  aria-hidden="true"
></iframe>

<style>
  .robot-frame {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border: 0;
    background: transparent;
    pointer-events: none;
    z-index: 20;
    /* = the frame document's, or browsers paint the frame opaque. */
    color-scheme: normal;
  }
  .robot-frame.hidden {
    visibility: hidden;
  }
</style>
