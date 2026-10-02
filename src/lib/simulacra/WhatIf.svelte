<script lang="ts">
  // Where you talk to the harness: it stands at the left (the page frames the
  // 3D robot into the slot; a face stands in where the robot isn't drawn),
  // says what it's doing in its bubble, and takes a what-if — a suggestion
  // tapped, or your own words — and reruns the election with it. The chips,
  // field and Rerun are WhatIfComposer.
  import type { WhatIf } from './schemas';
  import type { Message } from './whatif';
  import WhatIfComposer from './WhatIfComposer.svelte';

  interface Props {
    name?: string;
    /** The harness's face, for where no robot is drawn. */
    face?: string;
    faceStyle?: string;
    /** Reserve room for the drawn robot… */
    stage?: boolean;
    /** …and it's there. */
    robotShown?: boolean;
    /** The robot's spot (for the page to measure). */
    slot?: HTMLElement | null;
    message?: Message;
    whatIfs?: readonly WhatIf[];
    selected?: readonly string[];
    /** An open group: its what-ifs stand out. */
    slice?: string | null;
    /** The typed what-if. */
    value?: string;
    running?: boolean;
    canRun?: boolean;
    canReset?: boolean;
    /** The what-ifs in the rerun on show. */
    ran?: readonly string[];
    /** Something to run since that rerun. */
    dirty?: boolean;
    /** Nothing to rerun: no chips, no field. */
    closed?: boolean;
    /** The field. */
    input?: HTMLInputElement | null;
    ontoggle?: (key: string) => void;
    onrun?: () => void;
    onstop?: () => void;
    onreset?: () => void;
    /** A bubble action's key. */
    onaction?: (key: string) => void;
    onfocus?: (on: boolean) => void;
  }
  let {
    name = 'Harness',
    face = '',
    faceStyle = '',
    stage = false,
    robotShown = false,
    slot = $bindable(null),
    message = { text: '' },
    whatIfs = [],
    selected = [],
    slice = null,
    value = $bindable(''),
    running = false,
    canRun = true,
    canReset = false,
    ran = [],
    dirty = true,
    closed = false,
    input = $bindable(null),
    ontoggle,
    onrun,
    onstop,
    onreset,
    onaction,
    onfocus,
  }: Props = $props();

  const msgKey = $derived((message.text ?? '') + (message.quote ?? ''));
</script>

<section class="whatif" class:stage aria-label="What if">
  <!-- The robot stands over this spot (drawn by the page's overlay, which
       lets clicks through): pressing it is talking to it. -->
  <button type="button" class="bot" bind:this={slot} aria-label="Election Sim Harness" title="Election Sim Harness"
    disabled={closed || running} onclick={() => input?.focus()}>
    {#if !robotShown && face}
      <span class="face"><img src={face} alt="" style={faceStyle} draggable="false" /></span>
    {/if}
  </button>
  <div class="talk">
    <div class="bubble" class:busy={message.busy} role="status" aria-live="polite">
      {#key msgKey}<div class="lines">
      {#if message.quote}
        <blockquote>“{message.quote}”</blockquote>
        {#if message.by}<p class="by">{message.by}</p>{/if}
      {/if}
      {#if message.text}<p class="say" class:after={!!message.quote}>{message.text}</p>{/if}
      {#if message.detail}<p class="aside">{message.detail}</p>{/if}
      {#if message.actions?.length}
        <div class="acts">
          {#each message.actions as a (a.key)}
            <button type="button" class="act" class:primary={a.primary} onclick={() => onaction?.(a.key)}>{a.label}</button>
          {/each}
        </div>
      {/if}
      </div>{/key}
    </div>
    {#if !closed}
      <WhatIfComposer {name} {whatIfs} {selected} {slice} {ran} bind:value bind:input {running} {canRun} {canReset} {dirty}
        {ontoggle} {onrun} {onstop} {onreset} {onfocus} />
    {/if}
  </div>
</section>

<style>
  .whatif {
    margin-top: -10px;
    display: grid;
    grid-template-columns: 44px minmax(0, 1fr);
    align-items: start;
    gap: 12px;
  }
  /* Room for the robot to stand in, feet on the field's baseline. */
  .whatif.stage { grid-template-columns: 168px minmax(0, 1fr); align-items: end; min-height: 220px; }
  .bot {
    position: relative;
    height: 44px;
    padding: 0;
    border: none;
    border-radius: 16px;
    background: transparent;
    cursor: pointer;
  }
  .bot:disabled { cursor: default; }
  .bot:focus-visible { outline: 2px solid #3876b7; outline-offset: 2px; }
  /* The robot stands in the slot's full height, feet on its floor. */
  .stage .bot { height: auto; align-self: stretch; }
  .face {
    position: absolute;
    left: 0;
    top: 0;
    width: 44px;
    height: 44px;
    overflow: hidden;
    border-radius: 999px;
    background: #111716;
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.12);
  }
  /* The face is a photo: under dark mode's invert, turned back. */
  :global(.sa.dark) .face img { filter: invert(1) hue-rotate(180deg) saturate(66.7%); }
  .stage .face { top: auto; bottom: 64px; left: 50%; width: 88px; height: 88px; transform: translateX(-50%); }
  .face img { display: block; width: 100%; height: 100%; object-fit: cover; transform-origin: 50% 50%; }
  /* The what-if section sits on the dark page: the robot's
     voice and the controls you answer it with, in the Test Chat's dark
     materials (iOS system greys), so talking to the harness reads as a
     different place from the record above it. Tokens, read by the pieces too:
       --label / --label-2 / --label-3   text on the dark greys (92 / 62 / 42% white)
       --separator                       hairlines
       --tint                            #3876b7 lifted for dark surfaces (4.6:1 on --fill-press) */
  .whatif {
    --bubble: #262628;           /* iOS dark incoming bubble */
    --label: rgba(255, 255, 255, 0.92);
    --label-2: rgba(255, 255, 255, 0.62);
    --label-3: rgba(255, 255, 255, 0.42);
    --separator: rgba(255, 255, 255, 0.14);
    --fill: #2c2c2e;             /* raised: chips at rest */
    --fill-press: #3a3a3c;       /* raised further: hovers */
    --tint: #6ea8e0;
  }
  .talk { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
  /* On the stage the talk column fills the robot's height: the bubble pins to
     the top and the composer to the floor, so a year with more chips or a
     longer line never moves either while the time bar is scrubbed; a long
     bubble grows the column downward, like any message. */
  .stage .talk { align-self: stretch; }
  /* The robot's bubble: Messages' shape and tail, flat (no shadow). */
  .bubble {
    position: relative;
    align-self: flex-start;
    max-width: 58ch;
    margin-bottom: 5px;
    padding: 10px 16px 11px;
    border-radius: 20px;
    background: var(--bubble);
    color: var(--label);
    transition: opacity 0.2s ease;
  }
  .bubble.busy { opacity: 0.85; }
  /* The Test Chat's tail (MechaHud .msg--you.tail), mirrored to the left,
     filled with --bubble (#262628). */
  .bubble::after {
    content: '';
    position: absolute;
    left: 6px;
    bottom: -5px;
    width: 14px;
    height: 8px;
    transform: scaleX(-1);
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 93 76'%3E%3Cpath d='M-0.000,27.000 C12.839,31.371 39.956,53.698 40.1000,53.1000 C47.980,58.824 74.560,73.398 80.000,75.000 C85.440,76.602 89.403,76.321 92.156,73.836 C92.113,73.760 94.162,69.566 91.1000,64.1000 C88.060,59.218 84.265,53.211 82.000,49.000 C78.871,45.122 75.825,34.278 76.000,30.000 C75.936,25.444 77.127,19.864 78.1000,15.1000 C80.494,12.811 79.838,10.855 87.1000,2.1000 C64.644,-3.831 32.484,7.267 -0.000,27.000 Z' fill='%23262628'/%3E%3C/svg%3E") no-repeat 0 0 / 100% 100%;
    pointer-events: none;
  }
  .lines { animation: float-in 0.32s cubic-bezier(0.2, 0.9, 0.3, 1.2); }
  @keyframes float-in { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
  .say { position: relative; margin: 0; font-size: 15px; line-height: 1.42; letter-spacing: -0.005em; color: var(--label); }
  .say.after { margin-top: 8px; font-size: 13px; color: var(--label-2); }
  blockquote { margin: 2px 0 0; font-size: 15px; line-height: 1.45; font-style: italic; color: var(--label); }
  .by { margin: 6px 0 0; font-size: 12.5px; color: var(--label-2); }
  .aside { margin: 6px 0 0; font-size: 12.5px; line-height: 1.4; color: var(--label-2); }
  .acts { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
  /* In the bubble: text buttons on a hairline; the primary is the one
     light thing, white on the dark. */
  .act {
    height: 30px;
    padding: 0 13px;
    border: 1px solid var(--separator);
    border-radius: 999px;
    background: transparent;
    color: var(--label);
    font: inherit;
    font-size: 13px;
    cursor: pointer;
  }
  .act:hover { background: var(--fill); }
  .act:active { background: var(--fill-press); }
  .act.primary { background: #fff; border-color: #fff; color: #000; }
  .act.primary:hover { background: #e5e5ea; }
  .act.primary:active { background: #d1d1d6; }
  .act:focus-visible { outline: 2px solid #3876b7; outline-offset: 2px; }
  @media (prefers-reduced-motion: reduce) {
    .bubble { transition: none; }
    .lines { animation: none; }
  }
</style>
