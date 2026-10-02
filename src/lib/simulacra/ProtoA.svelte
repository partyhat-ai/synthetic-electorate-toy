<script lang="ts">
  // Prototype A, the time map: every election as a map of the model's calls
  // against what happened, scrubbed from 1789 to 2024, with an Accuracy tab,
  // an inspector for the picked state, search, and what-if scenarios. All of
  // it runs on the sample model (sample.ts), so every number is invented.
  import AccuracyView from './AccuracyView.svelte';
  import { BUILTIN_SCENARIOS, ELECTION_YEARS } from './geo';
  import { sample } from './sample';
  import ScenarioPopover from './ScenarioPopover.svelte';
  import Scrubber from './Scrubber.svelte';
  import SearchField from './SearchField.svelte';
  import StatePanel from './StatePanel.svelte';
  import TileMap from './TileMap.svelte';

  // Each era's parties, coloured by hand for now.
  const PARTY_COLORS: Readonly<Record<string, string>> = {
    R: '#d03b3b',
    D: '#2a78d6',
    W: '#eb6834',
    NR: '#eb6834',
    DR: '#1baf7a',
    F: '#4a3aa7',
  };
  const VIEWS = [
    { key: 'map', label: 'Map' },
    { key: 'accuracy', label: 'Accuracy' },
  ] as const;
  type View = (typeof VIEWS)[number]['key'];
  type Key = 'A' | 'B' | 'O';

  let view = $state<View>('map');
  let year = $state(2024);
  let selected = $state<string | null>(null);
  let matches = $state<ReadonlySet<string> | null>(null);
  let scenarios = $state<string[]>([]);

  const toKey = (k: string): Key => (k === 'A' || k === 'B' ? k : 'O');
  const election = $derived(sample.election(year));
  const call = $derived(sample.call(year));
  const colors = $derived({
    A: PARTY_COLORS[election?.candidates[0].party ?? ''] ?? '#666',
    B: PARTY_COLORS[election?.candidates[1]?.party ?? ''] ?? '#999',
    O: '#4d4c48',
  });
  const results = $derived(
    (call?.states ?? []).flatMap((s) => {
      const actual = election?.states.find((x) => x.code === s.code);
      return actual ? [{ code: s.code, actual: toKey(actual.won), call: toKey(s.won), margin: s.margin }] : [];
    }),
  );

  // Every election as an accuracy row.
  const rows = ELECTION_YEARS.flatMap((y) => {
    const e = sample.election(y);
    const c = sample.call(y);
    if (!e || !c) return [];
    const actual = e.candidates[0];
    const winner: 'A' | 'B' | null = c.winner === 'A' || c.winner === 'B' ? c.winner : null;
    return [
      {
        year: y,
        actual: actual.key,
        call: winner,
        statesMissed: c.states.filter((s) => s.flipped).length,
        states: c.states.length,
        evError: c.ev.A - actual.ev,
      },
    ];
  });
  const misses = new Set(rows.filter((r) => r.call !== r.actual).map((r) => r.year));
  const inEffect = $derived(BUILTIN_SCENARIOS.filter((s) => scenarios.includes(s.key) && year >= s.from && year <= s.to));

  // The picked state across the timeline.
  const history = $derived(
    selected
      ? ELECTION_YEARS.flatMap((y) => {
          const code = selected;
          const actual = sample.election(y)?.states.find((s) => s.code === code);
          const c = sample.call(y)?.states.find((s) => s.code === code);
          return actual && c ? [{ year: y, actual: toKey(actual.won), call: toKey(c.won), margin: c.margin }] : [];
        })
      : [],
  );
</script>

<div class="proto-a">
  <div class="bar">
    <div class="tabs" role="tablist" aria-label="View">
      {#each VIEWS as v (v.key)}
        <button type="button" role="tab" aria-selected={view === v.key} class:on={view === v.key} onclick={() => (view = v.key)}>{v.label}</button>
      {/each}
    </div>
    <SearchField
      onmatch={(m) => (matches = m)}
      onpick={(p) => {
        if (p.kind === 'year') year = p.year;
        else selected = p.code;
        view = 'map';
      }}
    />
    <ScenarioPopover chosen={scenarios} onchange={(k) => (scenarios = k)} />
  </div>

  {#if view === 'map'}
    <div class="body" class:inspecting={!!selected}>
      <div>
        <TileMap {year} {results} {colors} {selected} {matches} onselect={(code) => (selected = selected === code ? null : code)} />
        {#if inEffect.length}
          <p class="scenario-note">{inEffect.map((s) => s.label).join(', ')}: scenarios run on the simulation server; the sample shows the baseline.</p>
        {/if}
      </div>
      {#if selected}
        <StatePanel code={selected} {year} {history} onclose={() => (selected = null)} />
      {/if}
    </div>
    <Scrubber {year} {misses} onchange={(y) => (year = y)} />
  {:else}
    <AccuracyView
      {rows}
      onpick={(y) => {
        year = y;
        view = 'map';
      }}
    />
  {/if}
</div>

<style>
  .proto-a { display: flex; flex-direction: column; gap: 16px; }
  .bar { display: flex; align-items: center; gap: 10px; }
  .tabs { display: flex; gap: 2px; margin-right: auto; padding: 2px; border-radius: 999px; background: rgba(0, 0, 0, 0.06); }
  .tabs button { height: 28px; padding: 0 14px; border: none; border-radius: 999px; background: transparent; font: inherit; font-size: 13px; cursor: pointer; }
  .tabs button.on { background: #fff; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12); }
  .body { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; }
  .body.inspecting { grid-template-columns: minmax(0, 1fr) 260px; align-items: start; }
  .scenario-note { margin: 8px 0 0; font-size: 12px; color: rgba(0, 0, 0, 0.6); }
</style>
