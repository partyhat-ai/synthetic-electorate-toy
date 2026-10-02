<script lang="ts">
  // How often the model called it right: three headline numbers (backtest
  // years only; nothing is held out yet), then every election as a row —
  // the actual winner, the model's call, the states it missed and the gap
  // in electoral votes. The story years are the famous calls.
  import { fmtPct } from './format';
  import { STORY_YEARS } from './geo';
  import InfoPopover from './InfoPopover.svelte';

  interface Row {
    readonly year: number;
    readonly actual: 'A' | 'B';
    readonly call: 'A' | 'B' | null;
    readonly statesMissed: number;
    readonly states: number;
    /** The model's electoral votes for the actual winner, less the actual count. */
    readonly evError: number;
  }

  interface Props {
    rows: readonly Row[];
    onpick?: (year: number) => void;
  }
  let { rows, onpick }: Props = $props();

  const called = $derived(rows.filter((r) => r.call === r.actual).length);
  const stateCalls = $derived(rows.reduce((a, r) => a + (r.states - r.statesMissed), 0) / Math.max(1, rows.reduce((a, r) => a + r.states, 0)));
  const evError = $derived(rows.reduce((a, r) => a + Math.abs(r.evError), 0) / Math.max(1, rows.length));
  const story = (y: number) => STORY_YEARS.find((s) => s.year === y)?.detail ?? null;
</script>

<section class="accuracy" aria-label="Accuracy">
  <div class="kpis">
    <div class="kpi">
      <span class="v">{called} of {rows.length}</span>
      <span class="k">Winners called
        <InfoPopover label="What a backtest is">
          <p><strong>Backtest:</strong> the model reruns an election whose result is already known. A <strong>held-out</strong> election is one it never saw while being built.</p>
          <p>Every year here is a backtest, so the score flatters it. <strong>Leakage</strong> checks would test whether the voters simply remember who won.</p>
        </InfoPopover>
      </span>
    </div>
    <div class="kpi"><span class="v">{fmtPct(stateCalls, 1)}</span><span class="k">States called right</span></div>
    <div class="kpi"><span class="v">{evError.toFixed(0)}</span><span class="k">Mean electoral-vote error</span></div>
  </div>

  <table>
    <thead>
      <tr><th scope="col">Year</th><th scope="col">Won</th><th scope="col">Called</th><th scope="col">States missed</th><th scope="col">EV error</th></tr>
    </thead>
    <tbody>
      {#each rows as r (r.year)}
        <tr class:miss={r.call !== r.actual}>
          <td><button type="button" class="year" onclick={() => onpick?.(r.year)}>{r.year}</button>{#if story(r.year)}<span class="story" title={story(r.year)}>★</span>{/if}</td>
          <td>{r.actual}</td>
          <td>{r.call ?? 'No majority'}</td>
          <td>{r.statesMissed} of {r.states}</td>
          <td>{r.evError > 0 ? '+' : ''}{r.evError}</td>
        </tr>
      {/each}
    </tbody>
  </table>
</section>

<style>
  .kpis { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
  .kpi { display: flex; flex-direction: column; gap: 4px; padding: 14px 16px; border-radius: 12px; background: #fff; box-shadow: 0 0 0 0.5px rgba(0, 0, 0, 0.12); }
  .v { font-size: 26px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .k { display: inline-flex; align-items: center; gap: 2px; font-size: 12px; color: rgba(0, 0, 0, 0.55); }
  table { width: 100%; margin-top: 16px; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }
  th { text-align: left; font-weight: 500; color: rgba(0, 0, 0, 0.55); padding: 6px 8px; border-bottom: 1px solid rgba(0, 0, 0, 0.12); }
  td { padding: 5px 8px; border-bottom: 0.5px solid rgba(0, 0, 0, 0.08); }
  tr.miss td { background: rgba(208, 59, 59, 0.08); }
  .year { padding: 0; border: none; background: none; font: inherit; color: #3876b7; cursor: pointer; }
  .year:hover { text-decoration: underline; }
  .story { margin-left: 4px; color: #b98a00; }
</style>
