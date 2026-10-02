<script lang="ts">
  // The election's map, small: one tile per state, in the colour of whoever
  // carried it. After a rerun, the states that flipped pulse. A figure, not a
  // control — the words around it carry the detail, and each tile names
  // itself in a tooltip.
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

  function titleOf(name: string, r: MapState | undefined): string {
    if (!r) return `${name} · no electoral votes`;
    const key = bucketOf(r.won);
    const who = key === 'O' ? names.O || 'Other' : (names[key] ?? '');
    const votes = r.ev ? ` · ${r.ev} electoral vote${r.ev === 1 ? '' : 's'}` : '';
    return `${name}${votes} · ${who}${r.flipped ? ' (flipped)' : ''}`;
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
        title: titleOf(s.name, r),
      };
    }),
  );
  const w = $derived(GRID.cols * (tile + gap) - gap);
  const h = $derived(GRID.rows * (tile + gap) - gap);
</script>

<svg viewBox="0 0 {w} {h}" width={w} height={h} role="img" aria-label={label}>
  {#each tiles as t (t.code)}
    <g>
      <title>{t.title}</title>
      {#if t.fill}
        <rect x={t.x} y={t.y} width={tile} height={tile} rx="2.5" style:fill={t.fill} class="tile" />
      {:else}
        <rect x={t.x + 0.5} y={t.y + 0.5} width={tile - 1} height={tile - 1} rx="2.5" class="tile none" />
      {/if}
      {#if t.flipped}
        <rect x={t.x - 1.5} y={t.y - 1.5} width={tile + 3} height={tile + 3} rx="4" class="flip" />
      {/if}
    </g>
  {/each}
</svg>

<style>
  svg { display: block; overflow: visible; }
  .tile { transition: fill 0.4s ease; }
  .none { fill: none; stroke: rgba(0, 0, 0, 0.18); stroke-width: 1; }
  .flip {
    fill: none;
    stroke: #00000080;
    stroke-width: 1.5;
    animation: pulse 1.4s ease-in-out infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 0.9; }
    50% { opacity: 0.15; }
  }
  @media (prefers-reduced-motion: reduce) {
    .tile { transition: none; }
    .flip { animation: none; opacity: 0.9; }
  }
</style>
