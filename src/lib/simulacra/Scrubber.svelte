<script lang="ts">
  // The time map's timeline: every election from 1789 to 2024 on one
  // slider, with a tick per election (red where the model missed the
  // winner), the franchise's turning points under it, and a play button
  // that steps through them.
  import { Pause, Play } from 'lucide-svelte';
  import { onDestroy } from 'svelte';
  import { ELECTION_YEARS, FRANCHISE_EVENTS } from './geo';

  interface Props {
    year: number;
    /** Years the model called the wrong winner. */
    misses?: ReadonlySet<number>;
    onchange?: (year: number) => void;
  }
  let { year, misses = new Set(), onchange }: Props = $props();

  const first = ELECTION_YEARS[0] ?? 1789;
  const last = ELECTION_YEARS[ELECTION_YEARS.length - 1] ?? 2024;
  const pos = (y: number) => ((y - first) / (last - first)) * 100;
  const index = $derived(ELECTION_YEARS.indexOf(year));

  let playing = $state(false);
  let timer: ReturnType<typeof setInterval> | undefined;
  function stop() {
    playing = false;
    clearInterval(timer);
  }
  function play() {
    if (playing) {
      stop();
      return;
    }
    playing = true;
    if (year === last) onchange?.(first);
    timer = setInterval(() => {
      const next = ELECTION_YEARS[ELECTION_YEARS.indexOf(year) + 1];
      if (next === undefined) stop();
      else onchange?.(next);
    }, 900);
  }
  onDestroy(stop);
</script>

<div class="scrubber">
  <button type="button" class="play" aria-label={playing ? 'Pause' : 'Play'} onclick={play}>
    {#if playing}<Pause size={16} aria-hidden="true" />{:else}<Play size={16} aria-hidden="true" />{/if}
  </button>
  <div class="track">
    <input
      type="range"
      min="0"
      max={ELECTION_YEARS.length - 1}
      step="1"
      value={index}
      aria-label="Election"
      aria-valuetext={String(year)}
      oninput={(e) => {
        const y = ELECTION_YEARS[Number(e.currentTarget.value)];
        if (y !== undefined) onchange?.(y);
      }}
    />
    <div class="ticks" aria-hidden="true">
      {#each ELECTION_YEARS as y (y)}
        <span class="tick" class:miss={misses.has(y)} style:left="{pos(y)}%"></span>
      {/each}
    </div>
    <div class="events">
      {#each FRANCHISE_EVENTS as ev (ev.year)}
        <span class="event" style:left="{pos(ev.year)}%" title="{ev.year}: {ev.detail}">{ev.label}</span>
      {/each}
    </div>
  </div>
  <span class="year">{year}</span>
</div>

<style>
  .scrubber { display: flex; align-items: center; gap: 14px; }
  .play {
    width: 32px;
    height: 32px;
    flex: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: none;
    border-radius: 999px;
    background: #111;
    color: #fff;
    cursor: pointer;
  }
  .play:focus-visible { outline: 2px solid #3876b7; outline-offset: 2px; }
  .track { position: relative; flex: 1; padding-bottom: 26px; }
  input { width: 100%; margin: 0; accent-color: #111; }
  .ticks { position: relative; height: 8px; }
  .tick { position: absolute; top: 0; width: 1px; height: 5px; background: rgba(0, 0, 0, 0.25); }
  .tick.miss { width: 3px; height: 8px; margin-left: -1px; background: #d03b3b; }
  .events { position: absolute; left: 0; right: 0; bottom: 0; height: 16px; }
  .event { position: absolute; transform: translateX(-50%); font-size: 10px; white-space: nowrap; color: rgba(0, 0, 0, 0.5); }
  .year { width: 3.5em; font-size: 20px; font-weight: 700; font-variant-numeric: tabular-nums; }
</style>
