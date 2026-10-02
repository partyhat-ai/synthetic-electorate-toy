<script lang="ts">
  // The what-if composer: the suggestions (KindChips) on one row, scrolled
  // sideways, its edges fading where there's more past them (the right edge
  // is Rerun's); your own what-if, the field and Rerun, on the row beneath.
  import { Square } from 'lucide-svelte';
  import KindChips from './KindChips.svelte';
  import type { WhatIf } from './schemas';

  interface Props {
    /** The harness's name, for the field's label. */
    name: string;
    whatIfs?: readonly WhatIf[];
    selected?: readonly string[];
    slice?: string | null;
    ran?: readonly string[];
    /** The typed what-if. */
    value?: string;
    /** The field, for the page to focus. */
    input?: HTMLInputElement | null;
    running?: boolean;
    canRun?: boolean;
    canReset?: boolean;
    /** Something to run since the rerun on show. */
    dirty?: boolean;
    ontoggle?: (key: string) => void;
    onrun?: () => void;
    onstop?: () => void;
    onreset?: () => void;
    onfocus?: (on: boolean) => void;
  }
  let {
    name,
    whatIfs = [],
    selected = [],
    slice = null,
    ran = [],
    value = $bindable(''),
    input = $bindable(null),
    running = false,
    canRun = true,
    canReset = false,
    dirty = true,
    ontoggle,
    onrun,
    onstop,
    onreset,
    onfocus,
  }: Props = $props();

  function submit(e: SubmitEvent) {
    e.preventDefault();
    if (running) onstop?.();
    else onrun?.();
  }
</script>

<form class="compose" aria-label="What-ifs" onsubmit={submit}>
  <KindChips {whatIfs} {selected} {ran} {slice} {running} {ontoggle} />
  <span class="ask">
    <input
      bind:this={input}
      bind:value
      type="text"
      placeholder="What if…"
      aria-label="Tell {name} what to change"
      autocomplete="off"
      enterkeyhint="go"
      disabled={running}
      onfocus={() => onfocus?.(true)}
      onblur={() => onfocus?.(false)}
    />
    {#if canReset && !running}
      <button type="button" class="reset" onclick={() => onreset?.()}>Reset</button>
    {/if}
    <button type="submit" class="run" class:rest={!dirty && !running} disabled={!running && !canRun}>
      {#if running}<Square size={11} strokeWidth={0} fill="currentColor" aria-hidden="true" /> Stop{:else}Rerun{/if}
    </button>
  </span>
</form>

<style>
  /* The suggestions above, the field and Rerun beneath: both rows the
     column's full width, so the chip row ends at Rerun's right edge. */
  .compose { display: flex; flex-direction: column; align-items: stretch; gap: 8px; min-width: 0; }
  /* On the stage the composer pins to the column's floor (WhatIf.svelte). */
  :global(.whatif.stage) .compose { margin-top: auto; }
  .ask { display: flex; align-items: center; gap: 8px; min-width: 0; }
  /* The field: the bubble's grey on a hairline, a caret in the tint, its
     ring turning the tint while typing (the creator-rows search field's
     behaviour). */
  input {
    flex: 1;
    min-width: 0;
    height: 36px;
    padding: 0 14px;
    border: 1px solid var(--separator);
    border-radius: 999px;
    background: var(--bubble);
    color: var(--label);
    caret-color: var(--tint);
    font: inherit;
    font-size: 15px;
    transition: border-color 0.15s ease;
  }
  input::placeholder { color: var(--label-3); }
  input:focus { outline: none; border-color: var(--tint); }
  input:disabled { opacity: 0.6; }
  /* Rerun: the one filled accent, in the brand blue (white label, 4.7:1). */
  .run {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 36px;
    padding: 0 18px;
    border: none;
    border-radius: 999px;
    background: #3876b7;
    color: #fff;
    font: inherit;
    font-size: 15px;
    font-weight: 500;
    cursor: pointer;
  }
  .run:hover { background: #2f66a0; }
  .run:active { background: #285a8e; }
  .run:disabled { opacity: 0.35; cursor: default; background: #3876b7; }
  /* Nothing new to run: at rest, the button dims (pressing it shows the
     rerun already made). It brightens as soon as there's a change. */
  .run.rest { opacity: 0.6; }
  /* Reset sits on the page's light grey, beside the dark field: text only. */
  .reset {
    height: 36px;
    padding: 0 10px;
    border: none;
    background: transparent;
    color: #3876b7;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
    border-radius: 10px;
  }
  .reset:hover { background: rgba(56, 118, 183, 0.08); }
  .reset:active { opacity: 0.6; }
  .run:focus-visible, .reset:focus-visible { outline: 2px solid #3876b7; outline-offset: 2px; }
</style>
