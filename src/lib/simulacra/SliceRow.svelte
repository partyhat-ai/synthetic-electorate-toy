<script lang="ts">
  // One group of voters as a row of fifty people: the winner's voters from
  // the left, the runner-up's from the right, and between them everyone else
  // — third parties, those who stayed home, those who couldn't vote. A rerun
  // recolours the dots in place, so a franchise change reads as the gap in
  // the middle filling in. Tapping a row picks the group: the harness then
  // introduces someone from it (the page's bubble).
  import { fmtCompact } from './format';
  import type { Slice } from './schemas';
  import type { Colors, Names } from './types';

  interface Props {
    slice: Slice;
    /** The same group in history, to show what changed. */
    base?: Slice | null | undefined;
    colors: Colors;
    names: Names;
    /** The group the harness is talking about. */
    open?: boolean;
    /** Showing a rerun, not history. */
    rerun?: boolean;
    /** A chosen what-if reaches this group. */
    lit?: boolean;
    /** The row was tapped. */
    ontoggle?: () => void;
  }
  let { slice, base = null, colors, names, open = false, rerun = false, lit = false, ontoggle }: Props = $props();

  const N = 50;
  /** Left to right: A, O, home, barred, B. */
  const KINDS = ['A', 'O', 'home', 'barred', 'B'] as const;
  type Counts = readonly [number, number, number, number, number];

  // Largest-remainder counts, left to right: A, O, home, barred, B.
  function counts(s: Slice): Counts {
    const parts = KINDS.map((k) => Math.max(0, s[k] || 0));
    const total = parts.reduce((a, b) => a + b, 0) || 1;
    const raw = parts.map((x) => (x / total) * N);
    const out = raw.map(Math.floor);
    let left = N - out.reduce((a, b) => a + b, 0);
    const order = raw.map((x, i) => [x - Math.floor(x), i] as const).sort((a, b) => b[0] - a[0]);
    for (const [, i] of order) {
      if (left > 0) {
        out[i] = (out[i] ?? 0) + 1;
        left--;
      }
    }
    return [out[0] ?? 0, out[1] ?? 0, out[2] ?? 0, out[3] ?? 0, out[4] ?? 0];
  }
  const dots = $derived(KINDS.flatMap((k, j) => Array.from({ length: counts(slice)[j] ?? 0 }, () => k)));

  const voted = (s: Slice) => (s.A || 0) + (s.B || 0) + (s.O || 0);
  const pct = (x: number) => `${Math.round(x * 100)}%`;
  function lead(s: Slice): string {
    const v = voted(s);
    if (v < 0.02) return s.barred >= 0.5 ? 'Couldn’t vote' : 'Stayed home';
    let k: 'A' | 'B' | 'O' = 'O';
    if (s.A >= s.B && s.A >= s.O) k = 'A';
    else if (s.B >= s.O) k = 'B';
    return `${names[k] || 'Other'} ${pct(s[k] / v)}`;
  }
  function caption(s: Slice): string {
    const people = `${fmtCompact((s.adults || 0) * 1e6)} adults`;
    if (s.barred >= 0.95) return `${people} · couldn’t vote`;
    if (s.barred >= 0.5) return `${people} · ${Math.round(s.barred * 10)} in 10 couldn’t vote`;
    if (s.barred >= 0.1) return `${people} · ${pct(s.barred)} couldn’t vote`;
    return `${people} · ${pct(voted(s))} voted`;
  }
  // How many could vote, and did.
  function turnout(s: Slice): string {
    if (s.barred >= 0.95) return 'couldn’t vote';
    if (s.barred >= 0.5) return `${Math.round(s.barred * 10)} in 10 couldn’t vote`;
    return `${pct(voted(s))} voted`;
  }
  const main = $derived(lead(slice));
  // Under a rerun, what this group was in history: its split if that
  // changed, else its turnout if that did.
  function wasOf(): string {
    if (!rerun || !base) return '';
    if (lead(base) !== main) return `was ${lead(base)}`;
    if (Math.abs(voted(base) - voted(slice)) > 0.02) return `was ${turnout(base)}`;
    return '';
  }
  const was = $derived(wasOf());
</script>

<div class="row" class:open class:lit style:--a={colors.A} style:--b={colors.B} style:--o={colors.O}>
  <button type="button" class="head" aria-pressed={open} onclick={() => ontoggle?.()}>
    <span class="who">
      <span class="label">{slice.label}</span>
      <span class="cap">{caption(slice)}</span>
    </span>
    <svg class="strip" viewBox="0 0 {N * 10} 10" preserveAspectRatio="xMinYMid meet" aria-hidden="true">
      {#each dots as d, i (i)}
        <circle cx={i * 10 + 5} cy="5" class="dot {d}" style:transition-delay="{Math.min(i, N - 1 - i) * 9}ms" />
      {/each}
    </svg>
    <span class="val">
      <span class="main">{main}</span>
      {#if was}<span class="was">{was}</span>{/if}
    </span>
  </button>
</div>

<style>
  .row { position: relative; border-radius: 12px; transition: background-color 0.15s ease; }
  .row.open .head { background: rgba(0, 0, 0, 0.07); }
  /* A chosen what-if reaches this group: a mark at its leading edge. */
  .row.lit::before {
    content: '';
    position: absolute;
    left: -10px;
    top: 14px;
    width: 3px;
    height: 22px;
    border-radius: 2px;
    background: rgba(0, 0, 0, 0.7);
  }
  .head {
    display: grid;
    grid-template-columns: minmax(160px, 212px) minmax(0, 1fr) 124px;
    align-items: center;
    gap: 16px;
    width: 100%;
    min-height: 42px;
    padding: 3px 10px;
    border: none;
    border-radius: 12px;
    background: transparent;
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;
  }
  .head:hover { background: rgba(0, 0, 0, 0.04); }
  .head:focus-visible { outline: 2px solid #3876b7; outline-offset: 1px; }
  .who { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .label { font-size: 14px; font-weight: 600; line-height: 1.25; }
  .cap { font-size: 12px; color: rgba(0, 0, 0, 0.55); font-variant-numeric: tabular-nums; }
  .strip { width: 100%; height: auto; display: block; overflow: visible; }
  .dot {
    r: 3.9;
    transition: fill 0.4s ease, stroke 0.4s ease, r 0.4s ease;
  }
  .dot.A { fill: var(--a); stroke: transparent; }
  .dot.B { fill: var(--b); stroke: transparent; }
  .dot.O { fill: var(--o); stroke: transparent; }
  .dot.home { fill: transparent; stroke: rgba(0, 0, 0, 0.42); stroke-width: 1.2; r: 3.3; }
  .dot.barred { fill: rgba(0, 0, 0, 0.2); stroke: transparent; r: 1.7; }
  .val { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; text-align: right; }
  .main { font-size: 13px; font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .was { font-size: 12px; color: rgba(0, 0, 0, 0.5); font-variant-numeric: tabular-nums; white-space: nowrap; }
  @media (max-width: 700px) {
    .head { grid-template-columns: minmax(0, 1fr) auto; row-gap: 8px; }
    .strip { grid-column: 1 / -1; grid-row: 2; }
    .row.lit::before { left: -6px; }
  }
  @media (prefers-reduced-motion: reduce) {
    .dot, .row { transition: none !important; }
  }
</style>
