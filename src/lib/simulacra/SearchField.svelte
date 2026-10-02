<script lang="ts">
  // Find a state or an election: type a name, a postal code or a year; the
  // first match is picked on Enter. A year snaps to the nearest election.
  import { Search } from 'lucide-svelte';
  import { ELECTION_YEARS, nearestElection, STATES } from './geo';

  type Pick = { readonly kind: 'year'; readonly year: number } | { readonly kind: 'state'; readonly code: string };

  interface Props {
    /** The state codes matching what's typed, as it's typed (null: nothing typed). */
    onmatch?: (codes: ReadonlySet<string> | null) => void;
    onpick?: (pick: Pick) => void;
  }
  let { onmatch, onpick }: Props = $props();

  let value = $state('');
  function matches(q: string): Pick[] {
    const t = q.trim().toLowerCase();
    if (!t) return [];
    if (/^\d{4}$/.test(t)) return [{ kind: 'year', year: nearestElection(Number(t)) }];
    if (/^\d{1,3}$/.test(t)) return ELECTION_YEARS.filter((y) => String(y).startsWith(t)).map((year) => ({ kind: 'year', year }) as const);
    return STATES.filter((s) => s.name.toLowerCase().includes(t) || s.code.toLowerCase() === t).map((s) => ({ kind: 'state', code: s.code }) as const);
  }
  const found = $derived(matches(value));
  $effect(() => {
    onmatch?.(value.trim() ? new Set(found.flatMap((p) => (p.kind === 'state' ? [p.code] : []))) : null);
  });
  function submit(e: SubmitEvent) {
    e.preventDefault();
    const first = found[0];
    if (!first) return;
    onpick?.(first);
    value = '';
  }
</script>

<form class="search" role="search" onsubmit={submit}>
  <Search size={15} aria-hidden="true" />
  <input bind:value type="search" placeholder="State or year" aria-label="Find a state or year" autocomplete="off" />
</form>

<style>
  .search { display: inline-flex; align-items: center; gap: 6px; height: 30px; padding: 0 10px; border-radius: 999px; background: rgba(0, 0, 0, 0.06); color: rgba(0, 0, 0, 0.5); }
  input { width: 140px; border: none; background: transparent; font: inherit; font-size: 13px; color: #000; outline: none; }
</style>
