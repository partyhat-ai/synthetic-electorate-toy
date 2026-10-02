<script lang="ts">
  // A group's name. On a narrow window the word "citizens" is set small and
  // italic, without the parentheses some years' names put round it ("Men
  // outside the South (citizens)", 1972 on), so the name keeps to one line
  // beside its result; a wide window sets the name as it is.
  let { label }: { label: string } = $props();

  const parts = $derived(label.split(/(\(citizens\)|\bcitizens\b)/));
</script>

{#each parts as part, i (i)}{#if part === '(citizens)'}<span class="paren">(</span><span class="small">citizens</span><span class="paren">)</span>{:else if part === 'citizens'}<span class="small">{part}</span>{:else}{part}{/if}{/each}

<style>
  @media (max-width: 760px) {
    .small { font-size: 8px; font-weight: normal; font-style: italic; }
    .paren { display: none; }
  }
</style>
