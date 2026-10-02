// The sample model: a small deterministic stand-in for the simulation, so
// the page can be built and reviewed before any simulation server exists.
// It starts from the elections as they happened (history.ts): each state
// goes to its real winner, by a modelled margin — a state that stayed with
// the same party in the elections around this one was safe, one that swung
// was close. Plausible, never authoritative.
import { ELECTION_YEARS } from './geo';
import { type Election, electionOf } from './history';

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

/** A state as modelled: shares, electors, who carried it. */
interface Base extends Votes {
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
// it was is modelled.
function baseline(e: Election): Map<string, Base> {
  const nat = national(e);
  const i = ELECTION_YEARS.indexOf(e.year);
  const near = [-2, -1, 1, 2].flatMap((d) => {
    const y = ELECTION_YEARS[i + d];
    const n = y === undefined ? null : electionOf(y);
    return n ? [n] : [];
  });
  const out = new Map<string, Base>();
  for (const s of e.states) {
    const h = unit(`${e.year}:${s.code}`);
    const same = near.filter((n) => n.states.find((x) => x.code === s.code)?.party === s.party).length;
    const stable = near.length ? same / near.length : 0.5;
    const lead = ((2 + stable * stable * 24) * (0.7 + 0.6 * h) + Math.abs(nat.A - nat.B) * 35) / 100;
    const sh = split(bucketOf(s.won), lead, nat, h);
    out.set(s.code, { ...sh, ev: s.ev, won: s.won, split: s.party === 'SP' });
  }
  return out;
}

/** The gap between the first and second of three shares. */
const gap = (v: Votes) => {
  const [x = 0, y = 0] = [v.A, v.B, v.O].sort((p, q) => q - p);
  return x - y;
};

/** A rerun: each state's winner and margin (points), the electoral votes, and who won them. */
export interface SimResult {
  readonly ev: Votes;
  /** null: no one has a majority. */
  readonly winner: Bucket | null;
  readonly states: readonly { readonly code: string; readonly won: string; readonly flipped: boolean; readonly margin: number }[];
}

/** An election rerun with nothing changed. */
function rerunElection(e: Election): SimResult {
  const base = baseline(e);
  const ev: Votes = {
    A: e.candidates[0].ev,
    B: e.candidates[1]?.ev ?? 0,
    O: e.candidates.slice(2).reduce((a, c) => a + c.ev, 0),
  };
  const states = [...base].map(([code, b]) => {
    // A state history split between candidates stays split.
    const flipped = !b.split && leaderOf(b) !== bucketOf(b.won);
    return { code, won: b.won, flipped, margin: Math.round((gap(b) / (b.A + b.B + b.O || 1)) * 1000) / 10 };
  });
  return { ev, winner: 'A', states };
}

/** The model, for checking it outside the page (the tests). */
export const _model = {
  national: (year: number): Votes | null => {
    const e = electionOf(year);
    return e ? national(e) : null;
  },
  rerun: (year: number): SimResult | null => {
    const e = electionOf(year);
    return e ? rerunElection(e) : null;
  },
};
