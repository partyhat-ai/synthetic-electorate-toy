<script lang="ts">
  // The robot's frame: RobotFrame loads this page in an iframe and talks to it
  // with postMessage (protocol in $lib/robot/messages.ts). Its own document on
  // purpose: the scene's page styles (transparent html/body, a full-window
  // canvas) must not reach the host page.
  import { onMount } from 'svelte';
  import '$lib/robot/style.css';
  import { type FrameMessage, parseHostMessage, type RobotStage } from '$lib/robot/messages';
  import type { RobotApp } from '$lib/robot/scene';
  import { DEFAULT_STAGE } from '$lib/robot/stage';

  let canvas: HTMLCanvasElement | undefined = $state();

  onMount(() => {
    let app: RobotApp | null = null;
    let stage: RobotStage = DEFAULT_STAGE;
    let gone = false;
    const toHost = (message: FrameMessage) => window.parent.postMessage(message, location.origin);

    function onMessage(event: MessageEvent): void {
      if (!app || event.origin !== location.origin || event.source !== window.parent) return;
      const message = parseHostMessage(event.data);
      if (!message) return;
      switch (message.type) {
        case 'robot:stage':
          stage = message.stage ?? DEFAULT_STAGE;
          app.restage();
          break;
        case 'robot:running':
          app.setRunning(message.on);
          break;
        case 'robot:walk':
          app.setWalking(message.on);
          break;
        default:
          message satisfies never;
      }
    }

    // three.js loads with this page only, not with the host page.
    void import('$lib/robot/scene').then(({ mountRobot }) => {
      if (gone || !canvas) return;
      app = mountRobot({ canvas, stage: () => stage });
      app.onAnchors((anchors) => toHost({ type: 'robot:anchors', anchors }));
      window.addEventListener('message', onMessage);
      toHost({ type: 'robot:ready' });
    });

    return () => {
      gone = true;
      window.removeEventListener('message', onMessage);
      app?.dispose();
      app = null;
    };
  });
</script>

<svelte:head>
  <title>Narrator</title>
</svelte:head>

<canvas bind:this={canvas} class="robot-scene" aria-hidden="true"></canvas>
