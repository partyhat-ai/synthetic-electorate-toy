<script lang="ts">
  // The timeline along the bottom: every election from 1789 to 2024 as a
  // detent on one slider. Drag or click anywhere on it (it snaps to the
  // nearest election), step with the buttons or the arrow keys, or roll the
  // dice. The story years are the taller ticks.
  import { ChevronLeft, ChevronRight, Shuffle } from 'lucide-svelte';

  interface Props {
    years?: readonly number[];
    value: number;
    featured?: readonly number[];
    /** A year's spoken / tooltip text. */
    describe?: (y: number) => string;
    disabled?: boolean;
    /** The Rerun view: iOS dark colours. */
    dark?: boolean;
    /** A year was picked (dragged to, clicked, stepped, keyed). */
    onchange?: (year: number) => void;
    /** The dice. */
    onshuffle?: () => void;
  }
  let {
    years = [],
    value,
    featured = [],
    describe = (y) => String(y),
    disabled = false,
    dark = false,
    onchange,
    onshuffle,
  }: Props = $props();

  const LABELS = [1800, 1850, 1900, 1950, 2000];
  const first = $derived(years[0] ?? 0);
  const last = $derived(years[years.length - 1] ?? 0);
  const pos = (y: number) => ((y - first) / (last - first)) * 100;

  let rail = $state<HTMLElement | null>(null);
  let thumb = $state<HTMLElement | null>(null);
  let dragging = $state(false);
  let hover = $state<number | null>(null);
  const nearest = (x: number) => {
    if (!rail) return value;
    const r = rail.getBoundingClientRect();
    const y = first + ((x - r.left) / r.width) * (last - first);
    return years.reduce((b, e) => (Math.abs(e - y) < Math.abs(b - y) ? e : b), first);
  };
  const set = (y: number | undefined) => {
    if (y !== undefined && y !== value && !disabled) onchange?.(y);
  };
  function down(e: PointerEvent & { currentTarget: HTMLElement }) {
    if (e.button !== 0 || disabled) return;
    dragging = true;
    e.currentTarget.setPointerCapture?.(e.pointerId);
    set(nearest(e.clientX));
    thumb?.focus({ preventScroll: true });
  }
  function move(e: PointerEvent) {
    const y = nearest(e.clientX);
    if (dragging) set(y);
    else hover = y;
  }
  function up() {
    dragging = false;
  }
  function leave() {
    if (!dragging) hover = null;
  }
  const step = (d: number) => {
    const i = years.indexOf(value);
    set(years[Math.max(0, Math.min(years.length - 1, i + d))]);
  };
  const STEPS: Readonly<Record<string, number>> = { ArrowLeft: -1, ArrowDown: -1, ArrowRight: 1, ArrowUp: 1, PageDown: -5, PageUp: 5 };
  function key(e: KeyboardEvent) {
    const by = STEPS[e.key];
    if (by) {
      e.preventDefault();
      e.stopPropagation();
      step(by);
    } else if (e.key === 'Home') {
      e.preventDefault();
      set(first);
    } else if (e.key === 'End') {
      e.preventDefault();
      set(last);
    }
  }
  function tipOf(): number | null {
    if (dragging) return value;
    return hover != null && hover !== value ? hover : null;
  }
  const tip = $derived(tipOf());
</script>

<div class="bar" class:disabled class:dark>
  <div class="steps">
    <button type="button" class="icon" aria-label="Previous Election" title="Previous Election" disabled={disabled || value === first} onclick={() => step(-1)}>
      <ChevronLeft size={19} strokeWidth={2} aria-hidden="true" />
    </button>
    <button type="button" class="icon" aria-label="Next Election" title="Next Election" disabled={disabled || value === last} onclick={() => step(1)}>
      <ChevronRight size={19} strokeWidth={2} aria-hidden="true" />
    </button>
  </div>
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="slider" class:dragging onpointerdown={down} onpointermove={move} onpointerup={up} onpointercancel={up} onpointerleave={leave}>
    <div class="rail" bind:this={rail}>
      <div class="fill" style:width="{pos(value)}%"></div>
      {#each years as y (y)}
        <span class="tick" class:story={featured.includes(y)} style:left="{pos(y)}%"></span>
      {/each}
      {#each LABELS as l (l)}
        <span class="label" class:minor={l % 100 === 50} style:left="{pos(l)}%">{l}</span>
      {/each}
      <div
        class="thumb"
        bind:this={thumb}
        role="slider"
        tabindex={disabled ? -1 : 0}
        aria-label="Election"
        aria-valuemin={first}
        aria-valuemax={last}
        aria-valuenow={value}
        aria-valuetext={describe(value)}
        aria-disabled={disabled || undefined}
        style:left="{pos(value)}%"
        onkeydown={key}
      ></div>
      {#if tip != null}
        <span class="tip" style:left="{pos(tip)}%">{describe(tip)}</span>
      {/if}
    </div>
  </div>
  <button type="button" class="icon" aria-label="Random Election" title="Random Election" {disabled} onclick={() => onshuffle?.()}>
    <Shuffle size={17} strokeWidth={2} aria-hidden="true" />
  </button>
</div>

<style>
  /* The tuned sizes (settled with the old ?tuneTimeline panel), in one place. */
  .bar {
    --thumb: 28px;
    --track: 4px;
    --tick: 4px;
    --story-tick: 8px;
    --label-size: 11px;
    --label-gap: 20px;
    --bar-height: 68px;
    display: flex;
    align-items: center;
    gap: 14px;
    max-width: 980px;
    margin: 0 auto;
    padding: 0 16px;
    height: var(--bar-height);
  }
  .steps { display: flex; gap: 2px; }
  .icon {
    width: 34px;
    height: 34px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: none;
    border: none;
    border-radius: 999px;
    background: transparent;
    color: #007aff;              /* bar buttons take the tint (HIG) */
    cursor: pointer;
  }
  .icon:hover:not(:disabled) { background: rgba(0, 122, 255, 0.08); }
  .icon:active:not(:disabled) { opacity: 0.5; }
  .icon:disabled { opacity: 0.3; cursor: default; }
  .icon:focus-visible { outline: 2px solid #3876b7; outline-offset: 1px; }
  /* The hit area is the whole band, not just the rail. */
  .slider {
    position: relative;
    flex: 1;
    min-width: 0;
    height: 56px;
    padding: 0 10px;
    display: flex;
    align-items: center;
    cursor: pointer;
    touch-action: none;
    user-select: none;
    -webkit-user-select: none;
  }
  .slider.dragging { cursor: grabbing; }
  .rail {
    position: relative;
    width: 100%;
    height: var(--track);
    margin-top: -12px;
    border-radius: 999px;
    background: rgba(120, 120, 128, 0.2);   /* systemFill: the track */
  }
  /* The minimum track, in the tint (UISlider). */
  .fill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 999px; background: #007aff; }
  .tick {
    position: absolute;
    top: 9px;
    width: 1px;
    height: var(--tick);
    margin-left: -0.5px;
    background: rgba(60, 60, 67, 0.29);    /* separator */
    pointer-events: none;
  }
  .tick.story { height: var(--story-tick); width: 2px; margin-left: -1px; background: rgba(60, 60, 67, 0.6); border-radius: 1px; }
  .label {
    position: absolute;
    top: var(--label-gap);
    transform: translateX(-50%);
    font-size: var(--label-size);
    color: rgba(60, 60, 67, 0.6);           /* secondaryLabel */
    font-variant-numeric: tabular-nums;
    pointer-events: none;
  }
  .thumb {
    position: absolute;
    top: 50%;
    /* UISlider's thumb: 28pt, white, a hairline and a soft double shadow. */
    width: var(--thumb);
    height: var(--thumb);
    margin: calc(var(--thumb) / -2) 0 0 calc(var(--thumb) / -2);
    border-radius: 999px;
    background: #fff;
    box-shadow: 0 0 0 0.5px rgba(0, 0, 0, 0.04), 0 3px 8px rgba(0, 0, 0, 0.15), 0 3px 1px rgba(0, 0, 0, 0.06);
    cursor: grab;
  }
  .thumb:focus-visible { outline: 2px solid #3876b7; outline-offset: 2px; }
  .tip {
    position: absolute;
    bottom: 20px;
    transform: translateX(-50%);
    padding: 4px 9px;
    border-radius: 8px;
    background: #fff;
    color: #000;
    white-space: nowrap;
    font-size: 12px;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    pointer-events: none;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12), 0 0 0 0.5px rgba(0, 0, 0, 0.06);
  }
  .disabled .slider { cursor: default; opacity: 0.5; }
  /* Dark (Rerun): the same parts in iOS dark system colours — systemBlue
     #0A84FF, the dark systemFill track, separator ticks, secondaryLabel. */
  .dark .icon { color: #0a84ff; }
  .dark .icon:hover:not(:disabled) { background: rgba(10, 132, 255, 0.14); }
  .dark .rail { background: rgba(120, 120, 128, 0.36); }
  .dark .fill { background: #0a84ff; }
  .dark .tick { background: rgba(84, 84, 88, 0.65); }
  .dark .tick.story { background: rgba(235, 235, 245, 0.6); }
  .dark .label { color: rgba(235, 235, 245, 0.6); }
  .dark .tip { background: #2c2c2e; color: #fff; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4), 0 0 0 0.5px rgba(255, 255, 255, 0.08); }
  @media (max-width: 560px) {
    .bar { gap: 4px; padding: 0 8px; }
    .label.minor { display: none; }
  }
</style>
