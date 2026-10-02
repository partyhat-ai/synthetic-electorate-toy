<script lang="ts">
  // A run of text with its places (places.ts) made pointable: hovering one
  // lights its tiles on the map. The text stays ink; a blue dotted underline says so.
  import { onDestroy } from 'svelte';
  import { hoverPlaces, segments } from './places';

  let { text = '' }: { text?: string } = $props();
  const parts = $derived(segments(text));
  let mine = false;
  const on = (codes: readonly string[]) => {
    mine = true;
    hoverPlaces.set(codes);
  };
  const off = () => {
    if (mine) {
      mine = false;
      hoverPlaces.set([]);
    }
  };
  onDestroy(off);
</script>

{#each parts as p, i (i)}{#if p.codes}{@const codes = p.codes}<!-- svelte-ignore a11y_no_static_element_interactions --><span class="place" class:region={codes.length > 1} onmouseenter={() => on(codes)} onmouseleave={off}>{p.t}</span>{:else}{p.t}{/if}{/each}

<style>
  /* A blue dotted underline (systemBlue), heavier than a hairline, solid on hover. */
  .place {
    text-decoration: underline dotted #007aff;
    text-decoration-thickness: 2px;
    text-underline-offset: 3px;
    text-decoration-skip-ink: none;
    cursor: default;
  }
  .place:hover { text-decoration-style: solid; }
  /* A region (several states): the dots in the text's own colour, not blue. */
  .place.region, :global(.sa.dark) .place.region { text-decoration-color: currentColor; }
  /* Under the Rerun view's filter (.sa.dark .main: invert, hue-rotate 180°,
     saturate 1.5) #4696f5 comes out as dark mode's systemBlue #0a84ff
     (solved through the filter matrices; #007aff itself would read cyan). */
  :global(.sa.dark) .place { text-decoration-color: #4696f5; }
</style>
