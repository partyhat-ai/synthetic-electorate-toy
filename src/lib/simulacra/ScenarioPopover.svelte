<script lang="ts">
  // What-if scenarios for the time map: a popover of checkboxes, each with
  // the elections it applies to. Chosen scenarios ride along with the year
  // as a set of keys; the model compares them against its own baseline.
  import { FlaskConical } from 'lucide-svelte';
  import { BUILTIN_SCENARIOS } from './geo';

  interface Props {
    /** Chosen scenario keys. */
    chosen: readonly string[];
    onchange?: (keys: string[]) => void;
  }
  let { chosen, onchange }: Props = $props();

  let open = $state(false);
  let root = $state<HTMLElement | null>(null);
  const toggle = (key: string) =>
    onchange?.(chosen.includes(key) ? chosen.filter((k) => k !== key) : [...chosen, key]);
  const outside = (e: PointerEvent) => {
    if (open && root && !e.composedPath().includes(root)) open = false;
  };
  const span = (from: number, to: number) => (from === to ? String(from) : `${from}–${to}`);
</script>

<svelte:window onpointerdown={outside} onkeydown={(e) => e.key === 'Escape' && (open = false)} />

<span class="scenarios" bind:this={root}>
  <button type="button" class="open" aria-expanded={open} onclick={() => (open = !open)}>
    <FlaskConical size={15} aria-hidden="true" />
    Scenarios{#if chosen.length}<span class="n">{chosen.length}</span>{/if}
  </button>
  {#if open}
    <div class="pop" role="dialog" aria-label="Scenarios">
      {#each BUILTIN_SCENARIOS as s (s.key)}
        <label class="row">
          <input type="checkbox" checked={chosen.includes(s.key)} onchange={() => toggle(s.key)} />
          <span>
            <span class="label">{s.label}</span>
            <span class="detail">{s.detail} Applies to {span(s.from, s.to)}.</span>
          </span>
        </label>
      {/each}
      {#if chosen.length}<button type="button" class="clear" onclick={() => onchange?.([])}>Clear</button>{/if}
    </div>
  {/if}
</span>

<style>
  .scenarios { position: relative; display: inline-flex; }
  .open {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 30px;
    padding: 0 12px;
    border: 1px solid rgba(0, 0, 0, 0.16);
    border-radius: 999px;
    background: #fff;
    font: inherit;
    font-size: 13px;
    cursor: pointer;
  }
  .n { min-width: 18px; padding: 0 5px; border-radius: 999px; background: #111; color: #fff; font-size: 11px; }
  .pop {
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    z-index: 20;
    width: 320px;
    padding: 8px;
    border-radius: 12px;
    background: #fff;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.16), 0 0 0 0.5px rgba(0, 0, 0, 0.2);
  }
  .row { display: flex; gap: 10px; padding: 8px; border-radius: 8px; cursor: pointer; }
  .row:hover { background: rgba(0, 0, 0, 0.04); }
  .label { display: block; font-size: 13px; font-weight: 600; }
  .detail { display: block; margin-top: 2px; font-size: 12px; color: rgba(0, 0, 0, 0.6); }
  .clear { margin: 4px 8px; padding: 0; border: none; background: none; font: inherit; font-size: 12px; color: #3876b7; cursor: pointer; }
</style>
