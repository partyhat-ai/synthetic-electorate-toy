<script lang="ts">
  // The electorate as a cloud of a hundred dots, each a hundredth of the
  // adults: those who voted at the centre, then those who stayed home, those
  // turned away at the polls, and out at the edge those who couldn't vote
  // at all. The latest change to the franchise captions it.
  import { fmtCompact } from './format';
  import { FRANCHISE_EVENTS } from './geo';

  /** Shares of all adults, summing to 1. */
  interface Electorate {
    readonly voted: number;
    readonly home: number;
    readonly away: number;
    readonly barred: number;
  }

  interface Props {
    year: number;
    electorate: Electorate;
    /** Adults, all told. */
    adults: number;
  }
  let { year, electorate, adults }: Props = $props();

  const N = 100;
  /** Centre out: voted, stayed home, turned away, couldn't vote. */
  const KINDS = ['voted', 'home', 'away', 'barred'] as const;
  const LABEL: Readonly<Record<(typeof KINDS)[number], string>> = {
    voted: 'Voted',
    home: 'Stayed home',
    away: 'Turned away',
    barred: 'Couldn’t vote',
  };

  // Largest-remainder counts, so the dots always add up to N.
  function counts(e: Electorate): number[] {
    const parts = KINDS.map((k) => Math.max(0, e[k] || 0));
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
    return out;
  }

  // A sunflower spiral: dot i sits at radius √i, so the first dots (who
  // voted) fill the centre and each kind wraps the last.
  const GOLDEN = Math.PI * (3 - Math.sqrt(5));
  const dots = $derived.by(() => {
    const n = counts(electorate);
    const kinds = KINDS.flatMap((k, j) => Array.from({ length: n[j] ?? 0 }, () => k));
    return kinds.map((kind, i) => ({ kind, x: 100 + 9 * Math.sqrt(i + 0.5) * Math.cos(i * GOLDEN), y: 100 + 9 * Math.sqrt(i + 0.5) * Math.sin(i * GOLDEN) }));
  });
  const latest = $derived(FRANCHISE_EVENTS.filter((ev) => ev.year <= year).at(-1) ?? null);
</script>

<figure class="cloud">
  <svg viewBox="0 0 200 200" role="img" aria-label="The electorate in {year}, in hundredths of all adults">
    {#each dots as d, i (i)}
      <circle cx={d.x} cy={d.y} class="dot {d.kind}" />
    {/each}
  </svg>
  <figcaption>
    <ul class="key">
      {#each KINDS as k (k)}
        <li><span class="swatch {k}"></span>{LABEL[k]} <b>{fmtCompact(adults * electorate[k])}</b></li>
      {/each}
    </ul>
    {#if latest}<p class="rule">Since {latest.year}: {latest.label}. {latest.detail}</p>{/if}
  </figcaption>
</figure>

<style>
  .cloud { display: grid; grid-template-columns: minmax(0, 320px) minmax(0, 1fr); align-items: center; gap: 28px; margin: 0; }
  svg { width: 100%; height: auto; display: block; }
  .dot { r: 3.6; transition: fill 0.4s ease, r 0.4s ease; }
  .dot.voted { fill: #2a78d6; }
  .dot.home { fill: transparent; stroke: rgba(0, 0, 0, 0.42); stroke-width: 1.1; r: 3.1; }
  .dot.away { fill: #eb6834; }
  .dot.barred { fill: rgba(0, 0, 0, 0.2); r: 1.8; }
  .key { display: flex; flex-direction: column; gap: 6px; margin: 0; padding: 0; list-style: none; font-size: 13px; }
  .key li { display: flex; align-items: center; gap: 8px; }
  .key b { margin-left: auto; font-weight: 600; font-variant-numeric: tabular-nums; }
  .swatch { width: 10px; height: 10px; border-radius: 999px; flex: none; }
  .swatch.voted { background: #2a78d6; }
  .swatch.home { box-sizing: border-box; border: 1.2px solid rgba(0, 0, 0, 0.42); }
  .swatch.away { background: #eb6834; }
  .swatch.barred { width: 5px; height: 5px; margin: 0 2.5px; background: rgba(0, 0, 0, 0.2); }
  .rule { margin: 14px 0 0; font-size: 12px; line-height: 1.45; color: rgba(0, 0, 0, 0.6); }
  @media (prefers-reduced-motion: reduce) {
    .dot { transition: none; }
  }
</style>
