<script lang="ts">
  // The election at the top of the page: the two candidates with their
  // portraits and electoral votes, the year and the map between them, the
  // year's note and anyone else who won votes. With a rerun it shows the
  // rerun's numbers, with history's beside them.
  import { alsoRanOf, mapLabelOf, type Paints } from './header';
  import type { Election } from './history';
  import MiniMap from './MiniMap.svelte';
  import Places from './Places.svelte';
  import Portrait from './Portrait.svelte';
  import type { ShownRun } from './state';
  import type { Names } from './types';

  interface Props {
    election: Election;
    year: number;
    rerun: ShownRun | null;
    paints: Paints;
    names: Names;
    light: boolean;
    /** State codes to light on the map (places named in the text being read). */
    highlight: readonly string[];
    /** A height to hold, px (0: none): the page's scrub hold. */
    hold?: number;
    /** The block's rendered height, px. */
    height?: number;
  }

  let { election: e, year, rerun, paints, names, light, highlight, hold = 0, height = $bindable(0) }: Props = $props();

  const A = $derived(e.candidates[0]);
  const B = $derived(e.candidates[1] ?? null);
  const colors = $derived(paints.colors);
  const evNow = $derived<Record<'A' | 'B', number>>(rerun ? rerun.ev : { A: A.ev, B: B?.ev ?? 0 });
  const winner = $derived(rerun ? rerun.winner : 'A');
  const evByState = $derived(new Map(e.states.map((s) => [s.code, s.ev])));
  const mapStates = $derived(rerun ? rerun.states.map((s) => ({ ...s, ev: evByState.get(s.code) })) : e.states);
  const flips = $derived(rerun ? rerun.states.filter((s) => s.flipped).length : 0);
  const mapLabel = $derived(mapLabelOf(year, !!rerun, e, mapStates, flips));
  const alsoRan = $derived(alsoRanOf(e.candidates.slice(2)));
  const matchup = $derived([{ c: A, k: 'A' as const }, ...(B ? [{ c: B, k: 'B' as const }] : [])]);
  // In the Rerun view the note names what the last rerun ran: its chips'
  // text, as the chips show it. History's note before any rerun, and for a
  // rerun that applied no what-ifs (groups dragged by hand).
  const ranText = $derived(rerun ? rerun.applied.map((a) => a.label).join(' · ') : '');
  const note = $derived(ranText || e.note);
</script>

<section class="election" aria-labelledby="sa-year" bind:offsetHeight={height} style:min-height={hold ? `${hold}px` : null}>
  <div class="matchup" class:solo={!B}>
    {#each matchup as { c, k } (k)}
      <div class="cand" class:b={k === 'B'}>
        <Portrait candidate={c} color={colors[k]} ink={paints.inks[k]} won={winner === k} {light} size={96} />
        <div class="facts">
          <p class="name">{c.name}{#if winner === k}<span class="sr">{' (won)'}</span>{/if}</p>
          <p class="party">{c.partyLabel}</p>
          <p class="num">{evNow[k]}</p>
          <p class="ev">electoral vote{evNow[k] === 1 ? '' : 's'}</p>
          {#if rerun}
            <p class="sub">{c.ev} in history</p>
          {:else if c.popular != null}
            <p class="sub">{c.popular.toFixed(1)}% of the vote</p>
          {:else}
            <p class="sub sub-room" aria-hidden="true">&nbsp;</p>
          {/if}
        </div>
      </div>
      {#if k === 'A'}
        <div class="center">
          <h1 id="sa-year" class="year">{year}</h1>
          <MiniMap {year} states={mapStates} {colors} {names} label={mapLabel} tile={12} {highlight} />
          <p class="needed">{e.majority} to win{#if flips}<span class="flips">{` · `}<span class="dot" aria-hidden="true"></span>{`${flips} flipped`}</span>{/if}</p>
        </div>
      {/if}
    {/each}
  </div>
  <!-- Always both, empty or not. On a narrow window .foot holds the room of
       the longest pair (below); on a wide one it isn't a box at all. -->
  <div class="foot">
    <p class="note">{#if note}<Places text={note} />{/if}</p>
    <p class="also">{#if alsoRan}Also ran: {alsoRan}{/if}</p>
  </div>
</section>

<style>
  /* Zero jitter while scrubbing: the block reserves its tallest year (a
     two-line note plus an also-ran line), so the page's height never changes
     with the year. Measured across all 60 years at 1440px (189–246px);
     narrower windows are covered by the page's scrub hold. */
  .election { display: flex; flex-direction: column; align-items: center; text-align: center; min-height: 246px; }
  .matchup {
    margin-top: 6px;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    align-items: center;
    gap: 28px;
    width: 100%;
  }
  .matchup.solo { grid-template-columns: auto auto; justify-content: center; gap: 56px; }
  .cand { display: flex; align-items: center; gap: 18px; min-width: 0; }
  .cand.b { flex-direction: row-reverse; }
  .facts { display: flex; flex-direction: column; align-items: flex-start; min-width: 0; text-align: left; }
  .b .facts { align-items: flex-end; text-align: right; }
  .facts p { margin: 0; }
  .name { font-size: 17px; font-weight: 600; line-height: 1.2; }
  .party { margin-top: 2px !important; font-size: 13px; color: rgba(0, 0, 0, 0.55); }
  .num { margin-top: 10px !important; font-size: 32px; line-height: 1; font-weight: 700; letter-spacing: -0.01em; font-variant-numeric: tabular-nums; }
  .ev { margin-top: 3px !important; font-size: 12px; color: rgba(0, 0, 0, 0.6); }
  .sub { margin-top: 1px !important; font-size: 12px; color: rgba(0, 0, 0, 0.5); font-variant-numeric: tabular-nums; }
  .center { display: flex; flex-direction: column; align-items: center; gap: 8px; }
  .year {
    margin: 0;
    font-size: 44px;
    line-height: 1;
    font-weight: 700;
    letter-spacing: 0.018em;
    font-variant-numeric: tabular-nums;
  }
  .needed { margin: -2px 0 0; font-size: 12px; color: rgba(0, 0, 0, 0.5); font-variant-numeric: tabular-nums; }
  /* The key to the map's flip mark: the same dot (black at 50%). */
  .flips .dot { display: inline-block; width: 7px; height: 7px; margin: 0 4px 0 1px; border-radius: 999px; background: #00000080; vertical-align: 0.5px; }
  .note { margin: 12px 0 0; max-width: 60ch; font-size: 15px; line-height: 1.45; color: rgba(0, 0, 0, 0.72); }
  .also { margin: 6px 0 0; max-width: 70ch; font-size: 12px; line-height: 1.45; color: rgba(0, 0, 0, 0.5); }
  .sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

  @media (max-width: 760px) {
    .year { font-size: 40px; }
    .matchup { grid-template-columns: 1fr 1fr; gap: 22px 12px; }
    .matchup.solo { grid-template-columns: 1fr; gap: 22px 12px; } /* = .matchup: an unopposed year is as tall as any */
    .center { grid-column: 1 / -1; grid-row: 1; }
    /* The candidates sit 22px into the gap under the map. */
    .cand, .cand.b { flex-direction: column; gap: 12px; margin-top: -22px; }
    .facts, .b .facts { align-items: center; text-align: center; }
    .name { font-size: 15px; }
    /* Phones: the block is one height every year, so the what-if and the
       robot below it never move with the year. Each part that varies holds
       its most: two lines of name and party, three of note, two of also-ran
       (measured over all 60 years at 320-430px). */
    .name { min-height: calc(2 * 1.2em); }
    .party { line-height: 1.25; min-height: calc(2 * 1.25em); }
    /* The note sits 23px under the candidates at its own height, the
       also-ran under it; the pair's room is their most (three lines of note,
       two of also-ran), the spare at its foot, so the block stays one height. */
    .note { margin-top: 23px; }
    .foot {
      display: flex;
      flex-direction: column;
      align-items: center;
      width: 100%;
      min-height: calc(23px + 3 * 1.45 * 15px + 6px + 2 * 1.45 * 12px);
    }
  }
  /* The narrowest phones: a long name ("Charles Cotesworth Pinckney") takes three lines. */
  @media (max-width: 359px) {
    .name { min-height: calc(3 * 1.2em); }
  }
  /* Empty, they take no room on a wide window. */
  @media (min-width: 761px) {
    .foot { display: contents; }
    .note:empty, .also:empty, .sub-room { display: none; }
  }
</style>
