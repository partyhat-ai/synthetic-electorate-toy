<script lang="ts">
  // The narrator: the harness robot's bubble and the what-if composer
  // (WhatIf, which owns the bubble's 7-line clamp and More / Less), with
  // what it says worked out from the page's state (narrator.ts say()). A
  // finished rerun's steps come out one at a time (startReveal), and the
  // robot walks while they do (`revealing`).
  import { onDestroy } from 'svelte';
  import { say, STEP_MS } from './narrator';
  import type { WhatIf as WhatIfItem } from './schemas';
  import type { PageState } from './state.svelte';
  import type { Names } from './types';
  import WhatIf from './WhatIf.svelte';

  interface Props {
    page: PageState;
    names: Names;
    /** A browser tab wide enough to draw the robot in the slot. */
    stage: boolean;
    /** The live robot is drawn. */
    robotShown: boolean;
    /** The robot's spot, for RobotStage to measure. */
    slot?: HTMLElement | null;
    /** The chips, held from the last loaded year while scrubbing. */
    chips: readonly WhatIfItem[];
    closed: boolean;
    /** A finished rerun's steps are still coming out. */
    revealing?: boolean;
    onaction: (key: string) => void;
  }
  let {
    page,
    names,
    stage,
    robotShown,
    slot = $bindable(null),
    chips,
    closed,
    revealing = $bindable(false),
    onaction,
  }: Props = $props();

  // The ChatPro harness's face, cropped as the robot overlay crops it: where
  // no robot is drawn (narrow windows, before WebGL loads).
  const NAME = 'ChatPro';
  const FACE = '/harness-faces/atlas-09.png?v=5';
  const FACE_STYLE = 'transform: scale(1.213) translate(0%, 4%)';

  // Steps shown so far; Infinity once they're all out.
  let reveal = $state(Infinity);
  let revealTimer: ReturnType<typeof setInterval> | undefined;

  /** A finished rerun's n steps come out one at a time. */
  export function startReveal(n: number): void {
    clearInterval(revealTimer);
    reveal = 0;
    revealing = true;
    revealTimer = setInterval(() => {
      reveal += 1;
      if (reveal >= n) {
        clearInterval(revealTimer);
        reveal = Infinity;
        revealing = false;
      }
    }, STEP_MS);
  }
  onDestroy(() => clearInterval(revealTimer));

  const message = $derived(
    say({
      server: page.server,
      year: page.year,
      election: page.election,
      run: page.run,
      running: page.running,
      runError: page.runError,
      simFailed: page.simFailed,
      sim: page.sim,
      toggled: page.lastToggled,
      whatIfs: page.whatIfs,
      slice: page.openSlice,
      showing: page.showing,
      result: page.result,
      names,
      person: page.voter,
      finding: !!page.voterKey && page.voterLoading === page.voterKey,
      draft: page.typed,
      shown: reveal,
      sample: page.api.sample,
    }),
  );
</script>

<WhatIf
  name={NAME}
  face={FACE}
  faceStyle={FACE_STYLE}
  {stage}
  {robotShown}
  bind:slot
  {message}
  whatIfs={chips}
  selected={page.selected}
  slice={page.openSlice}
  bind:value={page.typed}
  running={page.running}
  canRun={page.canRun}
  canReset={!!page.result || page.selected.length > 0 || !!page.edits.get(page.year)}
  ran={page.result?.ran ?? []}
  dirty={page.dirty}
  {closed}
  ontoggle={(key) => page.toggle(key)}
  onrun={() => page.rerunNow()}
  onstop={() => page.stop()}
  onreset={() => page.reset()}
  {onaction}
/>
