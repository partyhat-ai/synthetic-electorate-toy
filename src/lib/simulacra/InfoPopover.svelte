<script lang="ts">
  // An ⓘ button that opens a short explanation — for terms (backtest, held
  // out, leakage) that need a sentence, not a tooltip.
  import { Info } from 'lucide-svelte';
  import type { Snippet } from 'svelte';

  interface Props {
    label?: string;
    align?: 'start' | 'end';
    children?: Snippet;
  }
  let { label = 'More information', align = 'start', children }: Props = $props();

  let open = $state(false);
  let root = $state<HTMLElement | null>(null);
  const outside = (e: PointerEvent) => {
    if (open && root && !e.composedPath().includes(root)) open = false;
  };
  const key = (e: KeyboardEvent) => {
    if (open && e.key === 'Escape') {
      e.stopPropagation();
      open = false;
    }
  };
</script>

<svelte:window onpointerdown={outside} onkeydown={key} />

<span class="info" bind:this={root}>
  <button type="button" aria-label={label} aria-expanded={open} title={label} onclick={() => (open = !open)}>
    <Info size={18} strokeWidth={2} aria-hidden="true" />
  </button>
  {#if open}
    <div class="pop" class:end={align === 'end'} role="dialog" aria-label={label}>
      {@render children?.()}
    </div>
  {/if}
</span>

<style>
  .info { position: relative; display: inline-flex; }
  button {
    width: 28px;
    height: 28px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    border: none;
    border-radius: 999px;
    background: transparent;
    color: rgba(0, 0, 0, 0.45);
    cursor: pointer;
  }
  button:hover { color: #000; background: rgba(0, 0, 0, 0.06); }
  button:focus-visible { outline: 2px solid #3876b7; outline-offset: 1px; }
  .pop {
    position: absolute;
    top: calc(100% + 6px);
    left: -8px;
    width: 300px;
    padding: 12px 14px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.98);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.16), 0 0 0 0.5px rgba(0, 0, 0, 0.2);
    font-size: 12px;
    line-height: 1.45;
    color: rgba(0, 0, 0, 0.78);
    z-index: 40;
    text-align: left;
    font-weight: 400;
    letter-spacing: 0;
    text-transform: none;
    font-family: 'Geist', -apple-system, sans-serif;
  }
  .pop.end { left: auto; right: -8px; }
  .pop :global(p) { margin: 0 0 8px; }
  .pop :global(p:last-child) { margin-bottom: 0; }
  .pop :global(strong) { color: #000; font-weight: 600; }
</style>
