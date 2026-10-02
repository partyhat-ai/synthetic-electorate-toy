<script lang="ts">
  // The electorate's make-up as one bar: voted, stayed home, turned away,
  // couldn't vote, each a share of all adults, labelled where it fits.
  import { fmtPct } from './format';

  interface Part {
    readonly key: string;
    readonly label: string;
    readonly share: number;
    readonly color: string;
  }
  let { parts }: { parts: readonly Part[] } = $props();
  const total = $derived(parts.reduce((a, p) => a + p.share, 0) || 1);
</script>

<div class="stack" role="img" aria-label={parts.map((p) => `${p.label} ${fmtPct(p.share / total)}`).join(', ')}>
  {#each parts as p (p.key)}
    <span class="part" style:flex-grow={p.share} style:background={p.color} title="{p.label}: {fmtPct(p.share / total)}">
      {#if p.share / total > 0.1}<span class="in">{fmtPct(p.share / total)}</span>{/if}
    </span>
  {/each}
</div>

<style>
  .stack { display: flex; height: 24px; overflow: hidden; border-radius: 6px; background: rgba(0, 0, 0, 0.06); }
  .part { flex-basis: 0; min-width: 2px; display: flex; align-items: center; justify-content: center; transition: flex-grow 0.4s ease; }
  .in { font-size: 11px; font-weight: 600; color: #fff; text-shadow: 0 0 2px rgba(0, 0, 0, 0.4); }
  @media (prefers-reduced-motion: reduce) {
    .part { transition: none; }
  }
</style>
