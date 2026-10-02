// The election header's derived text and colours: who gets which paint, the
// names the dots and map use, the "Also ran" line and the map's label.
import type { Candidate, Election } from './history';
import { candidateHues, onPaint, paint } from './palette';
import type { Colors, MapState, Names } from './types';

export interface Paints {
  readonly colors: Colors;
  /** The check's colour on the winner's and runner-up's rings. */
  readonly inks: Readonly<Record<'A' | 'B', string>>;
}

/** The winner's and runner-up's party colours and everyone else's grey, for the mode. */
export function paintsOf(election: Election, light: boolean): Paints {
  const hues = candidateHues(
    election.candidates.map((c) => ({ key: c.key, party: c.family })),
    Object.fromEntries(election.candidates.map((c) => [c.key, c.ev])),
  );
  const a = hues.get('A');
  const b = hues.get('B') ?? 'other';
  return {
    colors: { A: paint(a, light), B: paint(b, light), O: paint('other', light) },
    inks: { A: onPaint(a, light), B: onPaint(b, light) },
  };
}

export function namesOf(election: Election): Names {
  const [a, b, ...others] = election.candidates;
  const only = others.length === 1 ? others[0] : undefined;
  return { A: a.short, B: b?.short, O: only ? only.short : 'Others' };
}

/** Everyone else who won electoral votes or a real share of the vote. */
export function alsoRanOf(others: readonly Candidate[]): string {
  const won = others.filter((c) => c.ev > 0).map((c) => `${c.name} ${c.ev}`);
  const polled = others.filter((c) => !(c.ev > 0) && (c.popular ?? 0) >= 5).map((c) => `${c.name} ${c.popular}% of the vote`);
  const one = won.length === 1 && others.find((c) => c.ev > 0)?.ev === 1;
  return [won.length ? `${won.join(', ')} electoral vote${one ? '' : 's'}` : '', polled.join(', ')].filter(Boolean).join(' · ');
}

/** The map's spoken label: how many states each candidate carried, and how many flipped. */
export function mapLabelOf(year: number, rerun: boolean, election: Election, states: readonly MapState[], flips: number): string {
  const carried = (c: Candidate) =>
    states.filter((s) => (c.key === 'A' || c.key === 'B' ? s.won === c.key : s.won !== 'A' && s.won !== 'B' && s.won === c.key))
      .length;
  return (
    `Map of ${rerun ? `your ${year}` : year}: ` +
    election.candidates.map((c) => `${c.short} carried ${carried(c)} states`).join(', ') +
    (flips ? `; ${flips} flipped` : '')
  );
}
