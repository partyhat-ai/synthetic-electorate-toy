<script lang="ts">
  // A group's name. On a narrow window the word "citizens" is set small and
  // italic (as in "Immigrants not yet citizens"), so the name keeps to one
  // line beside its result; a wide window sets it like the rest.
  let { label }: { label: string } = $props();

  const parts = $derived(label.split(/(\bcitizens\b)/));
</script>

{#each parts as part, i (i)}{#if part === 'citizens'}<span class="small">{part}</span>{:else}{part}{/if}{/each}

<style>
  @media (max-width: 760px) {
    .small { font-size: 8px; font-weight: normal; font-style: italic; }
  }
</style>
