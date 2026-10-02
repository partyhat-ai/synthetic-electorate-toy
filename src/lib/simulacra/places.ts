// Places named in the page's words — a state, a region, the colonies — found
// by quick pattern matching, so pointing at the word can light its tiles on
// the map (MiniMap's `highlight`). Regions are the harness's own
// (simharness/geo.py), so "midwest" means the voters' midwest.
import { writable } from 'svelte/store';
import { STATES } from './geo';

const SOUTH = ['VA', 'NC', 'SC', 'GA', 'FL', 'AL', 'MS', 'LA', 'TX', 'AR', 'TN'];
const BORDER = ['KY', 'MD', 'DE', 'MO', 'WV', 'OK'];
const NORTHEAST = ['ME', 'NH', 'VT', 'MA', 'RI', 'CT', 'NY', 'NJ', 'PA'];
const NEW_ENGLAND = ['ME', 'NH', 'VT', 'MA', 'RI', 'CT'];
const MIDWEST = ['OH', 'IN', 'IL', 'MI', 'WI', 'MN', 'IA', 'ND', 'SD', 'NE', 'KS'];
const WEST = ['MT', 'ID', 'WY', 'CO', 'NM', 'AZ', 'UT', 'NV', 'WA', 'OR', 'CA'];
const COLONIES = ['NH', 'MA', 'RI', 'CT', 'NY', 'NJ', 'PA', 'DE', 'MD', 'VA', 'NC', 'SC', 'GA'];

// "George Washington" is a man, not a state.
const statePattern = (code: string, name: string): string =>
  code === 'WA' ? '(?<!George )Washington(?! D\\.C\\.)' : name.replace(/ /g, '\\s');

// [pattern, codes]. Order matters where one name contains another: the
// regex tries these left to right at each position, so longer names come first.
const RULES: readonly (readonly [string, readonly string[]])[] = [
  ['District of Columbia|Washington,? D\\.C\\.', ['DC']],
  ...STATES.filter((s) => s.code !== 'DC')
    .sort((a, b) => b.name.length - a.name.length)
    .map((s) => [statePattern(s.code, s.name), [s.code]] as const),
  ['(?:the\\s)?(?:thirteen|13|original)\\s(?:colonies|states)', COLONIES],
  ['New\\sEngland(?:ers?)?', NEW_ENGLAND],
  // Lowercase "south" only as a region ("the south", a group's ", south"), not "went south".
  ['(?:Deep\\s)?South(?:erners?|ern)?|(?<=(?:the|,)\\s)south(?:ern)?|[Dd]ixie', SOUTH],
  ['[Mm]id-?[Ww]est(?:erners?|ern)?|Middle\\sWest', MIDWEST],
  ['[Nn]orth-?[Ee]ast(?:erners?|ern)?', NORTHEAST],
  ['[Bb]order\\sstates?', BORDER],
  ['(?:the\\s|Far\\s)West|Westerners?', WEST],
];
const RE = new RegExp(`\\b(?:${RULES.map(([p], i) => `(?<r${i}>${p})`).join('|')})\\b`, 'g');

/** A run of text: plain, or a place with the state codes it names. */
export interface Segment {
  readonly t: string;
  readonly codes?: readonly string[];
}

/** text → plain runs, and the places in it with their state codes. */
export function segments(text = ''): Segment[] {
  const out: Segment[] = [];
  let at = 0;
  for (const m of text.matchAll(RE)) {
    const groups = m.groups ?? {};
    const i = Object.keys(groups).findIndex((k) => groups[k] !== undefined);
    if (m.index > at) out.push({ t: text.slice(at, m.index) });
    out.push({ t: m[0], codes: RULES[i]?.[1] ?? [] });
    at = m.index + m[0].length;
  }
  if (at < text.length) out.push({ t: text.slice(at) });
  return out;
}

/** The codes of the place under the pointer, for the map to light. */
export const hoverPlaces = writable<readonly string[]>([]);
