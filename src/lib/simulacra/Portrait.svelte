<script lang="ts">
  // A candidate's portrait (the lead image of their Wikipedia article), or
  // their initials while it loads or if it can't. The winner's frame wears a
  // ring and a check in their party's colour. With a Wikipedia article, the
  // portrait links to it: a click opens it in a new window, a modified or
  // middle click in a tab.
  import { Check } from 'lucide-svelte';

  interface Props {
    candidate: { readonly name: string; readonly portrait: string | null; readonly wiki?: string | null } | null;
    /** The party colour, authored for the mode. */
    color?: string;
    /** The check's colour on it. */
    ink?: string;
    won?: boolean;
    light?: boolean;
    /** Frame width, px (4:5). */
    size?: number;
  }
  let { candidate, color = '#898781', ink = '#ffffff', won = false, light = false, size = 104 }: Props = $props();

  const src = $derived(candidate?.portrait ?? null);
  // Which source loaded or failed: a new source starts over.
  let loadedSrc = $state<string | null>(null);
  let failedSrc = $state<string | null>(null);
  const loaded = $derived(src !== null && loadedSrc === src);
  const failed = $derived(src !== null && failedSrc === src);

  function initialsOf(name: string): string {
    const words = name.split(/\s+/).filter((w) => /^[A-Z]/.test(w));
    const first = words[0] ?? '';
    const last = words[words.length - 1] ?? '';
    if (words.length > 1) return first.charAt(0) + last.charAt(0);
    return first.charAt(0);
  }
  const initials = $derived(initialsOf(candidate?.name ?? ''));
  const wiki = $derived(candidate?.wiki ?? null);

  // A plain click opens the article in a new window; the link itself still
  // works for a middle click, a new tab or a screen reader.
  function openWiki(e: MouseEvent) {
    if (!wiki || e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return;
    e.preventDefault();
    window.open(wiki, '_blank', 'noopener,noreferrer,width=1100,height=850');
  }
</script>

{#snippet face()}
<div class="frame" class:won style:width="{size}px" style:height="{Math.round(size * 1.25)}px">
  <span class="initials" aria-hidden="true">{initials}</span>
  {#if src && !failed}
    {#key src}
      <img {src} alt="" class:shown={loaded} class:dark={!light} draggable="false" decoding="async" referrerpolicy="no-referrer"
        onload={() => (loadedSrc = src)} onerror={() => (failedSrc = src)} />
    {/key}
  {/if}
</div>
{#if won}
  <span class="badge" style:--ink={ink} aria-hidden="true"><Check size={13} strokeWidth={3} /></span>
{/if}
{/snippet}

{#if wiki}
  <a class="portrait" style:--c={color} href={wiki} target="_blank" rel="noopener noreferrer"
    aria-label="{candidate?.name} on Wikipedia (opens in a new window)" title="{candidate?.name} on Wikipedia" onclick={openWiki}>{@render face()}</a>
{:else}
  <div class="portrait" style:--c={color}>{@render face()}</div>
{/if}

<style>
  .portrait { position: relative; display: inline-flex; color: inherit; text-decoration: none; border-radius: 14px; }
  a.portrait { cursor: pointer; }
  a.portrait .frame { transition: transform 0.15s ease, filter 0.15s ease; }
  a.portrait:hover .frame { transform: translateY(-1px); filter: brightness(1.04); }
  a.portrait:focus-visible { outline: 2px solid #3876b7; outline-offset: 4px; }
  .frame {
    position: relative;
    overflow: hidden;
    border-radius: 14px;
    background: rgba(0, 0, 0, 0.07);
    flex: none;
  }
  /* The winner: a 2px surface gap, then the party's ring. */
  .frame.won { box-shadow: 0 0 0 2px #e5e5e5, 0 0 0 4px var(--c); }
  .initials {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 30px;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: rgba(0, 0, 0, 0.4);
  }
  img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: 50% 20%;
    opacity: 0;
    transition: opacity 0.35s ease;
  }
  img.shown { opacity: 1; }
  /* Dark mode inverts the whole page; a photo is turned back. */
  img.dark { filter: invert(1) hue-rotate(180deg) saturate(66.7%); }
  .badge {
    position: absolute;
    right: -7px;
    bottom: -7px;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    background: var(--c);
    color: var(--ink);
    box-shadow: 0 0 0 2px #e5e5e5;
  }
  @media (prefers-reduced-motion: reduce) { img, a.portrait .frame { transition: none; } }
</style>
