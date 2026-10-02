// Sample mode: the simulation server's answers (api.ts), made up, so the page
// can be reviewed without that server. The page says "Sample" while this is
// on. The elections are real (history.ts): who ran, who won, which party
// carried each state. What a simulation would work out — how groups of voters
// split, what a what-if changes, how close each state was — is invented here
// by a small deterministic model: plausible, never authoritative. Ten
// elections have written stories (stories.ts); every other year gets the
// groups every election has (sampleEras.ts), above all the people who
// couldn't vote.
import type { Edits, Outcome, RunAsk, SimulacraApi } from './api';
import { ELECTION_YEARS, STATE_BY_CODE } from './geo';
import { type Election, electionOf } from './history';
import {
  adultsIn,
  BORDER,
  blackShare,
  ENSLAVED,
  ERA_PEOPLE,
  REGIONS,
  SOUTH,
  SPREAD,
  southFactor,
  votesIn,
} from './sampleData';
import { eraSlices, eraWhatIfs } from './sampleEras';
import type {
  DropTo,
  Fractions,
  Lean,
  Region,
  SampleContext,
  SliceSpec,
  StateWeights,
  VoterSpec,
  Votes,
} from './sampleTypes';
import type { Choice, Kind, RunResult, Slice, StateResult, Voter } from './schemas';
import { STORIES } from './stories';
import { type Bucket, bucketOf } from './types';

const clamp = (x: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, x));
/** A stable number in [0, 1) for a string. */
const unit = (s: string) => {
  let h = 2166136261;
  for (const ch of s) h = Math.imul(h ^ ch.charCodeAt(0), 16777619) >>> 0;
  return (h % 10007) / 10007;
};
const FIELDS = ['barred', 'home', 'A', 'B', 'O'] as const;
const IDX = { A: 0, B: 1, O: 2 } as const;
const round3 = (x: number) => Math.round(x * 1000) / 1000;

/** Who leads: A on a tie with anyone, then B over O. */
function leaderOf(v: Votes): Bucket {
  if (v.A >= v.B && v.A >= v.O) return 'A';
  return v.B >= v.O ? 'B' : 'O';
}
const topOf = (l: Lean): Bucket => leaderOf({ A: l[0], B: l[1], O: l[2] });

/** Where a group lives → state → weight, summing to 1 over the states voting in e. */
function weights(e: Election, where: Region, states?: StateWeights): Map<string, number> {
  const ev = new Map(e.states.map((s) => [s.code, s.ev]));
  const out = new Map<string, number>();
  const add = (code: string, w: number) => {
    if (ev.has(code) && w > 0) out.set(code, (out.get(code) ?? 0) + w);
  };
  if (states) for (const [c, w] of Object.entries(states)) add(c, w);
  else {
    switch (where) {
      case 'immigrant':
      case 'latino':
      case 'felony':
        for (const [c, w] of Object.entries(SPREAD[where])) add(c, w * (ev.get(c) ?? 0));
        for (const [c, v] of ev) add(c, v * 0.08);
        break;
      case 'black':
      case 'black-south':
      case 'black-north':
        for (const [c, v] of ev) {
          const south = SOUTH.includes(c) || BORDER.includes(c);
          if ((where === 'black-south' && !south) || (where === 'black-north' && south)) continue;
          add(c, v * blackShare(c, e.year));
        }
        break;
      case 'north':
        for (const [c, v] of ev) if (!SOUTH.includes(c)) add(c, v);
        break;
      case 'south':
      case 'new-england':
      case 'middle':
      case 'midwest':
      case 'plains':
      case 'industrial':
        for (const c of REGIONS[where]) add(c, ev.get(c) ?? 0);
        break;
      case 'all':
        for (const [c, v] of ev) add(c, v);
        break;
      default: {
        const never: never = where;
        throw new Error(`Unknown region ${String(never)}`);
      }
    }
  }
  const total = [...out.values()].reduce((a, b) => a + b, 0) || 1;
  for (const [c, w] of out) out.set(c, w / total);
  return out;
}

// ── The election as modelled ──
/** An unopposed election (1789, 1792, 1820): everyone who voted, voted for A. */
export const UNOPPOSED: Readonly<Votes> = { A: 1, B: 0, O: 0 };

/** The country's split: the popular vote when there is one, else one guessed from the electoral vote. */
function national(e: Election): Votes {
  const [a, b] = e.candidates;
  if (!b) return { ...UNOPPOSED };
  if (a.popular != null && b.popular != null) {
    const A = a.popular / 100;
    const B = b.popular / 100;
    return { A, B, O: Math.max(0, 1 - A - B) };
  }
  const A = 0.5 + (0.25 * (a.ev - b.ev)) / Math.max(1, a.ev + b.ev);
  return { A, B: 0.98 - A, O: 0.02 };
}

/** A state as modelled before any change: shares, votes cast (V, millions), electors, who carried it. */
interface Base extends Votes {
  readonly V: number;
  readonly ev: number;
  readonly won: string;
  readonly split: boolean;
}

function split(won: Bucket, lead: number, nat: Votes, h: number): Votes {
  if (won === 'O') {
    const o = Math.min(0.8, 0.46 + 0.14 * h + lead / 2);
    const ra = nat.A / Math.max(0.01, nat.A + nat.B);
    return { A: (1 - o) * ra, B: (1 - o) * (1 - ra), O: o };
  }
  let o = Math.min(0.3, nat.O * (0.5 + h));
  let w = (1 - o + lead) / 2;
  if (w - o < 0.03) {
    o = Math.max(0, (1 + lead) / 3 - 0.03);
    w = (1 - o + lead) / 2;
  }
  const r = Math.max(0, 1 - o - w);
  return won === 'A' ? { A: w, B: r, O: o } : { A: r, B: w, O: o };
}

// Each state's vote share by candidate. The winner is history's; how close
// it was is modelled — a state that stayed with the same party in the
// elections around this one was safe, one that swung was close — except for
// the states the written stories carry real shares for.
function baseline(e: Election): Map<string, Base> {
  const nat = national(e);
  const fixed = STORIES[e.year]?.states ?? {};
  const i = ELECTION_YEARS.indexOf(e.year);
  const near = [-2, -1, 1, 2].flatMap((d) => {
    const y = ELECTION_YEARS[i + d];
    const n = y === undefined ? null : electionOf(y);
    return n ? [n] : [];
  });
  const weight = (s: { code: string; ev: number }) => s.ev * southFactor(s.code, e.year);
  const total = e.states.reduce((a, s) => a + weight(s), 0);
  const votes = votesIn(e.year);
  const out = new Map<string, Base>();
  for (const s of e.states) {
    const h = unit(`${e.year}:${s.code}`);
    const real = fixed[s.code];
    let sh: Votes;
    if (real) sh = { A: real[0], B: real[1], O: Math.max(0, 1 - real[0] - real[1]) };
    else {
      const same = near.filter((n) => n.states.find((x) => x.code === s.code)?.party === s.party).length;
      const stable = near.length ? same / near.length : 0.5;
      const lead = ((2 + stable * stable * 24) * (0.7 + 0.6 * h) + Math.abs(nat.A - nat.B) * 35) / 100;
      sh = split(bucketOf(s.won), lead, nat, h);
    }
    out.set(s.code, { ...sh, V: (votes * weight(s)) / total, ev: s.ev, won: s.won, split: s.party === 'SP' });
  }
  return out;
}

// ── The groups ──
/** A group as the model carries it through a run. */
interface ModelSlice extends Fractions {
  readonly key: string;
  readonly label: string;
  readonly where: Region;
  readonly states: StateWeights | undefined;
  readonly mirror: boolean;
  readonly tilt: number;
  /** Millions. */
  readonly adults: number;
  readonly turnout: number;
  readonly leanIf: Lean;
  readonly voter: VoterSpec | null;
}

function compose(barred: number, turnout: number, lean: Lean): Fractions {
  const voting = (1 - barred) * turnout;
  return { barred, home: 1 - barred - voting, A: voting * lean[0], B: voting * lean[1], O: voting * lean[2] };
}

function build(e: Election, nat: Votes, s: SliceSpec): ModelSlice {
  const tilt = s.tilt ?? 0;
  const voted = s.lean.some((x) => x > 0);
  let leanIf: Lean;
  if (s.mirror) {
    // A group that votes like its own state (women) splits like the country.
    const m = [nat.A + tilt / 2, nat.B - tilt / 2, nat.O].map((x) => Math.max(0, x));
    const sum = m.reduce((a, b) => a + b, 0) || 1;
    leanIf = [(m[0] ?? 0) / sum, (m[1] ?? 0) / sum, (m[2] ?? 0) / sum];
  } else if (s.leanIf) leanIf = s.leanIf;
  else leanIf = voted ? s.lean : [0.5, 0.5, 0];
  const lean = voted ? s.lean : leanIf;
  return {
    key: s.key,
    label: s.label,
    where: s.where,
    states: s.states,
    mirror: !!s.mirror,
    tilt,
    adults: adultsIn(e.year) * s.share,
    turnout: s.turnout,
    leanIf,
    voter: s.voter ?? null,
    ...compose(s.barred, s.turnout, lean),
  };
}

const slicesFor = (e: Election): ModelSlice[] => {
  const nat = national(e);
  return (STORIES[e.year]?.slices ?? eraSlices(e, nat)).map((s) => build(e, nat, s));
};

// ── What-ifs ──
export interface ModelWhatIf {
  readonly key: string;
  readonly label: string;
  readonly kind: Kind;
  readonly detail: string;
  readonly slices: readonly string[];
  readonly apply: (c: SampleContext) => void;
}

function whatIfsFor(e: Election): ModelWhatIf[] {
  if (e.unopposed) return [];
  return (STORIES[e.year]?.whatIfs ?? eraWhatIfs(e.year)).map(([key, label, kind, detail, slices, apply]) => ({
    key,
    label,
    kind,
    detail,
    slices,
    apply,
  }));
}

// Words in a typed what-if → the what-if it most likely means. Sample mode
// only; the server reads free text for real.
const WORDS: readonly (readonly [RegExp, readonly string[]])[] = [
  [/wom[ae]n|suffrag|19th/i, ['women', 'no-19th']],
  [/15th|jim crow|poll tax|literacy|disenfranch|voting rights|black (men|voters|southerners)/i, ['fifteenth']],
  [/emancipat|slave|abolit|freed/i, ['emancipation']],
  [/three.?fifths|3\/5/i, ['three-fifths']],
  [/propert|landless|freehold/i, ['no-property']],
  [/\b18\b|eighteen|young|youth|26th/i, ['age18']],
  [/felon|prison|convict|incarcerat/i, ['felons']],
  [/migrat/i, ['migration']],
  [/everyone|every adult|universal|compulsory|all adults/i, ['everyone']],
  [/panic|depression|crash|economy|recession/i, ['panic']],
  [/nader/i, ['nader-out']], [/wallace/i, ['wallace-out']], [/thurmond|dixiecrat/i, ['thurmond-out']],
  [/taft/i, ['taft-out']], [/debs|socialist/i, ['debs-out']], [/comey|email/i, ['comey']],
  [/debate|televis|\btv\b/i, ['debate']], [/sedition|alien/i, ['sedition']],
  [/unite|split|douglas|breckinridge/i, ['unite']], [/ballot|butterfly|palm beach/i, ['ballot']],
  [/money|spend|hanna|campaign/i, ['money']], [/peace|vietnam|paris/i, ['peace']], [/turnout/i, ['turnout', 'everyone']],
];
function understand(text: string, available: readonly ModelWhatIf[]): string | null {
  for (const [re, keys] of WORDS) {
    if (!re.test(text)) continue;
    const k = keys.find((x) => available.some((w) => w.key === x));
    if (k) return k;
  }
  return null;
}

// ── A run ──
/** One change to the country's votes, applied state by state once every what-if has run. */
type Delta =
  | { readonly type: 'votes'; readonly where: ReadonlyMap<string, number>; readonly A: number; readonly B: number; readonly O: number }
  | { readonly type: 'mirror'; readonly f: number; readonly tilt: number }
  | { readonly type: 'swing'; readonly pts: number; readonly to: 'A' | 'B'; readonly where: ReadonlyMap<string, number> | null }
  | { readonly type: 'drop'; readonly frac: number; readonly to: DropTo; readonly where: ReadonlyMap<string, number> | null }
  | { readonly type: 'shift'; readonly states: StateWeights; readonly to: 'A' | 'B' };

function fmtM(m: number): string {
  if (m >= 0.95) return `${m.toFixed(1).replace(/\.0$/, '')} million`;
  if (m >= 0.001) return `${Math.round(m * 1000).toLocaleString('en-US')},000`;
  return 'a few hundred';
}
// "Women" → "women" mid-sentence; proper adjectives and numbers stay.
const lower = (label: string) =>
  /^(Black|White|Latino|Southern|Northern|Irish|Catholic|Plains|New|Progressive|Loyal|Socialist|Northerners|\d)/.test(label)
    ? label
    : label.charAt(0).toLowerCase() + label.slice(1);
function howMany(share: number): string {
  if (share > 0.8) return 'nearly all';
  if (share > 0.6) return 'most';
  return 'more of them';
}

function makeContext(e: Election, base: ReadonlyMap<string, Base>) {
  const slices = new Map(slicesFor(e).map((s) => [s.key, s]));
  const deltas: Delta[] = [];
  const leads: string[] = [];
  const evs = new Map<string, number>();
  const name = (k: Bucket) =>
    k === 'O' ? (e.candidates[2]?.short ?? 'third parties') : (e.candidates.find((c) => c.key === k)?.short ?? '');
  const votes = votesIn(e.year);
  const set = (s: ModelSlice, next: Partial<Fractions>) => slices.set(s.key, { ...s, ...next });
  const at = (s: ModelSlice) => weights(e, s.where, s.states);
  /** The share of a group living inside region weights w. */
  const inside = (s: ModelSlice, w: ReadonlyMap<string, number> | null) =>
    w ? [...at(s)].reduce((a, [c, x]) => a + (w.has(c) ? x : 0), 0) : 1;
  const ctx: SampleContext = {
    year: e.year,
    has: (key) => slices.has(key),
    // Some of a group's barred members (or all) can vote, at the group's
    // turnout (or `turnout`), splitting like `lean` — or, for a group that
    // votes like its own state (women), like each state's voters.
    enfranchise(key, { barred = 0, turnout, lean } = {}) {
      const s = slices.get(key);
      if (!s) return;
      const t = turnout ?? s.turnout;
      const l = lean ?? s.leanIf;
      const add = s.barred - barred;
      const had = s.A + s.B + s.O > 0.01;
      let next: Fractions;
      if (add >= 0) {
        next = { barred, home: s.home + add * (1 - t), A: s.A + add * t * l[0], B: s.B + add * t * l[1], O: s.O + add * t * l[2] };
      } else {
        const k = 1 + add / Math.max(0.001, 1 - s.barred);
        next = { barred, home: s.home * k, A: s.A * k, B: s.B * k, O: s.O * k };
      }
      const d = { A: (next.A - s.A) * s.adults, B: (next.B - s.B) * s.adults, O: (next.O - s.O) * s.adults };
      const total = d.A + d.B + d.O;
      if (s.mirror) deltas.push({ type: 'mirror', f: total / votes, tilt: s.tilt });
      else deltas.push({ type: 'votes', where: at(s), ...d });
      set(s, next);
      const who = key === 'enslaved' ? 'freed men' : lower(s.label);
      const more = had ? 'more ' : '';
      if (total < 0) leads.push(`${fmtM(-total)} ${who} lose the vote.`);
      else if (s.mirror) leads.push(`${fmtM(total)} ${more}${who} vote, splitting much like the men of their states.`);
      else {
        const m = topOf(l);
        const share = l[IDX[m]] / (l[0] + l[1] + l[2] || 1);
        leads.push(`${fmtM(total)} ${more}${who} vote, ${howMany(share)} for ${name(m)}.`);
      }
    },
    swing(key, pts, to) {
      const s = slices.get(key);
      if (!s) return;
      const from = to === 'A' ? 'B' : 'A';
      const moved = Math.min(s[from], (pts / 100) * (s.A + s.B + s.O));
      const next = { ...s };
      next[to] += moved;
      next[from] -= moved;
      slices.set(key, next);
      const d = { A: 0, B: 0, O: 0 };
      d[to] = moved * s.adults;
      d[from] = -moved * s.adults;
      deltas.push({ type: 'votes', where: at(s), ...d });
      leads.push(`${name(to)} gains ${pts} points with ${lower(s.label)}.`);
    },
    swingAll(pts, to, region, text) {
      const w = region ? weights(e, region) : null;
      deltas.push({ type: 'swing', pts, to, where: w });
      const from = to === 'A' ? 'B' : 'A';
      for (const s of [...slices.values()]) {
        const moved = Math.min(s[from], (pts / 100) * inside(s, w) * (s.A + s.B + s.O));
        if (moved <= 0) continue;
        const next = { ...s };
        next[to] += moved;
        next[from] -= moved;
        slices.set(s.key, next);
      }
      leads.push(text);
    },
    drop(frac, to, text, region) {
      const w = region ? weights(e, region) : null;
      deltas.push({ type: 'drop', frac, to, where: w });
      const toA = to.A ?? 0;
      const toB = to.B ?? 0;
      for (const s of [...slices.values()]) {
        const moved = s.O * frac * inside(s, w);
        if (moved > 0) set(s, { O: s.O - moved, A: s.A + moved * toA, B: s.B + moved * toB, home: s.home + moved * (1 - toA - toB) });
      }
      leads.push(text);
    },
    unite(frac, text) {
      ctx.drop(frac, { B: 1 }, text);
    },
    shift(states, to, text) {
      deltas.push({ type: 'shift', states, to });
      leads.push(text);
    },
    move(key, frac, toKey) {
      const s = slices.get(key);
      const t = slices.get(toKey);
      if (!s || !t) return;
      const mix = (k: (typeof FIELDS)[number]) => (1 - frac) * s[k] + frac * t[k];
      const mixed: Fractions = { barred: mix('barred'), home: mix('home'), A: mix('A'), B: mix('B'), O: mix('O') };
      deltas.push({ type: 'votes', where: at(s), A: (mixed.A - s.A) * s.adults, B: (mixed.B - s.B) * s.adults, O: (mixed.O - s.O) * s.adults });
      deltas.push({ type: 'votes', where: at(t), A: frac * t.A * s.adults, B: frac * t.B * s.adults, O: frac * t.O * s.adults });
      const lost = (s.A + s.B + s.O - (mixed.A + mixed.B + mixed.O)) * s.adults;
      set(s, mixed);
      leads.push(`${fmtM(lost)} fewer Black votes are cast in the North, and almost none are added in the South.`);
    },
    turnout(key, t) {
      const s = slices.get(key);
      if (!s) return;
      const was = (s.A + s.B + s.O) / Math.max(0.001, 1 - s.barred);
      const k = t / Math.max(0.001, was);
      const A = s.A * k;
      const B = s.B * k;
      const O = s.O * k;
      const home = Math.max(0, 1 - s.barred - A - B - O);
      deltas.push({ type: 'votes', where: at(s), A: (A - s.A) * s.adults, B: (B - s.B) * s.adults, O: (O - s.O) * s.adults });
      set(s, { A, B, O, home });
      leads.push(`${s.label.replace(/ voters$/, '')} turnout rises from ${Math.round(was * 100)}% to ${Math.round(t * 100)}%.`);
    },
    everyone() {
      const before = leads.length;
      let added = 0;
      for (const key of [...slices.keys()]) {
        const was = slices.get(key);
        if (!was) continue;
        if (was.barred > 0) {
          ctx.enfranchise(key, { barred: 0, turnout: 1 });
          const n = slices.get(key) ?? was;
          added += (n.A + n.B + n.O - (was.A + was.B + was.O)) * was.adults;
        }
        // Those who could vote and stayed home vote too; they're counted
        // with everyone else below.
        const n = slices.get(key) ?? was;
        if (n.home > 0.0005) {
          const k = n.home / (n.A + n.B + n.O || 1);
          set(n, { home: 0, A: n.A * (1 + k), B: n.B * (1 + k), O: n.O * (1 + k) });
        }
      }
      // Every other adult who didn't vote does now — a little more
      // Democratic from the New Deal on.
      const rest = Math.max(0, adultsIn(e.year) - votes - added);
      let dem = 0;
      if (e.candidates[0].family === 'democratic') dem = 1;
      else if (e.candidates[1]?.family === 'democratic') dem = -1;
      deltas.push({ type: 'mirror', f: rest / votes, tilt: e.year >= 1936 ? 0.03 * dem : 0 });
      added += rest;
      leads.length = before;
      leads.push(`Every adult votes: about ${fmtM(added)} more ballots.`);
    },
    apportion() {
      const table = e.year <= 1830 ? ENSLAVED.early : ENSLAVED.late;
      let lost = 0;
      for (const [code, s] of base) {
        const share = table[code];
        if (!share) continue;
        const cut = Math.round((s.ev - 2) * ((0.6 * share) / (1 - 0.4 * share)));
        if (cut > 0) {
          evs.set(code, s.ev - cut);
          lost += cut;
        }
      }
      leads.push(`The slave states lose ${lost} electoral votes.`);
    },
    enfranchiseBlackSouth({ lean }) {
      const adults = adultsIn(e.year) * 0.04 * 0.9 * 0.6;
      deltas.push({ type: 'votes', where: weights(e, 'black-south'), A: adults * lean[0], B: adults * lean[1], O: adults * lean[2] });
      leads.push(`${fmtM(adults)} Black Southerners vote, most for ${name(topOf(lean))}.`);
    },
  };
  return { ctx, deltas, leads, evs, slices };
}

/** Each state's votes after every change. */
function tally(base: ReadonlyMap<string, Base>, deltas: readonly Delta[]): Map<string, Votes> {
  const now = new Map<string, Votes>();
  for (const [code, s] of base) now.set(code, { A: s.A * s.V, B: s.B * s.V, O: s.O * s.V });
  for (const d of deltas) {
    switch (d.type) {
      case 'votes':
        for (const [code, w] of d.where) {
          const s = now.get(code);
          if (!s) continue;
          s.A += d.A * w;
          s.B += d.B * w;
          s.O += d.O * w;
        }
        break;
      case 'mirror':
        for (const [code, b] of base) {
          const s = now.get(code);
          if (!s) continue;
          const add = d.f * b.V;
          s.A += add * clamp(b.A + d.tilt / 2, 0, 1);
          s.B += add * clamp(b.B - d.tilt / 2, 0, 1);
          s.O += add * b.O;
        }
        break;
      case 'swing': {
        const from = d.to === 'A' ? 'B' : 'A';
        for (const [code, s] of now) {
          if (d.where && !d.where.has(code)) continue;
          const moved = Math.min(s[from], (d.pts / 100) * (s.A + s.B + s.O));
          s[from] -= moved;
          s[d.to] += moved;
        }
        break;
      }
      case 'drop':
        for (const [code, s] of now) {
          if (d.where && !d.where.has(code)) continue;
          const moved = s.O * d.frac;
          s.O -= moved;
          s.A += moved * (d.to.A ?? 0);
          s.B += moved * (d.to.B ?? 0);
        }
        break;
      case 'shift':
        for (const [code, f] of Object.entries(d.states)) {
          const s = now.get(code);
          if (!s) continue;
          const moved = Math.min(s.O, f * (s.A + s.B + s.O));
          s.O -= moved;
          s[d.to] += moved;
        }
        break;
      default: {
        const never: never = d;
        throw new Error(`Unknown change ${JSON.stringify(never)}`);
      }
    }
  }
  return now;
}

const RANK: Readonly<Record<Kind, number>> = { franchise: 0, population: 1, issue: 2, candidate: 2 };
const CONFIDENCE = ['high', 'medium', 'low'] as const;
const stateName = (code: string) => STATE_BY_CODE.get(code)?.name ?? code;
const list = (names: readonly string[]) =>
  names.length <= 2 ? names.join(' and ') : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
function pts(m: number): string {
  if (m < 0.1) return 'less than a tenth of a point';
  const p = m.toFixed(1);
  return `${p} point${p === '1.0' ? '' : 's'}`;
}
/** The gap between the first and second of three shares. */
const gap = (v: Votes) => {
  const [x = 0, y = 0] = [v.A, v.B, v.O].sort((p, q) => q - p);
  return x - y;
};

function rerunElection(e: Election, keys: readonly string[] = [], text = '', edits: Edits = {}): RunResult {
  const year = e.year;
  const base = baseline(e);
  const available = whatIfsFor(e);
  const { ctx, deltas, leads, evs, slices } = makeContext(e, base);
  const chosen = keys.flatMap((k) => available.filter((w) => w.key === k).slice(0, 1));
  let unknown: string | null = null;
  const typed = text.trim();
  if (typed) {
    const meant = understand(typed, available);
    const w = available.find((x) => x.key === meant);
    if (!w) unknown = typed;
    else if (!chosen.includes(w)) chosen.push(w);
  }
  for (const w of chosen) w.apply(ctx);
  const shortOf = (k: string) => e.candidates.find((c) => c.key === k)?.short ?? '';
  // Groups changed by hand: the new make-up, its votes spread over the
  // group's states.
  let edited = 0;
  for (const [key, d] of Object.entries(edits)) {
    const s = slices.get(key);
    if (!s) continue;
    const moved = (k: (typeof FIELDS)[number]) => Math.max(0, s[k] + (d[k] ?? 0));
    const next: Fractions = { barred: moved('barred'), home: moved('home'), A: moved('A'), B: moved('B'), O: moved('O') };
    deltas.push({
      type: 'votes',
      where: weights(e, s.where, s.states),
      A: (next.A - s.A) * s.adults,
      B: (next.B - s.B) * s.adults,
      O: (next.O - s.O) * s.adults,
    });
    slices.set(key, { ...s, ...next });
    const moves = (['A', 'B'] as const).flatMap((k) => {
      const n = Math.round((d[k] ?? 0) * 50);
      return n ? [`${shortOf(k)} ${n > 0 ? 'gains' : 'loses'} ${Math.abs(n)} in 50`] : [];
    });
    if (moves.length) {
      leads.push(`Among ${lower(s.label)}, ${moves.join(' and ')}.`);
      edited++;
    }
  }

  const now = tally(base, deltas);
  const ev: Votes = {
    A: e.candidates[0].ev,
    B: e.candidates[1]?.ev ?? 0,
    O: e.candidates.slice(2).reduce((a, c) => a + c.ev, 0),
  };
  const states: (StateResult & { ev: number })[] = [];
  for (const [code, b] of base) {
    const s = now.get(code) ?? { A: 0, B: 0, O: 0 };
    // A state history split between candidates stays split.
    const flipped = !b.split && leaderOf(s) !== leaderOf(b);
    let won = b.won;
    if (flipped) {
      const to = leaderOf(s);
      const from = bucketOf(b.won);
      const moved = Math.min(b.ev, ev[from]);
      ev[from] -= moved;
      ev[to] += moved;
      won = to;
    }
    const cutTo = evs.get(code);
    if (cutTo !== undefined) {
      const cut = cutTo - b.ev;
      if (b.split) {
        ev.A += Math.ceil(cut / 2);
        ev.B += Math.floor(cut / 2);
      } else ev[bucketOf(won)] += cut;
    }
    states.push({ code, won, flipped, ev: cutTo ?? b.ev, margin: (gap(s) / (s.A + s.B + s.O || 1)) * 100 });
  }
  const total = ev.A + ev.B + ev.O;
  const best = leaderOf(ev);
  const changed = states.some((s) => s.flipped) || evs.size > 0;
  let winner: Bucket | null = 'A';
  if (changed) winner = ev[best] > total / 2 ? best : null;

  // The verdict: what changed, then what it did.
  const nameOf = (k: Bucket) => (k === 'O' ? (e.candidates[2]?.short ?? 'third parties') : shortOf(k));
  const flips = states.filter((s) => s.flipped).sort((a, b) => b.ev - a.ev);
  const score = (k: Bucket) => `${ev[k]}–${ev[k === 'A' ? 'B' : 'A']}`;
  // Flips that cost history's winner a state, and ones that gave it one.
  const lost = flips.filter((f) => base.get(f.code)?.won === 'A');
  const gained = flips.filter((f) => f.won === 'A');
  const names = (arr: readonly StateResult[], n: number) =>
    arr.length > n
      ? `${arr
          .slice(0, n)
          .map((f) => stateName(f.code))
          .join(', ')} and ${arr.length - n} more`
      : list(arr.map((f) => stateName(f.code)));
  const to = (arr: readonly StateResult[]) => {
    const [only, ...more] = [...new Set(arr.map((f) => bucketOf(f.won)))];
    return only && !more.length ? ` to ${nameOf(only)}` : '';
  };
  const flipOf = (arr: readonly StateResult[]) => `${names(arr, 3)} flip${arr.length === 1 ? 's' : ''}${to(arr)}`;
  // The closest state the change pushed toward losing, and how close.
  const was = new Map([...base].map(([code, b]) => [code, gap(b) * 100] as const));
  const squeezed = (k: Bucket) =>
    states
      .filter((f) => !f.flipped && f.won === k && f.margin < (was.get(f.code) ?? 0) - 0.05)
      .sort((a, b) => a.margin - b.margin)[0];
  const heldA = squeezed('A');
  const holds = heldA ? `${stateName(heldA.code)} holds for ${nameOf('A')} by ${pts(heldA.margin)}.` : '';
  let outcome: string;
  if (!chosen.length && !edited) {
    outcome = unknown ? '' : `Rerun with nothing changed, ${year} comes out as it did: ${nameOf('A')} wins, ${score('A')}.`;
  } else if (winner && winner !== 'A') {
    outcome = `That’s enough: ${nameOf(winner)} wins, ${score(winner)}${lost.length ? `, flipping ${names(lost, 4)}` : ''}.`;
  } else if (!winner) {
    outcome = `${lost.length ? `${flipOf(lost)}, and` : 'Now'} no one has a majority of electoral votes: the House would decide.`;
  } else if (lost.length) {
    outcome = `${flipOf(lost)}, but it isn’t enough: ${nameOf('A')} still wins, ${score('A')}. ${holds}`;
  } else if (gained.length) {
    outcome = `${nameOf('A')} wins bigger, ${score('A')}, taking ${names(gained, 4)}.`;
  } else if (evs.size) {
    outcome = `${nameOf('A')} still wins, ${score('A')}.`;
  } else if (heldA) {
    outcome = `It isn’t enough to flip a state. ${holds}`;
  } else {
    const heldB = e.candidates[1] ? squeezed('B') : undefined;
    outcome = heldB
      ? `No state changes hands; ${stateName(heldB.code)} stays with ${nameOf('B')} by ${pts(heldB.margin)}.`
      : 'No state changes hands.';
  }
  const kinds = chosen.map((w) => RANK[w.kind]);
  return {
    ev,
    winner,
    states: states.map(({ code, won, flipped, margin }) => ({ code, won, flipped, margin: Math.round(margin * 10) / 10 })),
    slices: [...slices.values()].map(display),
    summary: [...leads, outcome].filter(Boolean).join(' '),
    confidence: kinds.length ? (CONFIDENCE[Math.max(...kinds)] ?? 'low') : null,
    applied: chosen.map(({ key, label, kind }) => ({ key, label, kind })),
    unknown,
  };
}

const display = (s: ModelSlice): Slice => ({
  key: s.key,
  label: s.label,
  adults: Math.round(s.adults * 100) / 100,
  barred: round3(s.barred),
  home: round3(Math.max(0, s.home)),
  A: round3(s.A),
  B: round3(s.B),
  O: round3(s.O),
});

// ── The people ──
/** What most of a group did. */
function most(c: Fractions): Choice {
  if (c.barred >= 0.5) return 'barred';
  if (c.home > c.A + c.B + c.O) return 'home';
  return leaderOf(c);
}

function voterOf(e: Election, key: string, result: RunResult | null): Voter | null {
  const s = slicesFor(e).find((x) => x.key === key);
  if (!s) return null;
  const after = result?.slices.find((x) => x.key === key);
  const changed = !!after && FIELDS.some((k) => Math.abs(after[k] - round3(s[k])) > 0.002);
  if (s.voter) {
    const [name, line, history, then, quote] = s.voter;
    return { name, line, quote, history, now: changed ? then : history };
  }
  const pool = ERA_PEOPLE[key] ?? [];
  const [name, line, quote] = pool[Math.floor(unit(`${e.year}:${key}`) * pool.length)] ?? ['A voter', '', ''];
  const history = most(s);
  const then = after ? most(after) : history;
  return { name, line, quote, history, now: changed ? then : history };
}

// ── The API (api.ts's shape) ──
export interface SampleOptions {
  /** Waits a while, as a server would; tests pass one that doesn't. */
  readonly sleep?: (ms: number) => Promise<void>;
  /** The clock a run's progress is measured on. */
  readonly now?: () => number;
}

const ok = <T>(value: T): Outcome<T> => ({ kind: 'ok', value });
const missing = (message: string): Outcome<never> => ({ kind: 'error', reason: 'missing', message, status: 404 });
/** A sample run counts one state every RUN_MS, so it takes a moment, like a server's. */
const RUN_MS = 45;

export function createSampleApi(options: SampleOptions = {}): SimulacraApi {
  const sleep = options.sleep ?? ((ms: number) => new Promise<void>((r) => setTimeout(r, ms)));
  const clock = options.now ?? Date.now;
  const runs = new Map<string, { at: number; total: number; result: RunResult }>();
  let n = 0;
  return {
    sample: true,
    async election(year) {
      await sleep(220);
      const e = electionOf(year);
      if (!e) return ok({ slices: [], whatIfs: [], simulated: false });
      return ok({
        slices: slicesFor(e).map(display),
        whatIfs: whatIfsFor(e).map(({ key, label, kind, detail, slices }) => ({ key, label, kind, detail, slices: [...slices] })),
        simulated: true,
      });
    },
    async startRun(year, { whatIfs = [], text = '', edits = {} }: RunAsk = {}) {
      await sleep(120);
      const e = electionOf(year);
      if (!e) return missing('No simulation for this year.');
      n += 1;
      const id = `sample-${n}`;
      runs.set(id, { at: clock(), total: e.states.length, result: rerunElection(e, whatIfs, text, edits) });
      return ok({ id });
    },
    async run(id) {
      await sleep(40);
      const r = runs.get(id);
      if (!r) return ok({ status: 'failed', error: 'That run was stopped.' });
      const done = Math.min(r.total, Math.floor((clock() - r.at) / RUN_MS));
      if (done < r.total) return ok({ status: 'running', done, total: r.total });
      return ok({ status: 'done', done: r.total, total: r.total, result: r.result });
    },
    async stopRun(id) {
      runs.delete(id);
      return ok(null);
    },
    async voter(year, sliceKey, runId) {
      await sleep(140);
      const e = electionOf(year);
      const result = runId ? (runs.get(runId)?.result ?? null) : null;
      const v = e ? voterOf(e, sliceKey, result) : null;
      return v ? ok(v) : missing('No one from that group.');
    },
  };
}

/** The model, for checking it outside the page (scripts/model-check.ts, the tests). */
export const _model = {
  national: (year: number): Votes | null => {
    const e = electionOf(year);
    return e ? national(e) : null;
  },
  rerun: (year: number, keys: readonly string[] = [], text = '', edits: Edits = {}): RunResult | null => {
    const e = electionOf(year);
    return e ? rerunElection(e, keys, text, edits) : null;
  },
  slicesFor: (year: number): Slice[] => {
    const e = electionOf(year);
    return e ? slicesFor(e).map(display) : [];
  },
  whatIfsFor: (year: number): ModelWhatIf[] => {
    const e = electionOf(year);
    return e ? whatIfsFor(e) : [];
  },
};
