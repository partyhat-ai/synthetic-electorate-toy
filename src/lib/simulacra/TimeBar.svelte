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

<div class="bar" class:disabled>
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
  .bar {
    display: flex;
    align-items: center;
    gap: 14px;
    max-width: 980px;
    margin: 0 auto;
    padding: 0 16px;
    height: 68px;
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
    color: rgba(255, 255, 255, 0.75);
    cursor: pointer;
  }
  .icon:hover:not(:disabled) { background: rgba(255, 255, 255, 0.1); color: #fff; }
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
    height: 4px;
    margin-top: -12px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.16);
  }
  .fill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 999px; background: rgba(255, 255, 255, 0.7); }
  .tick {
    position: absolute;
    top: 9px;
    width: 1px;
    height: 4px;
    margin-left: -0.5px;
    background: rgba(255, 255, 255, 0.22);
    pointer-events: none;
  }
  .tick.story { height: 8px; width: 2px; margin-left: -1px; background: rgba(255, 255, 255, 0.55); border-radius: 1px; }
  .label {
    position: absolute;
    top: 20px;
    transform: translateX(-50%);
    font-size: 11px;
    color: rgba(255, 255, 255, 0.45);
    font-variant-numeric: tabular-nums;
    pointer-events: none;
  }
  .thumb {
    position: absolute;
    top: 50%;
    width: 22px;
    height: 22px;
    margin: -11px 0 0 -11px;
    border-radius: 999px;
    /* White on the dark bar: the inverse of the page it sits on. */
    background: #fff;
    box-shadow: 0 0 0 0.5px rgba(0, 0, 0, 0.3), 0 1px 4px rgba(0, 0, 0, 0.5);
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
  }
  .disabled .slider { cursor: default; opacity: 0.5; }
  @media (max-width: 560px) {
    .bar { gap: 4px; padding: 0 8px; }
    .label.minor { display: none; }
  }
</style>
