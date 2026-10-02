<script lang="ts">
  // Simulacra Americana: rerun an American presidential election with one
  // fact changed. It opens on a real election (one of the ten with stories,
  // at random, or ?year=): the two candidates, who won, and the map as it
  // happened. Below are the groups of voters that decided it, including the
  // ones who couldn't vote, each a row of fifty people. The narrator robot
  // stands beside the what-if field: tap a suggestion or type your own, and
  // it reruns the election and says what changed; tapped, it fires its chest
  // reactor, and the tab icon takes the shot's colour. The timeline along the
  // bottom moves between elections.
  //
  // This file is composition and layout. State: $lib/simulacra/state(.svelte).ts;
  // reruns: runs.ts; what the robot says: Narrator; the robot: RobotStage.
  import { onDestroy, onMount, tick, untrack } from 'svelte';
  import { replaceState } from '$app/navigation';
  import AboutSources from '$lib/simulacra/AboutSources.svelte';
  import { toBody } from '$lib/simulacra/actions';
  import { createSimulacraApi } from '$lib/simulacra/api';
  import { ELECTION_YEARS } from '$lib/simulacra/geo';
  import ElectionHeader from '$lib/simulacra/ElectionHeader.svelte';
  import { namesOf, paintsOf } from '$lib/simulacra/header';
  import { electionOf, FEATURED } from '$lib/simulacra/history';
  import InfoPopover from '$lib/simulacra/InfoPopover.svelte';
  import Narrator from '$lib/simulacra/Narrator.svelte';
  import { hoverPlaces } from '$lib/simulacra/places';
  import RevisitOnDesktop from '$lib/simulacra/RevisitOnDesktop.svelte';
  import RobotStage, { STILLS } from '$lib/simulacra/RobotStage.svelte';
  import { createSampleApi } from '$lib/simulacra/sample';
  import type { WhatIf } from '$lib/simulacra/schemas';
  import SliceRow from '$lib/simulacra/SliceRow.svelte';
  import { apiOptionsFor, OPENING_YEAR, randomStory, readParams } from '$lib/simulacra/state';
  import { PageState } from '$lib/simulacra/state.svelte';
  import { TabIcon } from '$lib/simulacra/tabIcon';
  import TimeBar from '$lib/simulacra/TimeBar.svelte';
  import '$lib/simulacra/theme.css';

  const params = readParams(new URLSearchParams(location.search), import.meta.env.DEV);
  const page = new PageState({
    api: params.sample ? createSampleApi() : createSimulacraApi(apiOptionsFor(params.simapi)),
    year: params.year ?? OPENING_YEAR,
    replaceUrl: (url) => {
      try {
        replaceState(url, {});
      } catch {
        // router not ready
      }
    },
    onFresh: (n) => narrator?.startReveal(n),
  });

  let narrator = $state<ReturnType<typeof Narrator> | null>(null);
  let robot = $state<ReturnType<typeof RobotStage> | null>(null);
  let mainEl = $state<HTMLElement | null>(null);
  let slotEl = $state<HTMLElement | null>(null);
  let robotShown = $state(false);
  let tabIcon = $state<TabIcon | null>(null);
  let revealing = $state(false);
  // Phone-width windows got RevisitOnDesktop instead of the page. Stubbed
  // out: phones get the page (and the robot). Set true to bring it back.
  const REVISIT_ON_DESKTOP = false;
  const SMALL = '(max-width: 760px)';
  let narrow = $state(window.matchMedia(SMALL).matches);
  const revisit = $derived(REVISIT_ON_DESKTOP && narrow);
  // On a narrow window, where the what-if group and the robot sit, each
  // nudged up or down from its place (WhatIf.svelte), px. ?tune=1 shows a
  // slider for each, kept in this browser; Reset returns to the defaults.
  const UI_Y = 10;
  const BOT_Y = -168;
  const TUNE_MIN = -2000;
  const TUNE_MAX = 800;
  const tuning = new URLSearchParams(location.search).has('tune');
  function readTune(key: string, fallback: number): number {
    try {
      const raw = localStorage.getItem(`sa-tune-${key}`);
      const v = raw === null ? Number.NaN : Number(raw);
      return Number.isFinite(v) ? Math.min(TUNE_MAX, Math.max(TUNE_MIN, v)) : fallback;
    } catch {
      return fallback;
    }
  }
  let uiY = $state(tuning ? readTune('ui', UI_Y) : UI_Y);
  let botY = $state(tuning ? readTune('bot', BOT_Y) : BOT_Y);
  $effect(() => {
    const ui = uiY;
    const bot = botY;
    if (tuning) {
      try {
        localStorage.setItem('sa-tune-ui', String(ui));
        localStorage.setItem('sa-tune-bot', String(bot));
      } catch {
        // private window: the sliders still work for this visit
      }
    }
    // The robot stands on its slot: measure it where it moved to.
    untrack(() => robot?.measureSoon());
  });
  // Dragging the time bar: the robot holds still (no restaging) and the
  // election and the groups hold their height while each year loads, so
  // nothing jumps; the robot is placed once more on release.
  let scrubbing = $state(false);
  let electionH = $state(0);
  let groupsH = $state(0);
  let electionHold = $state(0);
  let groupsHold = $state(0);

  const e = $derived(page.election);
  const B = $derived(e.candidates[1] ?? null);
  const paints = $derived(paintsOf(e, page.light));
  const colors = $derived(paints.colors);
  const names = $derived(namesOf(e));
  const rerun = $derived(page.rerun);
  const slices = $derived(rerun ? rerun.slices : (page.sim?.slices ?? []));
  const baseSlices = $derived(new Map((page.sim?.slices ?? []).map((s) => [s.key, s])));
  const reached = $derived(new Set(page.selected.flatMap((k) => page.whatIfs.find((w) => w.key === k)?.slices ?? [])));
  const hasOthers = $derived(slices.some((s) => s.O > 0.005));
  // The 3D robot is drawn at every width, in the slot below the what-if.
  const stageMode = $derived(!revisit);

  // The composer's chips and field, held from the last loaded year while a
  // scrubbed-to year is still loading.
  const held: { chips: readonly WhatIf[]; closed: boolean } = { chips: [], closed: true };
  const composer = $derived.by(() => {
    if (!(scrubbing && !page.sim)) {
      held.chips = page.whatIfs;
      held.closed = page.server !== 'online' || !page.sim || e.unopposed;
    }
    return { chips: held.chips, closed: held.closed };
  });

  $effect(() => {
    const y = page.year;
    if (revisit) return;
    untrack(() => void page.loadSim(y));
  });
  $effect(() => {
    if (page.voterKey) page.fetchVoter();
  });

  function scrub(on: boolean) {
    scrubbing = on;
    electionHold = on ? electionH : 0;
    groupsHold = on ? groupsH : 0;
    if (!on) robot?.measureSoon();
  }
  // While scrubbing, each block only ever grows to the tallest year passed so
  // far (a narrow window wraps notes past the CSS reservation), never shrinks.
  $effect(() => {
    if (!scrubbing) return;
    const measured = { election: electionH, groups: groupsH };
    untrack(() => {
      electionHold = Math.max(electionHold, measured.election);
      groupsHold = Math.max(groupsHold, measured.groups);
    });
  });
  // The tab icon cycles while a rerun works.
  $effect(() => {
    tabIcon?.setWorking(!!page.run);
  });

  /** A tap on the robot: a shot from its chest in the next colour, which the tab icon takes. */
  function blast() {
    if (tabIcon) robot?.blast(tabIcon.fire().hex);
  }

  function act(key: string) {
    if (key === 'sample') {
      const url = new URL(location.href);
      url.searchParams.set('sample', '1');
      url.searchParams.set('year', String(page.year));
      location.assign(url.href);
    } else if (key === 'retry') page.retry();
    else if (key === 'rerun') page.rerunNow();
    else if (key === 'shuffle') page.setYear(randomStory(page.year));
  }

  // ── Keys ──
  function onKey(ev: KeyboardEvent) {
    const t = ev.target instanceof Element ? ev.target : null;
    if ((ev.metaKey || ev.ctrlKey) && ev.key === 'Enter') {
      ev.preventDefault();
      page.rerunNow();
      return;
    }
    if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
    if (t?.closest('input, textarea, select, [contenteditable="true"], [role="slider"]')) return;
    if (ev.key === 'ArrowLeft') {
      ev.preventDefault();
      page.step(-1);
    } else if (ev.key === 'ArrowRight') {
      ev.preventDefault();
      page.step(1);
    } else if (ev.key === 'Escape' && page.openSlice && !document.querySelector('[role="dialog"]')) page.openSlice = null;
  }

  function describe(y: number): string {
    const [a, b] = electionOf(y)?.candidates ?? [];
    if (!a) return String(y);
    return b ? `${y} · ${a.short} over ${b.short}` : `${y} · ${a.short}, unopposed`;
  }

  onMount(() => {
    const small = window.matchMedia(SMALL);
    const readSmall = () => (narrow = small.matches);
    readSmall();
    small.addEventListener('change', readSmall);
    void tick().then(() => {
      page.urlReady = true;
      page.syncUrl();
      robot?.measureSoon();
    });
    // Without an icon link the blasts still take their turns.
    const icon = new TabIcon(document.querySelector<HTMLLinkElement>('link[rel="icon"]') ?? { href: '' });
    tabIcon = icon;
    return () => {
      small.removeEventListener('change', readSmall);
      icon.dispose();
      tabIcon = null;
    };
  });
  onDestroy(() => page.dispose());
</script>

<svelte:head>
  <title>Simulacra Americana</title>
</svelte:head>
<svelte:window onkeydown={onKey} />

{#if revisit}
  <RevisitOnDesktop />
{:else}
<div class="sa" class:scrubbing class:dark={!page.light} onscroll={() => robot?.measureSoon()}
  style:--ui-y="{uiY}px" style:--bot-y="{botY}px">
  <div class="page">
    <RobotStage bind:this={robot} bind:shown={robotShown} spot={slotEl} {stageMode} {scrubbing} year={page.year}
      paint={page.view === 'whatif' ? 'rerun' : 'history'} walking={page.running || revealing} observe={mainEl}
      ontap={blast} />
    <header class="top">
      <span class="brand">Simulacra Americana</span>
      <!-- Always there, always both: the switch sets the look and the robot's
           paint; the numbers are the rerun's once there is one, else history's. -->
      <div class="seg" role="radiogroup" aria-label="Show">
        <button type="button" role="radio" aria-checked={page.view !== 'whatif'} class:on={page.view !== 'whatif'} onclick={() => (page.view = 'history')}>History</button>
        <button type="button" role="radio" aria-checked={page.view === 'whatif'} class:on={page.view === 'whatif'} onclick={() => (page.view = 'whatif')}>Rerun</button>
        <div class="seg-thumb" class:second={page.view === 'whatif'} aria-hidden="true"></div>
      </div>
      <span class="trail">
        {#if page.api.sample}
          <span class="pill" title="The voter groups, what-ifs and reruns are invented to show how this works. The elections are real.">Sample Data</span>
        {/if}
        <InfoPopover label="About Simulacra Americana" align="end">
          <p><strong>Simulacra Americana</strong> reruns American presidential elections with one fact changed.</p>
          <p>Every election opens as it happened. The simulation server rebuilds who could vote from census records and lets synthetic voters decide, so a rerun can change who votes, where they live or what they care about.</p>
          {#if page.api.sample}<p>Sample data: the voter groups, what-ifs and reruns here are invented to show how it works. The elections are real.</p>{/if}
          <AboutSources />
        </InfoPopover>
      </span>
    </header>

    <main class="main" bind:this={mainEl}>
      <ElectionHeader election={e} year={page.year} {rerun} {paints} {names} light={page.light} highlight={$hoverPlaces}
        hold={electionHold} bind:height={electionH} />

      <section class="groups" aria-labelledby="sa-groups" bind:offsetHeight={groupsH} style:min-height={groupsHold ? `${groupsHold}px` : null}>
        <div class="groups-head">
          <h2 id="sa-groups">Who voted</h2>
          {#if page.sim?.slices.length}<ul class="legend" aria-label="Key">
            <li><span class="key fill" style:background={colors.A}></span>{names.A}</li>
            {#if B}<li><span class="key fill" style:background={colors.B}></span>{names.B}</li>{/if}
            {#if hasOthers}<li><span class="key fill" style:background={colors.O}></span>{names.O}</li>{/if}
            <li><span class="key ring"></span>Stayed home</li>
            <li><span class="key dot"></span>Couldn’t vote</li>
          </ul>{/if}
        </div>
        {#if page.sim?.slices.length}
          <div class="rows">
            {#key page.editEpoch}
            {#each slices as s (s.key)}
              <SliceRow slice={s} base={baseSlices.get(s.key)} {colors} {names} rerun={!!rerun} lit={reached.has(s.key)}
                open={page.openSlice === s.key} editable={page.canEdit}
                ontoggle={() => page.toggleSlice(s.key)} onedit={(d) => page.editSlice(s.key, d)} />
            {/each}
            {/key}
          </div>
        {:else}
          <div class="rows ghost" aria-hidden="true">
            {#each [0, 1, 2] as i (i)}
              <div class="ghost-row">
                <span class="ghost-label"></span>
                <svg viewBox="0 0 500 10" preserveAspectRatio="xMinYMid meet">
                  {#each Array(50) as _, j (j)}<circle cx={j * 10 + 5} cy="5" r="3.9" />{/each}
                </svg>
                <span class="ghost-val"></span>
              </div>
            {/each}
          </div>
          {#if page.server !== 'online' && page.server !== 'connecting'}
            <p class="groups-note">The voter groups come from the simulation server.</p>
          {/if}
        {/if}
      </section>

      <Narrator bind:this={narrator} bind:slot={slotEl} bind:revealing {page} {names} stage={stageMode} {robotShown}
        still={STILLS[page.view === 'whatif' ? 'rerun' : 'history']} chips={composer.chips} closed={composer.closed} onaction={act} />
    </main>
  </div>
</div>

{/if}

{#if tuning && narrow}
  <div class="tune" role="group" aria-label="Positions">
    <label>What-if <span>{uiY}</span>
      <input type="range" min={TUNE_MIN} max={TUNE_MAX} step="2" bind:value={uiY} /></label>
    <label>Robot <span>{botY}</span>
      <input type="range" min={TUNE_MIN} max={TUNE_MAX} step="2" bind:value={botY} /></label>
    <button type="button" onclick={() => { uiY = UI_Y; botY = BOT_Y; }}>Reset</button>
  </div>
{/if}

<!-- Its own block: toBody moves it, so it must not be the edge of the one above. -->
{#if !revisit}
<div class="timebar" class:dark={!page.light} use:toBody>
  <TimeBar dark={!page.light} years={ELECTION_YEARS} value={page.year} featured={FEATURED} {describe}
    onchange={(y) => page.setYear(y)} onscrub={scrub} />
</div>
{/if}

<style>
  /* The page's own layout. The scrolling layer, the Rerun view's invert and
     the time bar's glass are $lib/simulacra/theme.css. */
  .page { position: relative; min-height: 100%; padding-bottom: 84px; }
  /* The brand, the History / Your year switch (once there's a rerun) and
     the sample label and About, on one toolbar row. */
  .top {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    height: 48px;
    padding: 0 20px;
    margin-bottom: 18px;              /* = the gap under Who voted (.main) */
  }
  .top .seg { grid-column: 2; position: relative; top: 5px; }
  .trail { grid-column: 3; justify-self: end; }
  .brand { font-family: 'Geist Mono', ui-monospace, monospace; font-size: 12px; font-weight: 500; letter-spacing: 0.04em; text-transform: uppercase; color: rgba(0, 0, 0, 0.55); }
  .trail { display: flex; align-items: center; gap: 8px; }
  .pill {
    height: 22px;
    display: inline-flex;
    align-items: center;
    font-size: 11px;
    font-weight: 500;
    color: rgba(0, 0, 0, 0.6);
  }
  .main {
    max-width: 800px;
    margin: 0 auto;
    padding: 0 24px;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  /* ── Who voted ── */
  /* Zero jitter while scrubbing: the chart reserves its tallest year (five
     rows; 293px across all 60 years at 1440px). */
  .groups { min-height: 293px; }
  /* History / Your year: the hub's Content / Chat control
     (MainView .hub-segmented-control), metrics and all. */
  .seg {
    position: relative;
    display: flex;
    box-sizing: content-box;
    height: 29px;
    width: 154px;
    padding: 3px;
    border-radius: 20px;
    background: rgba(108, 108, 108, 0.15);
    -webkit-backdrop-filter: blur(12px) saturate(150%);
    backdrop-filter: blur(12px) saturate(150%);
    box-shadow: inset 0 -1px 3px rgba(0, 0, 0, 0.08), inset 0 0 0 0.5px rgba(0, 0, 0, 0.04);
    user-select: none;
  }
  .seg button {
    position: relative;
    z-index: 1;
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    border: none;
    border-radius: 7px;
    background: transparent;
    color: #00000096;
    font-family: 'Geist', -apple-system, sans-serif;
    font-size: 14px;
    white-space: nowrap;
    cursor: pointer;
    transition: color 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  }
  .seg button:hover:not(:disabled) { color: #000; }
  /* The selected label sits on the blue indicator. */
  .seg button.on, .seg button.on:hover { color: #fff; }
  .seg button:disabled { opacity: 0.45; cursor: default; }
  .seg button:focus-visible { outline: 2px solid #3876b7; outline-offset: 1px; }
  .seg-thumb {
    position: absolute;
    top: 3px;
    left: 3px;
    width: calc(50% - 3px);
    height: calc(100% - 6px);
    border-radius: 20px;
    background: #007aff;                              /* = Rerun (WhatIf .run) */
    box-shadow: inset 0 -0.5px 0 rgb(0 0 0 / 20%);   /* lit edge along the bottom */
    transition: transform 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    pointer-events: none;
  }
  .seg-thumb.second { transform: translateX(100%); }
  @media (prefers-reduced-motion: reduce) { .seg-thumb, .seg button { transition: none; } }
  /* Scrubbing: years change faster than the fades, so they're skipped. */
  .scrubbing :global(*) { transition: none !important; animation: none !important; }
  .groups-head { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; padding: 0 10px 8px; }
  h2 { margin: 0; font-size: 17px; font-weight: 600; }
  .legend { display: flex; flex-wrap: wrap; gap: 4px 14px; margin: 0; padding: 0; list-style: none; font-size: 12px; color: rgba(0, 0, 0, 0.6); }
  .legend li { display: inline-flex; align-items: center; gap: 6px; }
  .key { width: 9px; height: 9px; border-radius: 999px; flex: none; }
  .key.ring { box-sizing: border-box; border: 1.3px solid rgba(0, 0, 0, 0.45); }
  .key.dot { width: 4px; height: 4px; margin: 0 2.5px; background: rgba(0, 0, 0, 0.25); }
  .rows { display: flex; flex-direction: column; gap: 2px; }
  .ghost-row {
    display: grid;
    grid-template-columns: minmax(160px, 212px) minmax(0, 1fr) 124px;
    align-items: center;
    gap: 16px;
    min-height: 42px;
    padding: 4px 10px;
  }
  .ghost-label { height: 12px; width: 70%; border-radius: 6px; background: rgba(0, 0, 0, 0.08); }
  .ghost-val { height: 10px; width: 60%; justify-self: end; border-radius: 5px; background: rgba(0, 0, 0, 0.06); }
  .ghost svg { width: 100%; height: auto; display: block; }
  .ghost circle { fill: rgba(0, 0, 0, 0.08); }
  .groups-note { margin: 6px 10px 0; font-size: 13px; color: rgba(0, 0, 0, 0.5); }

  /* ?tune=1 on a phone: the two position sliders, pinned under the toolbar. */
  .tune {
    position: fixed;
    top: 56px;
    left: 12px;
    right: 12px;
    z-index: 30;
    display: grid;
    grid-template-columns: 1fr 1fr auto;
    align-items: end;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.92);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
    font-size: 12px;
    color: #000;
  }
  .tune label { display: flex; flex-direction: column; gap: 4px; font-weight: 600; }
  .tune span { font-weight: 400; font-variant-numeric: tabular-nums; color: rgba(0, 0, 0, 0.6); }
  .tune input { width: 100%; }
  .tune button { height: 30px; padding: 0 10px; border: none; border-radius: 999px; background: #f2f2f7; font: inherit; }

  @media (max-width: 760px) {
    /* Phones: no wordmark; its cell stays, so the switch stays centred. */
    .brand { visibility: hidden; }
    /* Narrow: above the robot's layer (RobotStage .robot-host, z 3), so the
       what-if is drawn over the robot standing behind it; the content is
       transparent elsewhere, so the robot shows through. A sideways drag
       over it turns the robot; vertical scrolling and pinch-zoom stay. */
    .main { padding: 0 16px; gap: 28px; position: relative; z-index: 4; touch-action: pan-y pinch-zoom; }
    /* Phones: Who voted is one height every year (up to five groups, each
       label up to two lines; the key up to two lines), so nothing below it
       moves with the year. */
    .legend { min-height: 33px; align-content: flex-start; }
    .rows { min-height: calc(5 * 72px + 4 * 2px); }
    .ghost-row { grid-template-columns: minmax(0, 1fr) auto; }
    .ghost-row svg { grid-column: 1 / -1; }
  }
  /* The narrowest phones wrap labels and counts further (1856 at 320px: 371px). */
  @media (max-width: 359px) {
    .rows { min-height: 384px; }
  }
</style>
