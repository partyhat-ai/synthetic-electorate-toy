// The groups and what-ifs every election has in the sample, by era, for the
// years with no written story (stories.ts) — above all, who couldn't vote.
import type { Election } from './history';
import type { Family } from './palette';
import { lerp, TURNOUT } from './sampleData';
import type { Lean, Region, SliceSpec, Votes, WhatIfSpec } from './sampleTypes';

const clamp = (x: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, x));

/** The first value whose test holds, else `otherwise`. */
const firstOf = (cases: readonly (readonly [boolean, number])[], otherwise: number): number =>
  cases.find(([holds]) => holds)?.[1] ?? otherwise;

/** The era's groups for election `e`, whose national split is `nat`. */
export function eraSlices(e: Election, nat: Votes): SliceSpec[] {
  const y = e.year;
  const fam = (k: string) => e.candidates.find((c) => c.key === k)?.family;
  // How a group leaning `pts` points toward `family` splits [A, B, O].
  const lean = (family: Family | null, pts = 0, o = nat.O): Lean => {
    let two = nat.A / Math.max(0.01, nat.A + nat.B);
    if (family && fam('A') === family) two += pts / 100;
    else if (family && fam('B') === family) two -= pts / 100;
    two = clamp(two, 0.03, 0.97);
    return [two * (1 - o), (1 - two) * (1 - o), o];
  };
  const T = lerp(TURNOUT, y);
  const s: SliceSpec[] = [];
  const add = (
    key: string,
    label: string,
    share: number,
    barred: number,
    turnout: number,
    l: Lean,
    where: Region,
    extra: { mirror?: boolean; tilt?: number } = {},
  ) => s.push({ key, label, share, barred, turnout, lean: barred >= 1 ? [0, 0, 0] : l, leanIf: l, where, ...extra });
  if (y <= 1824) {
    add('property-men', 'Men who own property', 0.28, 0, T, lean(null), 'all');
    add('no-property', 'Men without property', 0.14, lerp([[1789, 0.6], [1800, 0.5], [1812, 0.4], [1824, 0.25]], y), T, lean('democratic-republican', 12), 'all');
    // Freed, they'd have voted against the planters' party (in 1824, against Jackson).
    add('enslaved', 'Enslaved people', 0.16, 1, 0.6, y === 1824 ? [0.75, 0.05, 0.2] : lean('federalist', 10, 0), 'black');
    add('women', 'Women', 0.47, y >= 1792 && y <= 1804 ? 0.995 : 1, 0.4, lean(null), 'all', { mirror: true });
  } else if (y <= 1860) {
    add('north-men', 'Northern white men', 0.27, 0.04, T, y >= 1856 ? lean('republican', 12) : lean('whig', 3), 'north');
    add('south-men', 'White Southern men', 0.12, 0.03, T * 0.95, lean('democratic', y >= 1856 ? 30 : 6), 'south');
    if (y >= 1844) add('immigrants', 'Irish and German immigrants', 0.05, 0.45, 0.75, lean('democratic', 20), 'immigrant');
    add('enslaved', 'Enslaved people', 0.14, 1, 0.7, y >= 1856 ? lean('republican', 40, 0) : lean('whig', 15, 0), 'black');
    add('women', 'Women', 0.48, 1, 0.5, lean(null), 'all', { mirror: true });
  } else if (y <= 1876) {
    add('north-men', 'Northern white men', 0.29, 0.04, T, lean('republican', 6), 'north');
    if (y === 1864) add('enslaved', 'Black Americans', 0.1, 1, 0.8, lean('republican', 40, 0), 'black');
    else {
      add('south-men', 'White Southern men', 0.1, 0.02, T * 0.95, lean('democratic', 35), 'south');
      add('freedmen', 'Black men in the South', 0.045, lerp([[1868, 0.2], [1872, 0.25], [1876, 0.45]], y), 0.85, lean('republican', 40, 0), 'black-south');
    }
    add('immigrants', 'Immigrants', 0.05, 0.45, 0.75, lean('democratic', 20), 'immigrant');
    add('women', 'Women', 0.48, 1, 0.5, lean(null), 'all', { mirror: true });
  } else if (y <= 1916) {
    add('north-men', 'Northern men', 0.3, 0.06, T, lean('republican', 4), 'north');
    add('south-white', 'White Southern men', 0.1, y >= 1900 ? 0.2 : 0.05, y >= 1900 ? 0.45 : 0.6, lean('democratic', 38), 'south');
    add('black-south', 'Black men in the South', 0.04, lerp([[1880, 0.35], [1892, 0.5], [1896, 0.6], [1900, 0.75], [1904, 0.88], [1916, 0.94]], y), 0.6,
      lean('republican', 40, 0), 'black-south');
    add('women', 'Women', 0.48, lerp([[1888, 1], [1892, 0.999], [1896, 0.985], [1908, 0.985], [1912, 0.92], [1916, 0.88]], y), 0.5, lean(null), 'all', { mirror: true });
    add('immigrants', 'Immigrants not yet citizens', 0.06, 0.85, 0.6, lean('democratic', 12), 'immigrant');
  } else if (y <= 1968) {
    add('north', 'Northerners', 0.5, 0.03, Math.min(0.8, T + 0.05), lean('republican', y <= 1928 ? 3 : 0), 'north');
    const southBarred = firstOf([[y >= 1964, 0.03], [y >= 1948, 0.15]], 0.25);
    const southDemPts = firstOf([[y >= 1952, 8], [y === 1928, 15]], 35);
    const southLean = y === 1964 ? lean('republican', 15) : lean('democratic', southDemPts);
    add('south-white', 'White Southerners', 0.18, southBarred, y >= 1948 ? 0.45 : 0.3, southLean, 'south');
    const blackDemPts = y >= 1964 ? 45 : 20;
    const blackSouthLean = y <= 1932 ? lean('republican', 25, 0) : lean('democratic', blackDemPts, 0);
    add('black-south', 'Black Southerners', 0.05, lerp([[1944, 0.95], [1948, 0.88], [1952, 0.8], [1960, 0.7], [1964, 0.45], [1968, 0.3]], y), 0.6,
      blackSouthLean, 'black-south');
    const blackNorthLean = y <= 1932 ? lean('republican', 20, 0) : lean('democratic', blackDemPts, 0);
    add('black-north', 'Black Northerners', lerp([[1920, 0.02], [1960, 0.045]], y), 0.05, 0.6, blackNorthLean, 'black-north');
    if (y === 1920) add('women', 'Women', 0.48, 0.08, 0.35, lean('republican', 3), 'all', { mirror: true, tilt: 0.03 });
    else add('youth', '18- to 20-year-olds', 0.075, firstOf([[y >= 1956, 0.95], [y >= 1944, 0.97]], 1), 0.5, lean(null), 'all');
  } else {
    add('white', 'White voters', lerp([[1972, 0.8], [2024, 0.6]], y), 0.02, T + 0.04, lean('republican', 10), 'all');
    add('black', 'Black voters', 0.12, 0.08, T - 0.02, lean('democratic', 40, 0.02), 'black');
    if (y >= 1980) add('latino', 'Latino voters', lerp([[1980, 0.04], [2024, 0.15]], y), 0.4, 0.45, lean('democratic', 15), 'latino');
    add('young', 'Voters under 30', 0.22, 0.05, T - 0.15, lean('democratic', 6), 'all');
    if (y >= 1976) add('felony', 'People with felony records', lerp([[1976, 0.01], [2016, 0.025], [2024, 0.021]], y), 0.75, 0.3, lean('democratic', 20, 0), 'felony');
  }
  return s;
}

/** An era what-if: a WhatIfSpec, and the years it fits. */
type EraWhatIf = readonly [...WhatIfSpec, when: (y: number) => boolean];

const ERA_WHAT_IFS: readonly EraWhatIf[] = [
  ['women', 'Women Vote', 'franchise', 'Every woman can vote on the same terms as the men of her state.', ['women'],
    (c) => c.enfranchise('women', { barred: c.year < 1868 ? 0.14 : 0.08 }), (y) => y < 1920],
  ['no-19th', 'The 19th Amendment Fails', 'franchise', 'Women can vote only in the fifteen states that already let them.', ['women'],
    (c) => c.enfranchise('women', { barred: 0.7 }), (y) => y === 1920],
  ['fifteenth', 'Enforce the 15th Amendment', 'franchise', 'Black Southerners vote as freely as white Southerners: no literacy tests, poll taxes or terror.', ['black-south', 'freedmen'],
    (c) => c.enfranchise(c.has('freedmen') ? 'freedmen' : 'black-south', { barred: 0.05 }), (y) => y >= 1868 && y <= 1964],
  ['emancipation', 'Emancipation and the Vote', 'franchise', 'Slavery ends before the election, and freed men vote like other men in their states.', ['enslaved'],
    (c) => c.enfranchise('enslaved', { barred: 0.5 }), (y) => y >= 1796 && y <= 1860],
  ['three-fifths', 'No Three-Fifths Bonus', 'franchise', 'Slave states lose the electors they got for counting enslaved people as three-fifths of a person.', ['enslaved'],
    (c) => c.apportion(), (y) => y >= 1796 && y <= 1860],
  ['no-property', 'No Property Test', 'franchise', 'Every free man can vote, whether or not he owns land.', ['no-property'],
    (c) => c.enfranchise('no-property', { barred: 0 }), (y) => y <= 1824],
  ['age18', 'Vote at 18', 'franchise', 'Eighteen-year-olds can vote everywhere, as they could after 1971.', ['youth'],
    (c) => c.enfranchise('youth', { barred: 0 }), (y) => y >= 1924 && y <= 1968 && y !== 1920],
  ['felons', 'Felony Records Don’t Bar Voting', 'franchise', 'Everyone who has served a sentence can vote, as in Maine and Vermont.', ['felony'],
    (c) => c.enfranchise('felony', { barred: 0 }), (y) => y >= 1976],
  ['migration', 'No Great Migration', 'population', 'The Black Southerners who moved north after 1910 stay in the South, where most can’t vote.', ['black-north', 'black-south'],
    (c) => c.move('black-north', 0.7, 'black-south'), (y) => y >= 1928 && y <= 1968],
  ['everyone', 'Everyone Votes', 'franchise', 'Every adult can vote, and turns out.', [],
    (c) => c.everyone(), () => true],
];

/** The era's what-ifs that fit year y: up to three, then Everyone Votes. */
export function eraWhatIfs(y: number): WhatIfSpec[] {
  const fits = ERA_WHAT_IFS.filter((w) => w[6](y));
  return [...fits.filter((w) => w[0] !== 'everyone').slice(0, 3), ...fits.filter((w) => w[0] === 'everyone')].map(
    ([key, label, kind, detail, slices, apply]) => [key, label, kind, detail, slices, apply] as const,
  );
}
