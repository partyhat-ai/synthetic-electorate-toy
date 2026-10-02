<script lang="ts">
  // The robot's working, inside its bubble (WhatIf.svelte): the steps (live,
  // a mark per step; finished and opened, label / text rows), and, opened,
  // the interviews behind the rerun and what it drew on.
  import { Check, ChevronDown } from 'lucide-svelte';
  import Places from './Places.svelte';
  import type { InterviewAnswer, WhatIf } from './schemas';
  import { day, type Message, peopleIn, splitStep } from './whatif';

  interface Props {
    message: Message;
    whatIfs?: readonly WhatIf[];
    /** The robot is working: the steps show live. */
    working?: boolean;
    /** The bubble is opened (More). */
    opened?: boolean;
    /** The Sources fold opened or closed: the bubble's height changed. */
    onfold?: () => void;
  }
  let { message, whatIfs = [], working = false, opened = false, onfold }: Props = $props();

  // The Sources fold: closed until asked for, and kept as left across messages.
  let sourcesOpen = $state(false);

  const labelOf = (key: string) => whatIfs.find((x) => x.key === key)?.label || key;
  /** A person's two rows: as it was, and in the rerun. */
  const sides = (a: InterviewAnswer) =>
    [
      { tag: 'Historic', x: a.before },
      { tag: 'Rerun', x: a.after },
    ] as const;
</script>

{#if message.steps?.length && (working || opened)}
  <!-- The working: while live, a mark per step; opened and finished, a
       section of label / text rows (a step's "Label: text" split). -->
  <section class="sec" class:live={working} aria-label="How I got this">
    {#if !working}<h3 class="sec-h">How I got this</h3>{/if}
    <ol class="steps">
      {#each message.steps as st, i (i + st.text)}
        {@const s = splitStep(st.text)}
        <li class={st.state} class:bare={!s.label}>
          {#if working}<span class="mark" aria-hidden="true">{#if st.state === 'done'}<Check size={11} strokeWidth={2.6} />{:else}<i></i>{/if}</span>{/if}
          {#if s.label}<span class="k">{s.label}</span>{/if}
          <span class="v"><Places text={s.body} /></span>
        </li>
      {/each}
    </ol>
  </section>
{/if}
{#if opened && message.interview?.byWhatIf.length}
  <!-- The interviews behind the rerun: grouped by what-if (when there's
       more than one), then by the wording of the question; each person a
       header line and two rows, Historic and Rerun. -->
  {@const iv = message.interview}
  {@const many = iv.byWhatIf.length > 1}
  <section class="sec iv" aria-label="Interviews">
    <h3 class="sec-h">Interviews<span class="sec-n">{peopleIn(iv)} people</span></h3>
    {#each iv.byWhatIf as w (w.whatIf)}
      <div class="iv-w">
      {#if many}<h4 class="iv-wh">{labelOf(w.whatIf)}</h4>{/if}
      {#each iv.questions as q, qi (qi)}
        {@const asked = w.answers.filter((a) => a.question === qi)}
        {#if asked.length}
          <div class="iv-g">
            <p class="iv-q">“{q}”</p>
            <ul class="iv-a">
              {#each asked as a (a.name + a.line)}
                {@const moved = a.after.choice !== a.before.choice}
                <li class:misread={a.misread}>
                  <p class="iv-who">
                    <span><b>{a.name}</b> <Places text={a.line} /> · <Places text={a.cohort} /></span>
                    {#if a.misread}<em class="iv-flag">Misread the news</em>{:else if moved}<em class="iv-flag moved">Changed</em>{/if}
                  </p>
                  <dl class="iv-rows">
                    {#each sides(a) as { tag, x } (tag)}
                      <dt>{tag}</dt>
                      <dd class="iv-c">{x.choice}{#if x.pVote != null}<small>{x.pVote}% likely</small>{/if}</dd>
                      <dd class="iv-say">“<Places text={x.quote} />”</dd>
                    {/each}
                  </dl>
                </li>
              {/each}
            </ul>
          </div>
        {/if}
      {/each}
      </div>
    {/each}
  </section>
{/if}
{#if opened && message.sources}
  <!-- What the rerun drew on: the dated newspapers in the voters' briefs
       (each summarized in a line), the research behind the change, and
       the data. A short key column (date, year) and the line beside it. -->
  {@const src = message.sources}
  <details class="sec src" aria-label="Sources" bind:open={sourcesOpen} ontoggle={() => onfold?.()}>
    <!-- A click here folds the list, not the whole bubble. -->
    <summary class="sec-h src-sum" onclick={(e) => e.stopPropagation()}>
      <span>Sources</span><span class="src-chev" aria-hidden="true"><ChevronDown size={12} strokeWidth={2.25} /></span>
    </summary>
    {#if src.reading.length}
      <div class="src-g">
        <h4 class="src-h">Newspapers the voters read<span class="sec-n">{src.reading.length}</span></h4>
        <ul class="src-l">
          {#each src.reading as r, i (i)}
            <li><span class="src-k">{day(r.date)}</span><span class="src-v"><Places text={r.summary || r.newspaper} /><small>{r.newspaper}, {r.place}</small></span></li>
          {/each}
        </ul>
      </div>
    {/if}
    {#if src.research.length}
      <div class="src-g">
        <h4 class="src-h">Research<span class="sec-n">{src.research.length} findings</span></h4>
        <ul class="src-l">
          {#each src.research as r, i (i)}
            <li><span class="src-k">{r.when}</span><span class="src-v"><Places text={r.text} /></span></li>
          {/each}
        </ul>
      </div>
    {/if}
    {#if src.data.length}
      <div class="src-g">
        <h4 class="src-h">Data</h4>
        <ul class="src-l plain">
          {#each src.data as t, i (i)}<li><span class="src-v">{t}</span></li>{/each}
        </ul>
      </div>
    {/if}
  </details>
{/if}

<style>
  /* The opened bubble's sections (the working, the interviews), each closed
     by a hairline above the answer. One type scale throughout:
       section title   13 / 600 / label
       row label       12 / 500 / label-2   (step labels, Historic / Rerun)
       text            13 / 400 / label
       meta            12 / 400 / label-2 */
  .sec { margin: 0 0 14px; padding: 2px 0 14px; border-bottom: 0.5px solid var(--separator); }
  .sec.live { margin-bottom: 10px; padding: 0 0 10px; }
  .sec-h { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin: 0 0 10px; font-size: 13px; font-weight: 600; line-height: 1.3; letter-spacing: -0.005em; color: var(--label); }
  .sec-n { font-size: 12px; font-weight: 400; color: var(--label-2); font-variant-numeric: tabular-nums; }
  /* The working: label / text rows on one grid, so every label shares a
     column. Live, a mark leads each row: a check when done, a breathing dot
     on the step in hand. */
  .steps {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: fit-content(10em) minmax(0, 1fr);
    column-gap: 14px;
    row-gap: 7px;
    align-items: baseline;
  }
  .live .steps { grid-template-columns: 14px fit-content(10em) minmax(0, 1fr); column-gap: 8px; row-gap: 4px; }
  .steps li { display: contents; }
  .steps .k { grid-column: -3; font-size: 12px; font-weight: 500; line-height: 1.45; color: var(--label-2); }
  .steps .v { grid-column: -2; font-size: 13px; line-height: 1.45; color: var(--label); }
  .steps .bare .v { grid-column: -3 / -1; }
  .live .steps .k, .live .steps .v { font-size: 12.5px; line-height: 1.4; color: var(--label-2); }
  .live .steps .doing .k, .live .steps .doing .v { color: var(--label); }
  .steps .k, .steps .v, .steps .mark { animation: float-in 0.28s cubic-bezier(0.2, 0.9, 0.3, 1.2); }
  .sec:not(.live) .steps .k, .sec:not(.live) .steps .v { animation: none; }
  .steps .mark { grid-column: 1; align-self: start; display: inline-flex; align-items: center; justify-content: center; height: 17.5px; color: var(--tint); }
  /* Narrow, finished: each label over its text (the bubble's column, WhatIf .hold, is the container). */
  @container (max-width: 472px) {
    .sec:not(.live) .steps { grid-template-columns: minmax(0, 1fr); row-gap: 1px; }
    .sec:not(.live) .steps .k, .sec:not(.live) .steps .v, .sec:not(.live) .steps .bare .v { grid-column: 1; }
    .sec:not(.live) .steps li:not(:first-child) > :first-child { margin-top: 8px; }
  }
  .steps .mark i { width: 6px; height: 6px; border-radius: 999px; background: var(--tint); animation: breathe 1s ease-in-out infinite; }
  @keyframes breathe { 50% { opacity: 0.25; transform: scale(0.7); } }
  @keyframes float-in { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
  /* The interviews. A what-if (when there's more than one) heads its own
     block; each wording of the question heads its people, in italics; each
     person is a header line (name, who they are, and — right-aligned, the
     only accent — Changed) over a three-column grid: Historic / Rerun, the
     vote and its likelihood, then their words. Hairlines between people. */
  .iv-w + .iv-w { margin-top: 18px; }
  .iv-wh { margin: 0 0 2px; font-size: 12px; font-weight: 600; line-height: 1.3; color: var(--label-2); }
  .iv-g + .iv-g { margin-top: 20px; }
  .iv-q { margin: 0 0 2px; font-size: 12.5px; line-height: 1.4; font-style: italic; color: var(--label-2); }
  .iv-a { list-style: none; margin: 0; padding: 0; }
  .iv-a li { padding: 10px 0; }
  .iv-a li + li { border-top: 0.5px solid var(--separator); }
  .iv-a li:last-child { padding-bottom: 0; }
  .iv-a li.misread { opacity: 0.5; }
  .iv-who { display: flex; align-items: baseline; gap: 12px; margin: 0 0 6px; font-size: 12px; line-height: 1.4; color: var(--label-2); }
  .iv-who > span { min-width: 0; }
  .iv-who b { margin-right: 2px; font-size: 13px; font-weight: 600; color: var(--label); }
  .iv-flag { flex: none; margin-left: auto; font-size: 12px; font-style: normal; font-weight: 500; color: var(--label-2); }
  .iv-flag.moved { color: var(--tint); }
  .iv-rows { display: grid; grid-template-columns: 52px 84px minmax(0, 1fr); column-gap: 12px; row-gap: 6px; align-items: baseline; margin: 0; }
  .iv-rows dt { font-size: 12px; font-weight: 500; line-height: 1.45; color: var(--label-2); }
  .iv-rows dd { margin: 0; }
  .iv-c { font-size: 13px; font-weight: 500; line-height: 1.45; color: var(--label); }
  .iv-c small { display: block; font-size: 11.5px; font-weight: 400; line-height: 1.3; color: var(--label-2); font-variant-numeric: tabular-nums; }
  .iv-say { font-size: 13px; line-height: 1.45; color: var(--label); }
  /* Narrow: the words drop under the vote, in the vote's column. */
  @container (max-width: 472px) {
    .iv-rows { grid-template-columns: 52px minmax(0, 1fr); row-gap: 2px; }
    .iv-say { grid-column: 2; margin-bottom: 6px; }
    .iv-c small { display: inline; margin-left: 6px; }
  }
  /* Sources: subsections under the section title, each a quiet header (and
     count) over key / line rows: a newspaper's date, its one-line summary and,
     beneath, the paper; a finding's year and claim; the data, one per row. */
  .src-g + .src-g { margin-top: 18px; }
  .src-sum { cursor: pointer; list-style: none; user-select: none; align-items: center; gap: 6px; margin: 0; }
  .src-sum::-webkit-details-marker { display: none; }
  .src-sum:hover { opacity: 0.75; }
  .src-sum:focus-visible { outline: 2px solid #3876b7; outline-offset: 2px; border-radius: 4px; }
  .src-chev { display: inline-flex; color: var(--label-2); transition: transform 0.18s ease; }
  details[open] > .src-sum { margin-bottom: 10px; }
  details[open] > .src-sum .src-chev { transform: rotate(180deg); }
  .src-h { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin: 0 0 8px; font-size: 12px; font-weight: 600; line-height: 1.3; color: var(--label-2); }
  .src-l { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: fit-content(6.5em) minmax(0, 1fr); column-gap: 14px; row-gap: 9px; align-items: baseline; }
  .src-l li { display: contents; }
  .src-k { grid-column: 1; font-size: 12px; font-weight: 500; line-height: 1.45; color: var(--label-2); font-variant-numeric: tabular-nums; }
  .src-v { grid-column: 2; font-size: 13px; line-height: 1.45; color: var(--label); }
  .src-v small { display: block; margin-top: 1px; font-size: 12px; line-height: 1.35; color: var(--label-2); }
  .src-l.plain { grid-template-columns: minmax(0, 1fr); row-gap: 5px; }
  .src-l.plain .src-v { grid-column: 1; font-size: 12.5px; color: var(--label-2); }
  /* In the working (steps, interviews) every place is dotted in the text's own
     colour; blue is kept for states in the message itself. */
  :global(.sa .whatif) .steps :global(.place), :global(.sa .whatif) .iv :global(.place), :global(.sa .whatif) .src :global(.place) { text-decoration-color: currentColor; }
  @media (prefers-reduced-motion: reduce) {
    .src-chev { transition: none; }
    .steps .k, .steps .v, .steps .mark { animation: none; }
    .steps .mark i { animation: none; }
  }
</style>
