<script lang="ts">
  // The time map: one square tile per state on a 12 × 8 grid, filled with the
  // model's call and ringed with the actual winner, so a miss is a tile whose
  // ring and fill disagree (it also carries a cross). States not yet in the
  // Union are blank; states that sat an election out are hatched. Click a
  // tile to inspect it.
  import { absentReason, GRID, STATES } from './geo';

  /** One state's result: who actually carried it and who the model called. */
  interface TileResult {
    readonly code: string;
    readonly actual: 'A' | 'B' | 'O';
    readonly call: 'A' | 'B' | 'O';
    readonly margin: number;
  }

  interface Props {
    year: number;
    results: readonly TileResult[];
    /** Party colour per key. */
    colors: Readonly<Record<'A' | 'B' | 'O', string>>;
    selected?: string | null;
    /** State codes to emphasize (a search). */
    matches?: ReadonlySet<string> | null;
    onselect?: (code: string) => void;
  }
  let { year, results, colors, selected = null, matches = null, onselect }: Props = $props();

  const TILE = 34;
  const GAP = 4;
  const byCode = $derived(new Map(results.map((r) => [r.code, r])));
  const tiles = $derived(
    STATES.map((s) => {
      const r = byCode.get(s.code);
      const inUnion = s.first <= year;
      return {
        ...s,
        x: s.col * (TILE + GAP),
        y: s.row * (TILE + GAP),
        inUnion,
        absent: inUnion ? absentReason(s.code, year) : null,
        result: r ?? null,
        miss: !!r && r.call !== r.actual,
      };
    }),
  );
  const w = GRID.cols * (TILE + GAP) - GAP;
  const h = GRID.rows * (TILE + GAP) - GAP;
  const misses = $derived(tiles.filter((t) => t.miss).length);

  function titleOf(t: (typeof tiles)[number]): string {
    if (!t.inUnion) return `${t.name}: not yet a state`;
    if (t.absent) return `${t.name}: ${t.absent}`;
    if (!t.result) return `${t.name}: no result yet`;
    const verdict = t.miss ? 'missed' : 'called right';
    return `${t.name}: model ${t.result.call}, actual ${t.result.actual} (${verdict}, ${t.result.margin.toFixed(1)} points)`;
  }
</script>

<figure class="time-map">
  <svg viewBox="-4 -4 {w + 8} {h + 8}" role="group" aria-label="States in {year}: {misses} missed">
    <defs>
      <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="6" class="hatch" />
      </pattern>
    </defs>
    {#each tiles as t (t.code)}
      {#if t.inUnion}
        <g
          class="tile"
          class:selected={selected === t.code}
          class:faded={!!matches && !matches.has(t.code)}
          role="button"
          tabindex="0"
          aria-label={titleOf(t)}
          onclick={() => onselect?.(t.code)}
          onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && onselect?.(t.code)}
        >
          <title>{titleOf(t)}</title>
          {#if t.absent}
            <rect x={t.x} y={t.y} width={TILE} height={TILE} rx="5" fill="url(#hatch)" class="absent" />
          {:else if t.result}
            <rect x={t.x} y={t.y} width={TILE} height={TILE} rx="5" style:fill={colors[t.result.call]} />
            <rect x={t.x + 1.5} y={t.y + 1.5} width={TILE - 3} height={TILE - 3} rx="4" class="ring" style:stroke={colors[t.result.actual]} />
            {#if t.miss}
              <path d="M{t.x + 10} {t.y + 10} l14 14 m0 -14 l-14 14" class="cross" />
            {/if}
          {:else}
            <rect x={t.x} y={t.y} width={TILE} height={TILE} rx="5" class="empty" />
          {/if}
          <text x={t.x + TILE / 2} y={t.y + TILE - 5} class="code">{t.code}</text>
        </g>
      {/if}
    {/each}
  </svg>
  <figcaption>Fill: the model's call. Ring: who actually won. A cross marks a miss.</figcaption>
</figure>

<style>
  .time-map { margin: 0; }
  svg { width: 100%; height: auto; display: block; }
  .tile { cursor: pointer; outline: none; }
  .tile:focus-visible rect:first-of-type, .tile.selected rect:first-of-type { stroke: #000; stroke-width: 2.5; }
  .tile.faded { opacity: 0.25; }
  .ring { fill: none; stroke-width: 3; }
  .cross { stroke: #fff; stroke-width: 2.5; stroke-linecap: round; }
  .empty { fill: rgba(0, 0, 0, 0.06); }
  .absent { stroke: rgba(0, 0, 0, 0.15); }
  .hatch { stroke: rgba(0, 0, 0, 0.18); stroke-width: 2; }
  .code { font-size: 8px; text-anchor: middle; fill: rgba(255, 255, 255, 0.85); pointer-events: none; }
  figcaption { margin-top: 8px; font-size: 12px; color: rgba(0, 0, 0, 0.55); }
</style>
