// ?sample=1: a first sample model, so the prototypes have something to draw
// before any simulation exists. Every election here is invented — the era's
// two parties, each state's "actual" winner, its electoral votes — and the
// model's call sits beside it, a few points off, so close states can miss.
// Nothing here is a result.
import { ELECTION_YEARS, votingStatesIn } from './geo';

/** Votes or shares for the winner (A), the runner-up (B) and everyone else (O). */
export interface Votes {
  A: number;
  B: number;
  O: number;
}

/** Where a vote lands: the winner (A), the runner-up (B), or everyone else (O). */
type Bucket = 'A' | 'B' | 'O';
const bucketOf = (key: string): Bucket => {
  if (key === 'A' || key === 'B') return key;
  return 'O';
};

/** A stable number in [0, 1) for a string. */
const unit = (s: string) => {
  let h = 2166136261;
  for (const ch of s) h = Math.imul(h ^ ch.charCodeAt(0), 16777619) >>> 0;
  return (h % 10007) / 10007;
};

/** Who leads: A on a tie with anyone, then B over O. */
function leaderOf(v: Votes): Bucket {
  if (v.A >= v.B && v.A >= v.O) return 'A';
  return v.B >= v.O ? 'B' : 'O';
}

/** One candidate: A the winner, B the runner-up. */
export interface SampleCandidate {
  readonly key: 'A' | 'B';
  /** The era's party code. */
  readonly party: string;
  readonly ev: number;
  /** Share of the popular vote, %, or null before there was one. */
  readonly popular: number | null;
}

/** One invented election: two candidates and who carried each state. */
export interface SampleElection {
  readonly year: number;
  readonly candidates: readonly [SampleCandidate, ...SampleCandidate[]];
  readonly states: readonly { readonly code: string; readonly ev: number; readonly party: string; readonly won: string }[];
}

// Each era's two main parties, newest first.
const ERAS: readonly (readonly [from: number, a: string, b: string])[] = [
  [1856, 'R', 'D'],
  [1836, 'D', 'W'],
  [1828, 'D', 'NR'],
  [1789, 'DR', 'F'],
];

const invented = new Map<number, SampleElection>();

/** The election for `year`, invented once (null for a year with none). */
function sampleElection(year: number): SampleElection | null {
  if (!ELECTION_YEARS.includes(year)) return null;
  const hit = invented.get(year);
  if (hit) return hit;
  const [, pa = 'DR', pb = 'F'] = ERAS.find(([from]) => year >= from) ?? [];
  // The year's tilt toward the first party, and each state's draw against it.
  const tilt = unit(`tilt:${year}`) - 0.5;
  const drawn = votingStatesIn(year).map((s) => {
    const first = unit(`won:${year}:${s.code}`) < 0.5 + tilt * 0.6;
    return { code: s.code, ev: 3 + Math.floor(unit(`ev:${year}:${s.code}`) * 17), party: first ? pa : pb };
  });
  const evOf = (p: string) => drawn.filter((s) => s.party === p).reduce((a, s) => a + s.ev, 0);
  // A is whoever carried more electoral votes.
  const [wp, lp] = evOf(pa) >= evOf(pb) ? [pa, pb] : [pb, pa];
  const share = year < 1828 ? null : Math.round((50 + Math.abs(tilt) * 16) * 10) / 10;
  const e: SampleElection = {
    year,
    candidates: [
      { key: 'A', party: wp, ev: evOf(wp), popular: share },
      { key: 'B', party: lp, ev: evOf(lp), popular: share === null ? null : Math.round((96 - share) * 10) / 10 },
    ],
    states: drawn.map((s) => ({ ...s, won: s.party === wp ? 'A' : 'B' })),
  };
  invented.set(year, e);
  return e;
}

/** The country's split: the popular vote when there is one, else one guessed from the electoral vote. */
function national(e: SampleElection): Votes {
  const [a, b] = e.candidates;
  if (!b) throw new Error(`${e.year} has no runner-up.`);
  if (a.popular != null && b.popular != null) {
    const A = a.popular / 100;
    const B = b.popular / 100;
    return { A, B, O: Math.max(0, 1 - A - B) };
  }
  const A = 0.5 + (0.25 * (a.ev - b.ev)) / Math.max(1, a.ev + b.ev);
  return { A, B: 0.98 - A, O: 0.02 };
}

/** A state as modelled: shares, electors, who carried it. */
interface Base extends Votes {
  readonly ev: number;
  readonly won: string;
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

// Each state's vote share by candidate. The winner is the election's; how
// close it was is modelled — a state that stayed with the same party in the
// elections around this one was safe, one that swung was close.
function baseline(e: SampleElection): Map<string, Base> {
  const nat = national(e);
  const i = ELECTION_YEARS.indexOf(e.year);
  const near = [-2, -1, 1, 2].flatMap((d) => {
    const y = ELECTION_YEARS[i + d];
    const n = y === undefined ? null : sampleElection(y);
    return n ? [n] : [];
  });
  const out = new Map<string, Base>();
  for (const s of e.states) {
    const h = unit(`${e.year}:${s.code}`);
    const same = near.filter((n) => n.states.find((x) => x.code === s.code)?.party === s.party).length;
    const stable = near.length ? same / near.length : 0.5;
    const lead = ((2 + stable * stable * 24) * (0.7 + 0.6 * h) + Math.abs(nat.A - nat.B) * 35) / 100;
    out.set(s.code, { ...split(bucketOf(s.won), lead, nat, h), ev: s.ev, won: s.won });
  }
  return out;
}

/** The gap between the first and second of three shares. */
const gap = (v: Votes) => {
  const [x = 0, y = 0] = [v.A, v.B, v.O].sort((p, q) => q - p);
  return x - y;
};

/** The model's call: each state's winner and margin (points), whether it missed, and the electoral votes. */
export interface SimResult {
  readonly ev: Votes;
  /** null: no one has a majority. */
  readonly winner: Bucket | null;
  readonly states: readonly { readonly code: string; readonly won: string; readonly flipped: boolean; readonly margin: number }[];
}

function predict(e: SampleElection): SimResult {
  const ev: Votes = { A: 0, B: 0, O: 0 };
  const states = [...baseline(e)].map(([code, b]) => {
    // The model's error: a few points either way, so the close states can miss.
    const err = (unit(`err:${e.year}:${code}`) - 0.5) * 0.12;
    const call = { A: b.A + err, B: b.B - err, O: b.O };
    const won = leaderOf(call);
    ev[won] += b.ev;
    return { code, won, flipped: won !== bucketOf(b.won), margin: Math.round((gap(call) / (call.A + call.B + call.O || 1)) * 1000) / 10 };
  });
  const total = ev.A + ev.B + ev.O;
  const best = leaderOf(ev);
  return { ev, winner: ev[best] > total / 2 ? best : null, states };
}

/** The sample as the prototypes read it: each election, and the model's call on it. */
export const sample = {
  election: (year: number): SampleElection | null => sampleElection(year),
  call: (year: number): SimResult | null => {
    const e = sampleElection(year);
    return e ? predict(e) : null;
  },
};
