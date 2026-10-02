<script lang="ts">
  // Phone-width windows get a note instead of the page, which needs a wide
  // window. One quiet control copies the link (with its ?year=) to open later
  // on a computer; without a clipboard, the address is there to copy by hand.
  import { Check, Link } from 'lucide-svelte';
  import { onDestroy } from 'svelte';

  const COPIED_MS = 1600;
  const host = location.host;
  let copied = $state(false);
  let timer: ReturnType<typeof setTimeout> | undefined;

  async function copy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(location.href);
    } catch {
      return;
    }
    copied = true;
    clearTimeout(timer);
    timer = setTimeout(() => (copied = false), COPIED_MS);
  }

  onDestroy(() => clearTimeout(timer));
</script>

<main class="revisit">
  <span class="brand">Simulacra Americana</span>
  <h1>Revisit on desktop</h1>
  <button type="button" class="copy" onclick={copy} aria-label={copied ? 'Link copied' : 'Copy the link'}>
    {#if copied}
      <Check size={13} strokeWidth={2.2} aria-hidden="true" /><span>Copied</span>
    {:else}
      <Link size={13} strokeWidth={2.2} aria-hidden="true" /><span>{host}</span>
    {/if}
  </button>
</main>

<style>
  .revisit {
    position: fixed;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: env(safe-area-inset-top) 24px env(safe-area-inset-bottom);
    background: #e5e5e5;
    color: #000;
    text-align: center;
  }
  .brand { font-family: 'Geist Mono', ui-monospace, monospace; font-size: 11px; font-weight: 500; letter-spacing: 0.04em; text-transform: uppercase; color: rgba(0, 0, 0, 0.45); }
  h1 { margin: 0; font-size: 20px; font-weight: 600; letter-spacing: -0.01em; }
  .copy {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 2px;
    padding: 6px 10px;
    border: none;
    border-radius: 999px;
    background: transparent;
    color: rgba(0, 0, 0, 0.5);
    font-size: 13px;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    transition: background 0.15s ease, color 0.15s ease;
  }
  .copy:active, .copy:hover { background: rgba(0, 0, 0, 0.06); color: rgba(0, 0, 0, 0.75); }
  .copy:focus-visible { outline: 2px solid #3876b7; outline-offset: 1px; }
  @media (prefers-reduced-motion: reduce) { .copy { transition: none; } }
</style>
