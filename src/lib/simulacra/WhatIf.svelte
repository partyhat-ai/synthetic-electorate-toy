<script lang="ts">
  // Where you talk to the harness: it stands at the left (the page frames the
  // 3D robot into the slot; a still of it stands in until the robot draws),
  // says what it's doing in its bubble, and takes a what-if — a suggestion
  // tapped, or your own words — and reruns the election with it. The
  // bubble's working is WhatIfWorking; the chips, field and Rerun are
  // WhatIfComposer.
  import { onDestroy, untrack } from 'svelte';
  import { STAGE_SIZE } from '$lib/robot/stage';
  import Places from './Places.svelte';
  import { hoverPlaces } from './places';
  import type { WhatIf } from './schemas';
  import type { Message, Still } from './whatif';
  import WhatIfComposer from './WhatIfComposer.svelte';
  import WhatIfWorking from './WhatIfWorking.svelte';

  interface Props {
    name?: string;
    /** The live robot is drawn in the slot. */
    robotShown?: boolean;
    /** A still of the robot, shown in the slot until the live robot draws. */
    still?: Still | null;
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
    /** The year in words, shown under the opening message on a narrow window. */
    caption?: string;
  }
  let {
    name = 'Harness',
    robotShown = false,
    still = null,
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
    caption = '',
  }: Props = $props();

  // A long bubble: the Test Chat's More / Less (MechaHud .msg). Past CLAMP
  // lines it shows its last CLAMP lines, the top fading out (the HUD's peek); a click opens it to its full
  // height (capped at 46vh, then it scrolls, each edge feathering while
  // there's more past it) and a click folds it back. A new message folds.
  const CLAMP = 7;
  // The tail only on a bubble no taller than the default one ("Change one
  // thing about … / Pick a counterfactual…", 66px): anything bigger drops it.
  const TAIL_MAX = 68;
  // Less: one quiet move. The bubble shrinks while it's still lifted (its
  // bottom fixed, so only its top eases down), the content held to its end as
  // it goes; once it's at the folded height it drops back into the flow, where
  // the room kept for it is exactly that height, so nothing jumps.
  const CLOSE_MS = 240; // = .clip's max-height transition
  // The clip's line height when it reads as `normal`, px.
  const LINE_PX = 21;

  let clipEl = $state<HTMLElement | null>(null);
  let bubbleEl = $state<HTMLElement | null>(null);
  let over = $state(false);
  let opened = $state(false);
  let closing = $state(false);
  let moreAbove = $state(false);
  let moreBelow = $state(false);
  /** The folded bubble's height, kept while it's opened. */
  let holdH = $state(0);
  /** CLAMP lines, px: the folded bubble's most (.clip), and the room a narrow window keeps for it (.hold). */
  let lim = $state(CLAMP * LINE_PX);
  let tall = $state(false);
  let ro: ResizeObserver | null = null;
  let closeTimer: ReturnType<typeof setTimeout> | undefined;
  let pinFrame = 0;

  function sized(node: HTMLElement) {
    const r = new ResizeObserver(() => {
      tall = node.offsetHeight > TAIL_MAX;
    });
    r.observe(node);
    return { destroy: () => r.disconnect() };
  }
  function measure() {
    if (!clipEl) return;
    const lh = Number.parseFloat(getComputedStyle(clipEl).lineHeight) || LINE_PX;
    lim = Math.round(lh * CLAMP);
    clipEl.style.setProperty('--full', `${clipEl.scrollHeight}px`);
    over = clipEl.scrollHeight > lh * CLAMP + 2;
    // Folded, it's the HUD's peek: the newest (the answer, or the step in
    // hand) at the bottom, the earlier working fading out above it.
    if (!opened) clipEl.scrollTop = clipEl.scrollHeight;
    edges();
  }
  function edges() {
    if (!clipEl || !opened) {
      moreAbove = false;
      moreBelow = false;
      return;
    }
    moreAbove = clipEl.scrollTop > 1;
    moreBelow = clipEl.scrollHeight - clipEl.scrollTop - clipEl.clientHeight > 1;
  }
  function clampable(node: HTMLElement) {
    ro = new ResizeObserver(measure);
    ro.observe(node);
    for (const c of node.children) ro.observe(c);
    document.fonts?.ready?.then(measure);
    return { destroy: () => ro?.disconnect() };
  }
  const msgKey = $derived((message.text ?? '') + (message.quote ?? ''));
  // Folded and finished, the bubble is just the answer: the working (steps,
  // interviews) waits behind More. While the robot is working it shows live.
  const working = $derived(!!message.busy);
  const tucked = $derived(!working && !!(message.steps?.length || message.interview?.byWhatIf.length));
  const canMore = $derived(over || tucked);
  // A new message folds the bubble and lets go of any lit place.
  $effect.pre(() => {
    void msgKey;
    untrack(() => {
      opened = false;
      closing = false;
      hoverPlaces.set([]);
      queueMicrotask(measure);
    });
  });
  $effect.pre(() => {
    void message.steps;
    queueMicrotask(measure);
  });
  function pinEnd() {
    if (clipEl) clipEl.scrollTop = clipEl.scrollHeight;
    if (closing) pinFrame = requestAnimationFrame(pinEnd);
  }
  function toggleOpen() {
    if (!canMore || closing || window.getSelection()?.toString()) return;
    if (!opened) {
      holdH = (bubbleEl?.getBoundingClientRect().height ?? 0) + 5; // exact (sub-pixel) + its 5px margin (the tail's room)
      opened = true;
      // Open: the newest (the end) stays in view; the bubble grows upward.
      // The working appears now, so measure its full height, then hold the end in view.
      requestAnimationFrame(() => {
        measure();
        if (clipEl) clipEl.scrollTop = clipEl.scrollHeight;
        edges();
      });
      return;
    }
    closing = true;
    moreAbove = false;
    moreBelow = false;
    pinEnd();
    clearTimeout(closeTimer);
    closeTimer = setTimeout(() => {
      cancelAnimationFrame(pinFrame);
      closing = false;
      opened = false;
      requestAnimationFrame(measure);
    }, CLOSE_MS);
  }
  function more(e: MouseEvent) {
    e.stopPropagation();
    toggleOpen();
  }
  onDestroy(() => {
    ro?.disconnect();
    clearTimeout(closeTimer);
    cancelAnimationFrame(pinFrame);
  });
</script>

<section class="whatif" aria-label="What if" style:--stage-w="{STAGE_SIZE.width}px">
  <!-- The robot stands over this spot (drawn by the page's overlay, which
       lets clicks through): pressing it is talking to it. -->
  <button type="button" class="bot" bind:this={slot} aria-label="Election Sim Harness" title="Election Sim Harness"
    disabled={closed || running} onclick={() => input?.focus()}>
    {#if still}
      <img class="still" class:gone={robotShown} src={still.src} alt="" draggable="false" decoding="async" fetchpriority="high"
        style:left="calc(50% + {still.dx}px)" style:bottom="{still.db}px" style:width="{still.w}px" />
    {/if}
  </button>
  <div class="talk">
    <div class="hold" class:lifted={opened} style:height={opened ? `${holdH}px` : null} style:--lim="{lim}px">
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div class="bubble" class:busy={message.busy} class:over={canMore} class:clamped={over} class:opened class:closing class:tall role="status" aria-live="polite" onclick={toggleOpen} bind:this={bubbleEl} use:sized>
      <div class="clip" class:above={moreAbove} class:below={moreBelow} bind:this={clipEl} use:clampable onscroll={edges}>
      <WhatIfWorking {message} {whatIfs} {working} {opened} onfold={() => requestAnimationFrame(() => { measure(); edges(); })} />
      {#key msgKey}<div class="lines">
      {#if message.quote}
        <blockquote>“<Places text={message.quote} />”</blockquote>
        {#if message.by}<p class="by"><Places text={message.by} /></p>{/if}
      {/if}
      {#if message.text}<p class="say" class:after={!!message.quote}><Places text={message.text} /></p>{/if}
      {#if message.detail}<p class="aside"><Places text={message.detail} /></p>{/if}
      {#if message.actions?.length}
        <div class="acts">
          {#each message.actions as a (a.key)}
            <button type="button" class="act" class:primary={a.primary} onclick={() => onaction?.(a.key)}>{a.label}</button>
          {/each}
        </div>
      {/if}
      </div>{/key}
      </div>
      {#if canMore}<button type="button" class="more" aria-expanded={opened} onclick={more}>{opened ? 'Less' : 'More'}</button>{/if}
    </div>
    <!-- Narrow only: the time bar's tooltip, held here under the opening message. -->
    {#if message.opening && caption}<span class="year-pill" aria-hidden="true">{caption}</span>{/if}
    </div>
    {#if !closed}
      <WhatIfComposer {name} {whatIfs} {selected} {slice} {ran} bind:value bind:input {running} {canRun} {canReset} {dirty}
        {ontoggle} {onrun} {onstop} {onreset} {onfocus} />
    {:else}
      <!-- An unopposed year: no chips or field, but on a narrow window their room stays. -->
      <div class="composer-room" aria-hidden="true"></div>
    {/if}
  </div>
</section>

<style>
  /* Room for the robot to stand in, feet on the field's baseline. */
  .whatif {
    margin-top: -10px;
    display: grid;
    grid-template-columns: 168px minmax(0, 1fr);
    align-items: end;
    gap: 12px;
    min-height: 220px;
  }
  /* The robot keeps its spot: a tall bubble grows the talk column downward, never moves the bot. */
  .bot {
    position: relative;
    align-self: start;
    height: 220px;
    padding: 0;
    border: none;
    border-radius: 16px;
    background: transparent;
    cursor: pointer;
  }
  /* Tapping or clicking the robot is talking to it, not selecting it: no
     tap highlight, no selection or callout on a long press, no focus ring
     from a pointer (the keyboard's stays, below). */
  .bot {
    -webkit-tap-highlight-color: transparent;
    -webkit-user-select: none;
    user-select: none;
    -webkit-touch-callout: none;
  }
  .bot:focus:not(:focus-visible) { outline: none; }
  .bot:disabled { cursor: default; }
  .bot:focus-visible { outline: 2px solid #3876b7; outline-offset: 2px; }
  /* The still: under the live robot, faded out once it draws. */
  .still { position: absolute; height: auto; max-width: none; pointer-events: none; transition: opacity 0.18s ease; }   /* = the page's .robot-host fade */
  .still.gone { opacity: 0; }
  :global(.sa.dark) .still { filter: invert(1) hue-rotate(180deg) saturate(66.7%); }
  /* The what-if section in HIG light mode, after iOS Messages: the robot's
     bubble is an incoming message, the what-ifs and field are Messages'
     white capsules and hairlines, and the one accent is iMessage blue
     (#007AFF), on Rerun as on the send button. Messages sets its grey
     incoming bubble (#E9E9EB) on white; this page is already about that
     grey (#e5e5e5, systemGray5), so the bubble takes the white step up
     instead. Tokens (iOS system colours), read by the pieces too:
       --label / --label-2 / --label-3   label, secondaryLabel, tertiaryLabel
       --separator                       opaqueSeparator
       --tint                            systemBlue */
  .whatif {
    --bubble: #fff;
    --label: #000;
    --label-2: rgba(60, 60, 67, 0.6);
    --label-3: rgba(60, 60, 67, 0.3);
    --separator: #c6c6c8;
    --fill: #f2f2f7;             /* systemGray6: chips at rest, hovers */
    --fill-press: #e5e5ea;       /* systemGray5: press */
    --tint: #007aff;
    /* Metrics, read by the pieces too. */
    --control-h: 36px;           /* a chip, Rerun, and the field inside its hairline */
    --hairline: 1px;             /* the field's ring */
    --compose-gap: 8px;          /* the chips over the field */
    --bubble-pad-top: 10px;
    --bubble-pad-bottom: 11px;
    --more-gap: 8px;             /* More / Less under the bubble's text */
    --more-size: 12px;
    --more-leading: 1.2;
  }
  /* The talk column fills the robot's height: the bubble pins to the top and
     the composer to the floor, so a year with more chips or a longer line
     never moves either while the time bar is scrubbed; a long bubble grows
     the column downward, like any message. */
  .talk { display: flex; flex-direction: column; gap: 12px; min-width: 0; align-self: stretch; }
  .composer-room, .year-pill { display: none; }
  /* Narrow windows (phones, or a narrow desktop window): the what-if takes
     the full width and the robot stands above it. Every part of the what-if
     that varies holds its most, so nothing moves with the year or the
     message. Opened, the bubble grows over the chips and field. */
  @media (max-width: 760px) {
    /* Narrow: Who voted, then the robot, then the bubble, the chips and the
       field, top to bottom; the robot --robot-gap under the last group and
       over the bubble, whatever the screen. The robot's figure doesn't fill
       its slot: --figure-head is how far under the slot's top its head reads,
       seen from the last group's dots, and --figure-toes how far past the
       slot's floor its toes reach, seen from the bubble. Both were measured
       on screen at its narrow rest (stage.ts NARROW_ROBOT_YAW); re-measure
       them if the model, its framing (RobotStage STILLS) or that turn
       changes. The slot is the robot's width (STAGE_SIZE) by --slot-h. */
    .whatif {
      --robot-gap: 12px;
      --figure-head: 50px;
      --figure-toes: 8px;
      --slot-h: 236px;
      display: flex;
      flex-direction: column;
      align-items: stretch;
      gap: 0;
      min-height: 0;
      margin-top: 0;
      /* A horizontal drag on the robot turns it; a vertical one scrolls. */
      touch-action: pan-y pinch-zoom;
      /* The robot stands over this area too: no tap highlight on it. */
      -webkit-tap-highlight-color: transparent;
    }
    .bot { width: var(--stage-w); height: var(--slot-h); margin: calc(var(--robot-gap) - var(--figure-head)) 0 0; align-self: center; }
    .talk { position: relative; z-index: 1; min-width: 0; margin-top: calc(var(--robot-gap) + var(--figure-toes)); }
    /* The bubble's room is its folded most (CLAMP lines and More) and it sits
       at the room's top, just under the robot, so the robot's gap holds for
       any message; a shorter one leaves the room under it, so the chips and
       field never move. Opened, it grows down over them. */
    .hold {
      min-height: calc(var(--bubble-pad-top) + var(--lim) + var(--more-gap) + var(--more-size) * var(--more-leading) + var(--bubble-pad-bottom));
      justify-content: flex-start;
    }
    .hold.lifted .bubble { top: 0; bottom: auto; }
    /* As tall as the chips and the field (WhatIfComposer). */
    .composer-room { display: block; height: calc(2 * var(--control-h) + 2 * var(--hairline) + var(--compose-gap)); }
    /* The time bar's tooltip (TimeBar .tip, same size, padding and look),
       solid under the opening message instead of floating over the bar.
       It fits in the bubble's room, so nothing moves when it goes. */
    .year-pill {
      display: inline-block;
      align-self: center;
      margin-top: 8px;
      padding: 4px 9px;
      border-radius: 8px;
      background: #fff;
      color: #000;
      white-space: nowrap;
      font-size: 12px;
      font-weight: 500;
      font-variant-numeric: tabular-nums;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12), 0 0 0 0.5px rgba(0, 0, 0, 0.06);
    }
    /* A newline in the bubble's aside breaks here (a wide window reads it as a space). */
    .aside { white-space: pre-line; }
    /* The tail pointed at the robot beside the bubble; it stands above now. */
    .bubble::after { display: none; }
  }
  /* Opened (More), the bubble leaves the flow: its slot keeps the folded
     height, so nothing below or around moves, and the bubble grows upward
     from the slot's bottom, over the page above. The bubble's column is the
     container its sections query (the bubble itself shrinks to fit, so it
     can't be one): 472px = 440px of text + its padding. */
  .hold { position: relative; container-type: inline-size; display: flex; flex-direction: column; align-items: flex-start; width: 100%; }
  .hold.lifted .bubble { position: absolute; left: 0; right: 0; bottom: 5px; z-index: 2; margin-bottom: 0; }
  /* The robot's bubble: Messages' shape and tail, flat (no shadow). */
  /* Always the column's full width, however short the message. */
  .bubble {
    position: relative;
    align-self: stretch;
    margin-bottom: 5px;
    padding: var(--bubble-pad-top) 16px var(--bubble-pad-bottom);
    border-radius: 20px;
    background: var(--bubble);
    color: var(--label);
    transition: opacity 0.2s ease;
  }
  .bubble.busy { opacity: 0.85; }
  /* Rerun: lit from above. The page is inverted there (theme.css), so a
     dark inset and sheen on the white bubble render as a white top hairline
     and a faint highlight on the dark one. */
  :global(.sa.dark) .bubble {
    box-shadow: inset 0 1px 0 rgba(0, 0, 0, 0.22);
    background-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.045), rgba(0, 0, 0, 0) 45%);
  }
  .bubble.tall::after { display: none; }
  /* The Test Chat's tail (MechaHud .msg--you.tail), mirrored to the left,
     filled with --bubble (#fff). */
  .bubble::after {
    content: '';
    position: absolute;
    left: 6px;
    bottom: -5px;
    width: 14px;
    height: 8px;
    transform: scaleX(-1);
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 93 76'%3E%3Cpath d='M-0.000,27.000 C12.839,31.371 39.956,53.698 40.1000,53.1000 C47.980,58.824 74.560,73.398 80.000,75.000 C85.440,76.602 89.403,76.321 92.156,73.836 C92.113,73.760 94.162,69.566 91.1000,64.1000 C88.060,59.218 84.265,53.211 82.000,49.000 C78.871,45.122 75.825,34.278 76.000,30.000 C75.936,25.444 77.127,19.864 78.1000,15.1000 C80.494,12.811 79.838,10.855 87.1000,2.1000 C64.644,-3.831 32.484,7.267 -0.000,27.000 Z' fill='%23fff'/%3E%3C/svg%3E") no-repeat 0 0 / 100% 100%;
    pointer-events: none;
  }
  /* More / Less (MechaHud .msg): clamped with a fade; opened to its height,
     then scrolling with feathered edges (@property, so they ease). */
  @property --ft { syntax: '<length>'; inherits: false; initial-value: 0px; }
  @property --fb { syntax: '<length>'; inherits: false; initial-value: 0px; }
  .clip { max-height: var(--lim, none); overflow: hidden; transition: max-height 0.24s cubic-bezier(0.2, 0.9, 0.3, 1), --ft 0.3s ease, --fb 0.3s ease; }
  .bubble.over { cursor: pointer; }
  .bubble.clamped:not(.opened) .clip { -webkit-mask-image: linear-gradient(to top, #000 55%, transparent); mask-image: linear-gradient(to top, #000 55%, transparent); }
  .bubble.opened .clip {
    --band: 28px;
    max-height: min(var(--full), 46vh);
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-width: none;
    -webkit-mask-image: linear-gradient(to bottom, transparent calc(var(--ft) - var(--band)), #000 var(--ft), #000 calc(100% - var(--fb)), transparent calc(100% - var(--fb) + var(--band)));
    mask-image: linear-gradient(to bottom, transparent calc(var(--ft) - var(--band)), #000 var(--ft), #000 calc(100% - var(--fb)), transparent calc(100% - var(--fb) + var(--band)));
  }
  .bubble.opened .clip::-webkit-scrollbar { display: none; }
  .clip.above { --ft: var(--band); }
  .clip.below { --fb: var(--band); }
  /* Less: back to the folded height, still lifted, on the same ease. */
  .bubble.closing .clip { transition: max-height 0.24s cubic-bezier(0.4, 0, 0.2, 1); max-height: var(--lim); overflow: hidden; -webkit-mask-image: linear-gradient(to top, #000 55%, transparent); mask-image: linear-gradient(to top, #000 55%, transparent); }
  .more { display: block; margin: var(--more-gap) 0 0; padding: 0; border: none; background: none; font: inherit; font-size: var(--more-size); font-weight: 500; line-height: var(--more-leading); color: var(--tint); cursor: pointer; }
  .more:hover { opacity: 0.7; }
  .more:focus-visible { outline: 2px solid #3876b7; outline-offset: 2px; border-radius: 4px; }
  .lines { animation: float-in 0.32s cubic-bezier(0.2, 0.9, 0.3, 1.2); }
  @keyframes float-in { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
  .say { position: relative; margin: 0; font-size: 15px; line-height: 1.42; letter-spacing: -0.005em; color: var(--label); }
  .say.after { margin-top: 8px; font-size: 13px; color: var(--label-2); }
  blockquote { margin: 2px 0 0; font-size: 15px; line-height: 1.45; font-style: italic; color: var(--label); }
  .by { margin: 6px 0 0; font-size: 12.5px; color: var(--label-2); }
  .aside { margin: 6px 0 0; font-size: 12.5px; line-height: 1.4; color: var(--label-2); }
  .acts { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
  /* In the bubble: tinted text buttons on a hairline, the primary filled. */
  .act {
    height: 30px;
    padding: 0 13px;
    border: 1px solid var(--separator);
    border-radius: 999px;
    background: transparent;
    color: var(--tint);
    font: inherit;
    font-size: 13px;
    cursor: pointer;
  }
  .act:hover { background: var(--fill); }
  .act:active { background: var(--fill-press); }
  .act.primary { background: var(--tint); border-color: var(--tint); color: #fff; }
  .act.primary:hover { background: #0071eb; }
  .act.primary:active { background: #0062cc; }
  .act:focus-visible { outline: 2px solid #3876b7; outline-offset: 2px; }
  /* Under the Rerun view's invert (.sa.dark) the tint would come out cyan
     and white labels black: the accent-coloured parts are turned back (as
     the photos are) and take dark mode's systemBlue. */
  :global(.sa.dark) .whatif { --tint: #0a84ff; }
  :global(.sa.dark) .act.primary { filter: invert(1) hue-rotate(180deg) saturate(66.7%); }
  @media (prefers-reduced-motion: reduce) {
    .bubble { transition: none; }
    .lines { animation: none; }
    .clip { transition: none; }
  }
</style>
