// What the robot says (the Narrator's pure parts): a finished rerun's steps
// (traceOf), what it drew on (sourcesOf), and the one line for the page's
// state right now (say), in the order docs/handoff-ui.md lists.
import type { Election } from './history';
import type { ActiveRun } from './runs';
import type { Choice, Kind, RunResult, Slice, Step, Voter, WhatIf } from './schemas';
import type { Server, ShownRun, Sim } from './state';
import type { Names } from './types';
import type { BubbleSources, Message } from './whatif';

/** A finished rerun's steps come out one at a time, this far apart, ms. */
export const STEP_MS = 420;

export const CONFIDENCE: Readonly<Record<'high' | 'medium' | 'low', string>> = {
  high: 'High confidence: who could vote is arithmetic on census counts.',
  medium: 'Medium confidence: where people lived is on record; how they’d have voted there is inferred.',
  low: 'Low confidence: what people cared about is the hardest thing to change and know.',
};

export const KIND_NOTE: Readonly<Record<Kind, string>> = {
  franchise: 'Who can vote, high confidence.',
  population: 'Who lives where, medium confidence.',
  issue: 'What people care about, low confidence.',
  candidate: 'Who is on the ballot, low confidence.',
};

const pct = (r: number) => `${Math.round(r * 100)}%`;

/**
 * A rerun's steps, from what the server did: how your words were read, what
 * changed, who was asked again, what it counted, and how sure it is. Each
 * line is "Label: text", like the server's, so the bubble sets it as a row.
 */
export function traceOf(res: RunResult, text: string, keys: readonly string[], y: number): string[] {
  const out: string[] = [];
  const typedRead = res.applied.filter((a) => !keys.includes(a.key));
  if (text) {
    out.push(typedRead.length ? `Read: “${text}” as ${typedRead.map((a) => a.label).join(', ')}.` : `Read: “${text}”.`);
  }
  if (res.unknown) out.push(`Left out: “${res.unknown}”. I couldn’t model it.`);
  const chosenLabels = res.applied.filter((a) => keys.includes(a.key)).map((a) => a.label);
  if (chosenLabels.length) out.push(`Applied: ${chosenLabels.join(', ')}.`);
  // The server's lines: what changed (and whose behaviour new voters
  // borrow) first; the research, the numbers and how sure after the
  // interviews.
  const how = res.howIGotThis ?? [];
  // A typed change the server reinterpreted ("Not quite what you asked") leads.
  const isChange = (l: string) => /^(Not quite what you asked|What changed|New voters borrow)/.test(l);
  out.push(...how.filter(isChange));
  const applied = res.applied.map((a) => a.key);
  const labelOf = (k: string) => res.applied.find((a) => a.key === k)?.label || k;
  const asked = (res.cohortEffects ?? []).filter((c) => applied.includes(c.whatIf));
  const interviewed = asked.length > 0 || !!res.interview?.byWhatIf.length;
  const pre = res.pre;
  if (pre?.voters && interviewed) {
    // Each voter's brief, then the interview before any change: the
    // baseline, and the leakage tests when the run had them.
    const n = `${pre.voters} synthetic voters${pre.interviews > pre.voters ? ` (${pre.interviews} interviews)` : ''}`;
    const leak: string[] = [];
    if (pre.recall) leak.push(`In ${pre.recall.n} recall probes the model named the real winner ${pct(pre.recall.winnerRate)} of the time.`);
    if (pre.swap) leak.push(`With party labels swapped, answers followed the platforms ${pct(pre.swap.platformRate)} of the time.`);
    const asOf = pre.asOf
      ? new Date(`${pre.asOf}T12:00:00`).toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' })
      : '';
    const [lo, hi] = pre.items ?? [];
    let items = '';
    if (hi) items = lo === hi ? `${lo}` : `${lo}–${hi}`;
    out.push(
      `Briefed: Each voter got a life, a home state and the ballot${asOf ? `, dated ${asOf}` : ''}. ` +
        (items ? `Each read ${items} real newspaper items from that year. ` : `No period newspapers were available for ${y}. `) +
        'Candidates appeared as neutral letters, not names.',
    );
    out.push(
      `Pre-interviewed: ${n}, in ${y} as it was. This set the baseline${leak.length ? ' and tested for leakage' : ''}.${leak.length ? ` ${leak.join(' ')}` : ''}`,
    );
  }
  // The exact words that put each change into the voters' world: settled
  // facts, or news printed on the nominee's own ballot line.
  const told = applied.filter((k) => res.told?.[k]);
  for (const k of told) {
    const t = res.told?.[k];
    if (!t) continue;
    const lead = told.length > 1 ? `${labelOf(k)}. ` : '';
    const said = [...(t.facts ?? []), ...(t.news ?? [])].map((s) => `“${s}”`).join(' ');
    const where = t.news?.length && !t.facts?.length ? ' Printed as recent news on the nominee’s ballot line.' : '';
    const planks = [
      t.added?.length ? ` Added to the platforms: ${t.added.map((p) => p.replace(/\.$/, '')).join('; ')}.` : '',
      t.dropped?.length ? ` Taken off the platforms: ${t.dropped.join(', ')}.` : '',
      // Staged: real items the change makes false come out; news from the changed world goes in.
      t.removed ? ` Took out ${t.removed} newspaper item${t.removed === 1 ? '' : 's'} the change makes false.` : '',
      t.items?.length ? ` Their newspapers also carried: ${t.items.map((i) => `“${i.text}”`).join(' ')}` : '',
    ].join('');
    out.push(`Told the voters: ${lead}${said}${where}${planks}`);
  }
  if (asked.length) {
    const people = Math.max(
      ...applied.map((k) => asked.filter((c) => c.whatIf === k).reduce((sum, c) => sum + (c.n || 0), 0)),
    );
    const wordings = (pre?.wordings ?? 0) > 1 ? ` Each heard one of ${pre?.wordings} wordings of the question.` : '';
    out.push(`Asked again: ${people} people in ${new Set(asked.map((c) => c.cohort)).size} groups, now with the change.${wordings}`);
    out.push('Measured: Each person’s answer with the change, minus their answer without it.');
  }
  // After the research, how the interviews compare with the closest real cases.
  const rest = how.filter((l) => !isChange(l));
  const lastFound = rest.map((l) => l.startsWith('What historians found')).lastIndexOf(true);
  const against = (res.evidence ?? [])
    .filter((e) => applied.includes(e.whatIf) && e.agreementDetail)
    .map((e) => `Against history: ${e.agreementDetail}`);
  rest.splice(lastFound + 1, 0, ...against);
  out.push(...rest);
  if (res.states.length) out.push(`Counted: ${res.states.length} states.`);
  return out;
}

/**
 * What a rerun drew on, for the bubble's Sources: the dated newspapers in
 * the voters' briefs, the research behind each applied what-if, and the data.
 */
export function sourcesOf(res: RunResult): BubbleSources | null {
  const applied = res.applied.map((a) => a.key);
  const ev = (res.evidence ?? []).filter((e) => applied.includes(e.whatIf));
  const research = ev.flatMap((e) => e.findings.map((f) => ({ when: f.when || '', text: f.claim })));
  const cited = new Set(ev.flatMap((e) => e.findings.flatMap((f) => f.sources.map((s) => s.title))));
  const reading = res.reading ?? [];
  const data = (res.sources ?? [])
    .map((s) => s.title)
    .filter((t) => !cited.has(t) && !(reading.length && /Chronicling America/.test(t)));
  return reading.length || research.length || data.length ? { reading, research, data } : null;
}

const lower = (label: string) =>
  /^(Black|White|Latino|Southern|Northern|Irish|Catholic|Plains|New|Progressive|Loyal|Socialist|Northerners|\d)/.test(label)
    ? label
    : label.charAt(0).toLowerCase() + label.slice(1);

/** One line about a group: who couldn't vote, stayed home, or how those who voted chose. */
export function aboutGroup(s: Slice, y: number, nm: Names): string {
  const voted = s.A + s.B + s.O;
  if (s.barred >= 0.95) return `${s.label} couldn’t vote in ${y}.`;
  if (s.barred >= 0.5) return `${Math.round(s.barred * 10)} in 10 ${lower(s.label)} couldn’t vote in ${y}.`;
  if (voted < 0.02) return `Most ${lower(s.label)} stayed home in ${y}.`;
  let k: 'A' | 'B' | 'O' = 'O';
  if (s.A >= s.B && s.A >= s.O) k = 'A';
  else if (s.B >= s.O) k = 'B';
  return `${Math.round((s[k] / voted) * 100)}% of ${lower(s.label)} who voted chose ${nm[k] ?? ''}.`;
}

const did = (k: Choice, nm: Names): string => {
  switch (k) {
    case 'A':
      return `voted for ${nm.A}`;
    case 'B':
      return `voted for ${nm.B ?? ''}`;
    case 'O':
      return `voted for ${nm.O === 'Others' ? 'a third party' : nm.O}`;
    case 'home':
      return 'stayed home';
    case 'barred':
      return 'couldn’t vote';
    default:
      return k satisfies never;
  }
};

/** Everything say() reads. */
export interface SayInput {
  readonly server: Server;
  readonly year: number;
  readonly election: Election;
  readonly run: ActiveRun | null;
  /** The run is this year's. */
  readonly running: boolean;
  readonly runError: string | null;
  /** Why the year's groups didn't load. */
  readonly simFailed: string | null;
  readonly sim: Sim | null;
  /** A just-tapped suggestion. */
  readonly toggled: string | null;
  readonly whatIfs: readonly WhatIf[];
  /** The picked group. */
  readonly slice: string | null;
  readonly showing: 'history' | 'whatif';
  readonly result: ShownRun | null;
  readonly names: Names;
  /** Someone from the picked group, once fetched. */
  readonly person: Voter | null;
  /** That person is being fetched. */
  readonly finding: boolean;
  /** The typed words. */
  readonly draft: string;
  /** How many of the rerun's steps are out (Infinity: all of them). */
  readonly shown: number;
  /** The sample stand-in is on. */
  readonly sample: boolean;
}

function running(y: number, r: ActiveRun): Message {
  const steps: Step[] = [];
  if (r.text) steps.push({ text: `Reading “${r.text}”.`, state: 'done' });
  if (r.labels.length) steps.push({ text: `Applying ${r.labels.join(', ')}.`, state: 'done' });
  if (r.steps?.length) {
    return {
      text: 'That’s new to me, so I’m modelling it. This will take a minute.',
      steps: [...steps.slice(r.text ? 1 : 0), ...r.steps],
      busy: true,
    };
  }
  steps.push({ text: r.total ? `Rerunning ${y}: ${r.done} of ${r.total} states counted.` : `Rerunning ${y}.`, state: 'doing' });
  return { text: `Rerunning ${y}…`, steps, busy: true };
}

function verdict(res: ShownRun, sample: boolean): Message {
  if (!res.applied.length && res.unknown) {
    return {
      text: `I couldn’t turn “${res.unknown}” into a change I can model${sample ? ' with sample data' : ''}.${res.unknownWhy ? ` ${res.unknownWhy}` : ''} Try one of the what-ifs below.`,
    };
  }
  // Typed words the rerun understood: say how they were read.
  const read = res.text ? res.applied.find((a) => !res.keys.includes(a.key)) : undefined;
  // "the voters I interviewed" is "the voters" (publish.py says that now;
  // bundles published before then still carry the old words).
  const summary = res.summary.replaceAll('the voters I interviewed', 'the voters');
  return {
    steps: res.trace.map((t) => ({ text: t, state: 'done' })),
    interview: res.interview ?? null, // shown when the bubble is opened (More)
    sources: sourcesOf(res), // …and what it drew on
    // The steps already say how the words were read.
    text: `${read && !res.trace.length ? `I read “${res.text}” as ${read.label}. ` : ''}${summary}${res.unknown ? ` I left out “${res.unknown}”; I couldn’t model it.` : ''}`,
    // The summary already names the tier when the server flags it (a built or very-low what-if).
    detail:
      res.confidence && !(res.confidenceLabel && res.summary.includes(res.confidenceLabel)) ? CONFIDENCE[res.confidence] : '',
  };
}

/** What the robot says now. */
export function say(i: SayInput): Message {
  const { year: y, sim: s, result: res, showing: show, names: nm } = i;
  if (i.server === 'connecting') return { text: `Getting ${y}’s voters ready.`, busy: true };
  if (i.server === 'unsupported' || i.server === 'offline') {
    return {
      text:
        i.server === 'unsupported'
          ? 'This server has no simulation service yet, so I can’t rerun elections here.'
          : 'I can’t reach the simulation server, so I can’t rerun elections yet.',
      detail: 'The elections themselves are all here. Sample data shows how a rerun works.',
      actions: [
        { key: 'sample', label: 'Use Sample Data', primary: true },
        { key: 'retry', label: 'Try Again' },
      ],
    };
  }
  if (i.server === 'auth') return { text: 'Sign in to rerun elections.', actions: [{ key: 'retry', label: 'Try Again' }] };
  if (i.election.unopposed) {
    return {
      text: `${i.election.candidates[0].name} ran unopposed in ${y}, so there’s nothing to rerun.`,
      actions: [{ key: 'shuffle', label: 'Another Election', primary: true }],
    };
  }
  if (i.running && i.run) return running(y, i.run);
  if (i.runError) return { text: i.runError, actions: [{ key: 'rerun', label: 'Try Again', primary: true }] };
  if (i.simFailed && !s) return { text: i.simFailed, actions: [{ key: 'retry', label: 'Try Again' }] };
  if (!s) return { text: `Getting ${y}’s voters ready.`, busy: true };
  const w = i.toggled ? i.whatIfs.find((x) => x.key === i.toggled) : undefined;
  if (w) return { text: w.detail, detail: `${KIND_NOTE[w.kind]} Press Rerun to see what happens.` };
  // A group picked: someone from it, in their own words, and what could
  // change their fate.
  const slice = i.slice;
  if (slice) {
    const g = (show === 'whatif' && res ? res.slices : s.slices).find((x) => x.key === slice);
    const reach = i.whatIfs.filter((x) => x.slices.includes(slice)).map((x) => x.label);
    const could = reach.length ? `What could change that: ${reach.join(', ')}.` : '';
    const person = i.person;
    if (person) {
      const now = show === 'whatif' && person.now && person.now !== person.history ? ` In your ${y}, ${did(person.now, nm)}.` : '';
      const fate = `In ${y}, ${did(person.history, nm)}.${now}`;
      return {
        quote: person.quote,
        by: [person.name, person.line].filter(Boolean).join(', '),
        text: `${fate}${could && show !== 'whatif' ? ` ${could}` : ''}`,
      };
    }
    if (g) return { text: aboutGroup(g, y, nm), detail: i.finding ? 'Finding someone from this group…' : could };
  }
  // Typing: say what will happen to the words.
  if (i.draft.trim() && !slice) {
    return {
      text: 'I’ll read that and turn it into a change I can model.',
      steps: [{ text: `Reading “${i.draft.trim()}”…`, state: 'doing' }],
      detail: 'Press Rerun to run it.',
    };
  }
  if (res && show === 'whatif' && res.trace.length && i.shown < res.trace.length) {
    return {
      text: 'Working it through…',
      steps: res.trace.slice(0, i.shown + 1).map((t, n) => ({ text: t, state: n < i.shown ? 'done' : 'doing' })),
      busy: true,
    };
  }
  if (res && show === 'whatif') return verdict(res, i.sample);
  if (res) return { text: `This is ${y} as it happened. Switch to Rerun to see yours.` };
  return {
    text: `Change one thing about ${y} and I’ll rerun it.`,
    // The newline breaks on a narrow window only (WhatIf .aside); a wide one reads it as a space.
    detail: 'Pick a counterfactual or type your own.\nTap a group to meet someone in it.',
  };
}
