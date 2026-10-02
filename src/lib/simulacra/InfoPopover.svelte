<script lang="ts">
  // An ⓘ button that opens a short explanation — for terms (backtest, held
  // out, leakage) that need a sentence, not a tooltip.
  import { Info } from 'lucide-svelte';
  import type { Snippet } from 'svelte';
  import { toBody } from './actions';

  interface Props {
    label?: string;
    align?: 'start' | 'end';
    children?: Snippet;
  }
  let { label = 'More information', align = 'start', children }: Props = $props();

  let open = $state(false);
  let root = $state<HTMLElement | null>(null);
  let pop = $state<HTMLElement | null>(null);
  const outside = (e: PointerEvent) => {
    if (!open || !root) return;
    const path = e.composedPath();
    if (!path.includes(root) && !(pop && path.includes(pop))) open = false;
  };
  const key = (e: KeyboardEvent) => {
    if (open && e.key === 'Escape') {
      e.stopPropagation();
      open = false;
    }
  };

  // Always on top: the popover is moved to <body> and fixed under its button,
  // so no stacking context in the page (the robot's frame, the time bar on
  // <body>, a filtered wrapper) can cover it.
  let pos = $state({ top: 0, left: 0, right: 0, max: 600 });
  function place(): void {
    const r = root?.getBoundingClientRect();
    if (r) pos = { top: r.bottom + 6, left: r.left - 8, right: innerWidth - r.right - 8, max: innerHeight - r.bottom - 22 };
  }
  $effect(() => {
    if (open) place();
  });
  const replace = () => {
    if (open) place();
  };
</script>

<svelte:window onpointerdown={outside} onkeydown={key} onresize={replace} onscrollcapture={replace} />

<span class="info" bind:this={root}>
  <button type="button" aria-label={label} aria-expanded={open} title={label} onclick={() => (open = !open)}>
    <Info size={18} strokeWidth={2} aria-hidden="true" />
  </button>
  {#if open}
    <div class="pop" role="dialog" aria-label={label} bind:this={pop} use:toBody
      style:top="{pos.top}px" style:max-height="{pos.max}px" style:left={align === 'end' ? 'auto' : `${pos.left}px`} style:right={align === 'end' ? `${pos.right}px` : 'auto'}>
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
    position: fixed;
    width: 340px;
    box-sizing: border-box;
    overflow-y: auto;
    overscroll-behavior: contain;
    padding: 12px 14px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.98);
    border: 0.5px solid rgba(0, 0, 0, 0.2);
    font-size: 12px;
    line-height: 1.45;
    color: rgba(0, 0, 0, 0.78);
    z-index: 2147483647;
    text-align: left;
    font-weight: 400;
    letter-spacing: 0;
    text-transform: none;
    font-family: 'Geist', -apple-system, sans-serif;
  }
  .pop :global(p) { margin: 0 0 8px; }
  .pop :global(p:last-child) { margin-bottom: 0; }
  .pop :global(strong) { color: #000; font-weight: 600; }
  .pop :global(.fine) { font-size: 11px; color: rgba(0, 0, 0, 0.5); }
</style>
