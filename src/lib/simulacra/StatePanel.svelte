<script lang="ts">
  // The inspector for one state in one election: who won, what the model
  // called, by how much, and the state's record across the timeline.
  import { X } from 'lucide-svelte';
  import { fmtPoints } from './format';
  import { absentReason, STATE_BY_CODE } from './geo';

  interface Row {
    readonly year: number;
    readonly actual: 'A' | 'B' | 'O';
    readonly call: 'A' | 'B' | 'O';
    readonly margin: number;
  }

  interface Props {
    code: string;
    year: number;
    /** The state's result in every election it voted in, oldest first. */
    history: readonly Row[];
    onclose?: () => void;
  }
  let { code, year, history, onclose }: Props = $props();

  const state = $derived(STATE_BY_CODE.get(code) ?? null);
  const now = $derived(history.find((r) => r.year === year) ?? null);
  const missed = $derived(history.filter((r) => r.call !== r.actual));
</script>

<aside class="panel" aria-label="{state?.name ?? code} in {year}">
  <header>
    <h3>{state?.name ?? code}</h3>
    <button type="button" class="close" aria-label="Close" onclick={() => onclose?.()}><X size={16} aria-hidden="true" /></button>
  </header>
  {#if state && state.first > year}
    <p class="note">Not yet a state in {year}: it first voted in {state.first}.</p>
  {:else if absentReason(code, year)}
    <p class="note">{absentReason(code, year)}</p>
  {:else if now}
    <dl>
      <dt>Actual</dt><dd>Candidate {now.actual}</dd>
      <dt>Model</dt><dd>Candidate {now.call}{now.call === now.actual ? '' : ' (missed)'}</dd>
      <dt>Margin</dt><dd>{fmtPoints(now.margin)} points</dd>
    </dl>
  {/if}
  <p class="record">Missed {missed.length} of {history.length} elections{missed.length ? `: ${missed.map((r) => r.year).join(', ')}` : ''}.</p>
</aside>

<style>
  .panel { padding: 14px 16px; border-radius: 12px; background: #fff; box-shadow: 0 0 0 0.5px rgba(0, 0, 0, 0.12); }
  header { display: flex; align-items: center; justify-content: space-between; }
  h3 { margin: 0; font-size: 15px; }
  .close { display: inline-flex; padding: 4px; border: none; border-radius: 999px; background: transparent; cursor: pointer; }
  .close:hover { background: rgba(0, 0, 0, 0.06); }
  dl { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; margin: 12px 0 0; font-size: 13px; }
  dt { color: rgba(0, 0, 0, 0.55); }
  dd { margin: 0; font-variant-numeric: tabular-nums; }
  .note, .record { margin: 10px 0 0; font-size: 12px; color: rgba(0, 0, 0, 0.6); }
</style>
