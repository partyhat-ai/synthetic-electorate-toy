<script lang="ts">
  // The election's map, small: one tile per state, in the colour of whoever
  // carried it. After a rerun, a flipped state carries a dot (black at 50%) inside its
  // tile (the page's "● n flipped" beside the map is its key). A figure, not a
  // control — the words around it carry the detail. Pointing at a tile names
  // it: a flat black label over it, set flush left (Vignelli: one face, two
  // weights, no ornament) — the state, then its electoral votes and who won.
  // The hover follows the grid cell under the pointer, so the gaps between
  // tiles never drop it; a tap does the same on touch.
  import { GRID, STATES } from './geo';
  import { bucketOf, type Colors, type MapState, type Names } from './types';

  interface Props {
    year: number;
    states?: readonly MapState[];
    /** Candidate bucket → fill. */
    colors: Colors;
    /** Candidate bucket → surname. */
    names: Names;
    label?: string;
    tile?: number;
    gap?: number;
  }
  let { year, states = [], colors, names, label = '', tile = 13, gap = 2 }: Props = $props();

  function detailOf(r: MapState | undefined): string {
    if (!r) return 'No electoral votes';
    const key = bucketOf(r.won);
    const who = key === 'O' ? names.O || 'Other' : (names[key] ?? '');
    const votes = r.ev ? `${r.ev} electoral vote${r.ev === 1 ? '' : 's'}` : '';
    return [votes, r.flipped ? `flipped to ${who}` : who].filter(Boolean).join(' · ');
  }

  const byCode = $derived(new Map(states.map((s) => [s.code, s])));
  const tiles = $derived(
    STATES.filter((s) => s.first <= year).map((s) => {
      const r = byCode.get(s.code);
      return {
        ...s,
        x: s.col * (tile + gap),
        y: s.row * (tile + gap),
        fill: r ? colors[bucketOf(r.won)] : null,
        flipped: !!r?.flipped,
        detail: detailOf(r),
      };
    }),
  );
  const w = $derived(GRID.cols * (tile + gap) - gap);
  const h = $derived(GRID.rows * (tile + gap) - gap);
  const byCell = $derived(new Map(tiles.map((t) => [`${t.row},${t.col}`, t])));

  let svg = $state<SVGSVGElement | null>(null);
  /** A tile's code. */
  let hovered = $state<string | null>(null);
  // Lit: the tile under the pointer. One lit tile gets its label.
  const lit = $derived<readonly string[]>(hovered ? [hovered] : []);
  const hot = $derived(lit.length === 1 ? (tiles.find((t) => t.code === lit[0]) ?? null) : null);
  function point(e: PointerEvent) {
    if (!svg) return;
    const r = svg.getBoundingClientRect();
    const col = Math.floor(((e.clientX - r.left) * (w / r.width) + gap / 2) / (tile + gap));
    const row = Math.floor(((e.clientY - r.top) * (h / r.height) + gap / 2) / (tile + gap));
    hovered = byCell.get(`${row},${col}`)?.code ?? null;
  }
  // The label hangs over the tile, flush with its left edge — or its right,
  // for tiles in the east, so it stays over the map.
  const flushRight = $derived(!!hot && hot.col >= GRID.cols / 2);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<span class="map" onpointermove={point} onpointerdown={point} onpointerleave={() => (hovered = null)}>
  <!-- Pointing at a tile fades the rest back; nothing draws outside a tile. -->
  <svg bind:this={svg} class:hovering={lit.length > 0} viewBox="0 0 {w} {h}" width={w} height={h} role="img" aria-label={label}>
    {#each tiles as t (t.code)}
      <g class="cell" class:hot={lit.includes(t.code)}>
        {#if t.fill}
          <rect x={t.x} y={t.y} width={tile} height={tile} rx="2.5" style:fill={t.fill} class="tile" />
        {:else}
          <rect x={t.x + 0.5} y={t.y + 0.5} width={tile - 1} height={tile - 1} rx="2.5" class="tile none" />
        {/if}
        {#if t.flipped}
          <circle cx={t.x + tile / 2} cy={t.y + tile / 2} r={tile * 0.17} class="flip" />
        {/if}
      </g>
    {/each}
  </svg>
  {#if hot}
    <span
      class="label"
      class:right={flushRight}
      style:left={flushRight ? null : `${hot.x - 2}px`}
      style:right={flushRight ? `${w - hot.x - tile - 2}px` : null}
      style:bottom="{h - hot.y + 6}px"
      aria-hidden="true"
    >
      <span class="name">{hot.name}</span>
      <span class="detail">{hot.detail}</span>
    </span>
  {/if}
</span>

<style>
  .map { position: relative; display: block; cursor: default; touch-action: manipulation; }
  svg { display: block; overflow: visible; }
  .tile { transition: fill 0.4s ease; }
  .none { fill: none; stroke: rgba(0, 0, 0, 0.18); stroke-width: 1; }
  .flip { fill: #00000080; }
  .cell { transition: opacity 0.12s ease; }
  .hovering .cell:not(.hot) { opacity: 0.28; }
  /* The label: black, white type, square, flush left; name over detail. */
  .label {
    position: absolute;
    z-index: 5;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
    padding: 6px 9px 7px;
    background: #000;
    color: #fff;
    white-space: nowrap;
    text-align: left;
    pointer-events: none;
    font-family: 'Geist', -apple-system, 'Helvetica Neue', Helvetica, sans-serif;
  }
  .label.right { align-items: flex-end; text-align: right; }
  .name { font-size: 13px; font-weight: 600; line-height: 1.15; letter-spacing: -0.01em; }
  .detail { font-size: 11px; font-weight: 400; line-height: 1.2; color: rgba(255, 255, 255, 0.7); font-variant-numeric: tabular-nums; }
  @media (prefers-reduced-motion: reduce) {
    .tile, .cell { transition: none; }
  }
</style>
