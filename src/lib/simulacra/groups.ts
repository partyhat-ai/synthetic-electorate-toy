// The five voter groups every simulated year is built from, in the order the
// page shows them, and why a year can be missing one. Thirteen years
// (1789-1836) have no immigrant group; 1864 has no Southern ones. On a narrow
// window the page holds a missing group's place with an AbsentRow, so every
// year shows five rows and nothing under them moves with the year.
import type { Slice } from './schemas';

export const GROUP_ORDER = ['men', 'women', 'south-white', 'black-south', 'immigrants'] as const;
/** Each group is drawn as this many people, a row of dots (SliceRow; AbsentRow's rule spans as many). */
export const DOTS = 50;
const IN_ORDER: ReadonlySet<string> = new Set(GROUP_ORDER);

export interface Absent {
  readonly key: string;
  readonly label: string;
  readonly why: string;
}

// One line each, so a held row is as tall as a group's.
const CONFEDERACY = 'Didn’t vote: the Confederacy had seceded.';

const ABSENT: Readonly<Record<string, Omit<Absent, 'key'>>> = {
  immigrants: { label: 'Immigrants not yet citizens', why: 'Not counted in the census data before 1840.' },
  'south-white': { label: 'White Southerners', why: CONFEDERACY },
  'black-south': { label: 'Black Southerners, most of them enslaved', why: CONFEDERACY },
};

/** The year's groups in GROUP_ORDER, each missing one replaced by its Absent (any group outside the order kept, last). */
export function withAbsent(slices: readonly Slice[]): (Slice | Absent)[] {
  const byKey = new Map(slices.map((s) => [s.key, s]));
  const rows: (Slice | Absent)[] = [];
  for (const key of GROUP_ORDER) {
    const s = byKey.get(key);
    if (s) rows.push(s);
    else if (ABSENT[key]) rows.push({ key, ...ABSENT[key] });
  }
  for (const s of slices) if (!IN_ORDER.has(s.key)) rows.push(s);
  return rows;
}

export const isAbsent = (row: Slice | Absent): row is Absent => 'why' in row;
