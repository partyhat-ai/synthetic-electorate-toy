<script lang="ts">
  // The what-if suggestions: one row of chips, scrolled sideways (a vertical
  // wheel scrolls it too, while it can go further that way); each edge fades
  // while there's more past it. Chosen and run: filled, a check. Chosen, not
  // run yet: a tint ring and a dot — queued for the next Rerun.
  import { Check, Dot, MapPin, Newspaper, Vote } from 'lucide-svelte';
  import type { Kind, WhatIf } from './schemas';
  import { KIND_LABEL, reaches } from './whatif';

  interface Props {
    whatIfs?: readonly WhatIf[];
    /** Chosen what-if keys. */
    selected?: readonly string[];
    /** The what-ifs in the rerun on show. */
    ran?: readonly string[];
    /** An open group: the what-ifs that reach it stand out. */
    slice?: string | null;
    running?: boolean;
    ontoggle?: (key: string) => void;
  }
  let { whatIfs = [], selected = [], ran = [], slice = null, running = false, ontoggle }: Props = $props();

  const KIND_ICON: Readonly<Record<Kind, typeof Vote>> = {
    franchise: Vote,
    population: MapPin,
    issue: Newspaper,
    candidate: Vote,
  };

  let chipsEl = $state<HTMLElement | null>(null);
  let chipsL = $state(false);
  let chipsR = $state(false);
  function chipEdges() {
    if (!chipsEl) return;
    chipsL = chipsEl.scrollLeft > 1;
    chipsR = chipsEl.scrollWidth - chipsEl.scrollLeft - chipsEl.clientWidth > 1;
  }
  function chipRow(node: HTMLElement) {
    const r = new ResizeObserver(chipEdges);
    r.observe(node);
    const wheel = (e: WheelEvent) => {
      if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
      const max = node.scrollWidth - node.clientWidth;
      if (max <= 0 || (e.deltaY < 0 && node.scrollLeft <= 0) || (e.deltaY > 0 && node.scrollLeft >= max - 1)) return;
      e.preventDefault();
      node.scrollLeft += e.deltaY;
    };
    node.addEventListener('wheel', wheel, { passive: false });
    return {
      destroy() {
        r.disconnect();
        node.removeEventListener('wheel', wheel);
      },
    };
  }
  // New chips (another year, a built what-if): measure the edges again.
  $effect.pre(() => {
    void whatIfs;
    queueMicrotask(chipEdges);
  });
</script>

<div class="chips" class:l={chipsL} class:r={chipsR} bind:this={chipsEl} use:chipRow onscroll={chipEdges}>
  {#each whatIfs as w (w.key)}
    {@const on = selected.includes(w.key)}
    {@const pending = on && !ran.includes(w.key)}
    {@const Icon = KIND_ICON[w.kind]}
    <button type="button" class="chip" class:on class:pending class:dim={!reaches(w, slice)} aria-pressed={on} disabled={running}
      title="{KIND_LABEL[w.kind]}: {w.detail}{pending ? ' (not run yet)' : ''}" onclick={() => ontoggle?.(w.key)}>
      {#if pending}<Dot size={14} strokeWidth={5} aria-hidden="true" />{:else if on}<Check size={14} strokeWidth={2.4} aria-hidden="true" />{:else}<Icon size={14} strokeWidth={2} aria-hidden="true" />{/if}
      {w.label}
    </button>
  {/each}
</div>

<style>
  /* One row, scrolled sideways, no scrollbar. Each edge fades (a 40px band,
     easing in via @property) only while there's more past it. The 4px of
     padding top and bottom keeps a chip's focus ring inside the clip. */
  @property --fl { syntax: '<length>'; inherits: false; initial-value: 0px; }
  @property --fr { syntax: '<length>'; inherits: false; initial-value: 0px; }
  .chips {
    --band: 40px;
    display: flex;
    gap: 8px;
    min-width: 0;
    margin: -4px 0;
    padding: 4px 0;
    overflow-x: auto;
    overflow-y: hidden;
    overscroll-behavior-x: contain;
    scrollbar-width: none;
    -webkit-mask-image: linear-gradient(to right, transparent, #000 var(--fl), #000 calc(100% - var(--fr)), transparent);
    mask-image: linear-gradient(to right, transparent, #000 var(--fl), #000 calc(100% - var(--fr)), transparent);
    transition: --fl 0.25s ease, --fr 0.25s ease;
  }
  .chips::-webkit-scrollbar { display: none; }
  .chips.l { --fl: var(--band); }
  .chips.r { --fr: var(--band); }
  .chips .chip { flex: none; }
  /* The what-ifs: Messages' white capsules at rest, label text, glyphs in
     the tint; hover lifts one a hair onto a soft shadow; a press dims it to
     systemGray5. Chosen is filled: the tint, a white label and a check. */
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 36px;
    padding: 0 14px 0 12px;
    border: none;
    border-radius: 999px;
    background: #fff;
    color: var(--label);
    font: inherit;
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;
    cursor: pointer;
    transition: background-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s cubic-bezier(0.2, 0.9, 0.3, 1.3), opacity 0.15s ease, color 0.12s ease;
  }
  .chip :global(svg) { color: var(--tint); flex: none; transition: color 0.18s ease; }
  /* Hover (pointers only): the chip lifts a hair onto a soft shadow. */
  @media (hover: hover) {
    .chip:hover:not(:disabled):not(.on) {
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06), 0 6px 14px -6px rgba(0, 0, 0, 0.18);
      transform: translateY(-1px);
    }
  }
  .chip:active:not(:disabled):not(.on) { background: var(--fill-press); transform: scale(0.97); box-shadow: none; }
  .chip.on { background: var(--tint); color: #fff; }
  .chip.on :global(svg) { color: #fff; }
  /* Chosen, not run yet: still the rest white, ringed in the tint, a dot in it. */
  .chip.on.pending { background: #fff; color: var(--label); box-shadow: inset 0 0 0 1.5px var(--tint); }
  .chip.on.pending :global(svg) { color: var(--tint); }
  .chip.dim { opacity: 0.45; }
  .chip:disabled { cursor: default; }
  .chip:focus-visible { outline: 2px solid #3876b7; outline-offset: 2px; }
  @media (prefers-reduced-motion: reduce) {
    .chip { transition: none; }
    .chips { transition: none; }
  }
</style>
