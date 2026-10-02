<script lang="ts">
  // Simulacra Americana: rerun an American presidential election with one
  // fact changed. The page is being rebuilt around that one flow; until it
  // lands, this is the hub's chrome.
  import InfoPopover from '$lib/simulacra/InfoPopover.svelte';
</script>

<svelte:head>
  <title>Simulacra Americana</title>
</svelte:head>

<div class="sa">
  <header class="top">
    <span class="brand">Simulacra Americana</span>
    <InfoPopover label="About Simulacra Americana" align="end">
      <p><strong>Simulacra Americana</strong> reruns American presidential elections with one fact changed.</p>
    </InfoPopover>
  </header>
</div>

<style>
  .sa { position: fixed; inset: 0; overflow-y: auto; background: #e5e5e5; color: #000; }
  .top { display: flex; align-items: center; justify-content: space-between; height: 48px; padding: 0 20px; }
  .brand { font-size: 13px; font-weight: 600; letter-spacing: 0.01em; }
</style>
