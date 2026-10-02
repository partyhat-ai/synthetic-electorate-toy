<script lang="ts">
  // Simulacra Americana, as two throwaway prototypes behind ?proto=: a, the
  // time map (ProtoA), and c, the electorate (ProtoC). Time-boxed and
  // sharing no code; whichever idea survives is rebuilt properly.
  import InfoPopover from '$lib/simulacra/InfoPopover.svelte';
  import ProtoA from '$lib/simulacra/ProtoA.svelte';
  import ProtoC from '$lib/simulacra/ProtoC.svelte';

  const proto = new URLSearchParams(location.search).get('proto');
</script>

<svelte:head>
  <title>Simulacra Americana</title>
</svelte:head>

<div class="sa">
  <header class="top">
    <span class="brand">Simulacra Americana</span>
    {#if proto === 'a' || proto === 'c'}<span class="pill">Prototype {proto.toUpperCase()} · sample data</span>{/if}
    <InfoPopover label="About Simulacra Americana" align="end">
      <p><strong>Simulacra Americana</strong> rebuilds each presidential election's electorate and lets synthetic voters call it, beside what happened.</p>
      <p>These are prototypes: every number on them is invented.</p>
    </InfoPopover>
  </header>
  <main class="main">
    {#if proto === 'a'}
      <ProtoA />
    {:else if proto === 'c'}
      <ProtoC />
    {:else}
      <ul class="index">
        <li><a href="?proto=a">Prototype A: the time map</a></li>
        <li><a href="?proto=c">Prototype C: the electorate</a></li>
      </ul>
    {/if}
  </main>
</div>

<style>
  .sa { position: fixed; inset: 0; overflow-y: auto; background: #e5e5e5; color: #000; }
  .top { display: flex; align-items: center; gap: 12px; height: 48px; padding: 0 20px; }
  .brand { margin-right: auto; font-size: 13px; font-weight: 600; letter-spacing: 0.01em; }
  .pill { padding: 2px 9px; border-radius: 999px; background: rgba(0, 0, 0, 0.08); font-size: 11px; font-weight: 500; color: rgba(0, 0, 0, 0.6); }
  .main { max-width: 960px; margin: 0 auto; padding: 8px 24px 48px; }
  .index { display: flex; flex-direction: column; gap: 8px; margin: 40px 0; padding: 0; list-style: none; font-size: 15px; }
  .index a { color: #3876b7; }
</style>
