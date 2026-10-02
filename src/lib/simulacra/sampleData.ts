// The sample model's numbers (sample.ts): the country, roughly, by year;
// where groups live; and the people it quotes for years with no written
// story. Rough on purpose: the sample is labelled, and only shows how a
// rerun works.
import type { Region } from './sampleTypes';

/** [[x, y], …], x ascending, for lerp(). */
export type Table = readonly (readonly [number, number])[];

/** Piecewise-linear lookup in a table, flat past either end. */
export function lerp(table: Table, x: number): number {
  let prev: readonly [number, number] | undefined;
  for (const pt of table) {
    if (x <= pt[0]) {
      if (!prev) return pt[1];
      return prev[1] + ((pt[1] - prev[1]) * (x - prev[0])) / (pt[0] - prev[0]);
    }
    prev = pt;
  }
  return prev ? prev[1] : 0;
}

// ── The country, roughly ──
// Population, millions.
const POPULATION: Table = [[1790, 3.9], [1800, 5.3], [1810, 7.2], [1820, 9.6], [1830, 12.9], [1840, 17.1], [1850, 23.2], [1860, 31.4], [1870, 38.6], [1880, 50.2], [1890, 63], [1900, 76.2], [1910, 92.2], [1920, 106], [1930, 123.2], [1940, 132.2], [1950, 151.3], [1960, 179.3], [1970, 203.2], [1980, 226.5], [1990, 248.7], [2000, 281.4], [2010, 308.7], [2020, 331.4], [2024, 340]];
// Adults' share of it: 21 and over until the 26th Amendment, then 18.
const ADULT: Table = [[1790, 0.43], [1850, 0.47], [1880, 0.5], [1900, 0.53], [1920, 0.58], [1940, 0.64], [1950, 0.64], [1960, 0.61], [1968, 0.61], [1972, 0.7], [1980, 0.72], [1990, 0.74], [2010, 0.76], [2024, 0.78]];
/** Adults in year y, millions. */
export const adultsIn = (y: number): number => lerp(POPULATION, y) * lerp(ADULT, y);
// Popular votes cast, millions.
const VOTES: Readonly<Record<number, number>> = { 1789: 0.044, 1792: 0.028, 1796: 0.066, 1800: 0.068, 1804: 0.143, 1808: 0.193, 1812: 0.278, 1816: 0.113, 1820: 0.109, 1824: 0.366, 1828: 1.148, 1832: 1.293, 1836: 1.503, 1840: 2.412, 1844: 2.703, 1848: 2.879, 1852: 3.162, 1856: 4.054, 1860: 4.686, 1864: 4.031, 1868: 5.723, 1872: 6.467, 1876: 8.413, 1880: 9.217, 1884: 10.058, 1888: 11.383, 1892: 12.057, 1896: 13.936, 1900: 13.97, 1904: 13.518, 1908: 14.884, 1912: 15.044, 1916: 18.536, 1920: 26.768, 1924: 29.095, 1928: 36.805, 1932: 39.758, 1936: 45.655, 1940: 49.9, 1944: 47.977, 1948: 48.794, 1952: 61.552, 1956: 62.027, 1960: 68.838, 1964: 70.645, 1968: 73.212, 1972: 77.744, 1976: 81.556, 1980: 86.515, 1984: 92.653, 1988: 91.595, 1992: 104.425, 1996: 96.278, 2000: 105.426, 2004: 122.295, 2008: 131.473, 2012: 129.085, 2016: 136.669, 2020: 158.429, 2024: 155.238 };
// Before 1828 most states chose electors through their legislatures, so the
// popular vote above understates who took part: the model uses the men who
// voted for those legislatures.
const EARLY: Readonly<Record<number, number>> = { 1789: 0.25, 1792: 0.3, 1796: 0.35, 1800: 0.45, 1804: 0.5, 1808: 0.6, 1812: 0.7, 1816: 0.75, 1820: 0.8, 1824: 0.85 };
/** Votes cast in year y, millions. */
export const votesIn = (y: number): number => Math.max(VOTES[y] ?? 0, EARLY[y] ?? 0);
// Turnout of those who could vote.
export const TURNOUT: Table = [[1789, 0.2], [1824, 0.27], [1828, 0.57], [1840, 0.8], [1860, 0.81], [1876, 0.82], [1896, 0.79], [1900, 0.73], [1912, 0.59], [1920, 0.49], [1936, 0.61], [1960, 0.63], [1972, 0.55], [1996, 0.49], [2008, 0.58], [2020, 0.66], [2024, 0.64]];

// ── Where groups live ──
export const SOUTH: readonly string[] = ['VA', 'NC', 'SC', 'GA', 'FL', 'AL', 'MS', 'LA', 'TX', 'AR', 'TN'];
export const BORDER: readonly string[] = ['KY', 'MD', 'DE', 'MO', 'WV', 'OK'];
type Listed = Extract<Region, 'south' | 'new-england' | 'middle' | 'midwest' | 'plains' | 'industrial'>;
export const REGIONS: Readonly<Record<Listed, readonly string[]>> = {
  south: SOUTH,
  'new-england': ['ME', 'NH', 'VT', 'MA', 'RI', 'CT'],
  middle: ['NY', 'NJ', 'PA', 'DE', 'MD'],
  midwest: ['OH', 'IN', 'IL', 'MI', 'WI', 'MN', 'IA', 'MO', 'KS', 'NE', 'ND', 'SD'],
  plains: ['KS', 'NE', 'ND', 'SD', 'MN', 'IA', 'CO', 'MT', 'ID', 'WA', 'OK', 'WY', 'NV', 'UT'],
  industrial: ['NY', 'PA', 'NJ', 'MA', 'OH', 'IL', 'MI', 'CT', 'RI', 'IN', 'WI'],
};
type Spread = Extract<Region, 'immigrant' | 'latino' | 'felony'>;
export const SPREAD: Readonly<Record<Spread, Readonly<Record<string, number>>>> = {
  immigrant: { NY: 3, PA: 2, MA: 2, IL: 2, OH: 1.5, WI: 1.5, MO: 1, NJ: 1, MI: 1, MN: 1, CA: 1, LA: 0.5 },
  latino: { CA: 5, TX: 4, FL: 2, AZ: 2, NM: 2, NY: 1.5, NV: 1, CO: 1, IL: 1, NJ: 1 },
  felony: { FL: 6, TX: 2, VA: 1.5, TN: 1.2, AL: 1, KY: 1, GA: 1.2, MS: 0.8, AZ: 0.8, WA: 0.4 },
};
// Black share of each state's population (census), 1900, 1960 and 2000.
const BLACK = {
  1900: { MS: 0.58, SC: 0.58, LA: 0.47, GA: 0.47, AL: 0.45, FL: 0.44, VA: 0.36, NC: 0.33, AR: 0.28, TN: 0.24, TX: 0.2, MD: 0.2, DE: 0.17, KY: 0.13, DC: 0.31, MO: 0.05, WV: 0.05, OK: 0.07, KS: 0.035, OH: 0.023, PA: 0.025, NY: 0.014, NJ: 0.037, IL: 0.018, IN: 0.023 },
  1960: { MS: 0.42, SC: 0.35, LA: 0.32, GA: 0.28, AL: 0.3, FL: 0.18, VA: 0.21, NC: 0.25, AR: 0.22, TN: 0.16, TX: 0.12, MD: 0.17, DE: 0.14, KY: 0.07, DC: 0.54, MO: 0.09, WV: 0.05, OK: 0.07, KS: 0.04, OH: 0.08, PA: 0.075, NY: 0.084, NJ: 0.085, IL: 0.1, IN: 0.06, MI: 0.09, CA: 0.056, CT: 0.042, MA: 0.022, WI: 0.019 },
  2000: { MS: 0.36, SC: 0.29, LA: 0.32, GA: 0.29, AL: 0.26, FL: 0.15, VA: 0.2, NC: 0.22, AR: 0.16, TN: 0.16, TX: 0.12, MD: 0.28, DE: 0.19, KY: 0.07, DC: 0.6, MO: 0.11, OK: 0.08, OH: 0.12, PA: 0.1, NY: 0.16, NJ: 0.14, IL: 0.15, IN: 0.08, MI: 0.14, CA: 0.07, CT: 0.09, MA: 0.05, WI: 0.06, NV: 0.07, CO: 0.04, MN: 0.035 },
} as const satisfies Record<number, Readonly<Record<string, number>>>;
export function blackShare(code: string, y: number): number {
  const at = (t: keyof typeof BLACK): number => {
    const table: Readonly<Record<string, number>> = BLACK[t];
    return table[code] ?? 0.01;
  };
  if (y <= 1900) return at(1900);
  if (y <= 1960) return at(1900) + ((at(1960) - at(1900)) * (y - 1900)) / 60;
  return at(1960) + (at(2000) - at(1960)) * Math.min(1, (y - 1960) / 40);
}
// Share of each slave state's people held in slavery (1800 and 1860
// censuses), for the three-fifths what-if.
export const ENSLAVED: Readonly<Record<'early' | 'late', Readonly<Record<string, number>>>> = {
  early: { VA: 0.39, SC: 0.42, GA: 0.37, NC: 0.28, MD: 0.31, KY: 0.18, TN: 0.13, DE: 0.06, LA: 0.45, MS: 0.42, AL: 0.33, MO: 0.15 },
  late: { VA: 0.31, SC: 0.57, GA: 0.44, NC: 0.33, MD: 0.13, KY: 0.2, TN: 0.25, DE: 0.02, LA: 0.47, MS: 0.55, AL: 0.45, MO: 0.1, FL: 0.44, AR: 0.26, TX: 0.3 },
};
// Southern votes per electoral vote, against the North's: from the 1880s to
// the 1960s the South cast far fewer, most of its Black citizens and many
// poor whites kept from the polls — the Deep South fewest of all.
const DEEP_SOUTH: readonly string[] = ['SC', 'MS', 'LA', 'GA', 'AL', 'FL'];
export function southFactor(code: string, y: number): number {
  // Before emancipation a slave state's electors counted three-fifths of its
  // enslaved people, so it had fewer voters per elector.
  if (y <= 1864) {
    const share = (y <= 1830 ? ENSLAVED.early : ENSLAVED.late)[code] ?? 0;
    return (1 - share) / (1 - 0.4 * share);
  }
  if (!SOUTH.includes(code) || y < 1880 || y > 1964) return 1;
  const deep = DEEP_SOUTH.includes(code);
  if (y < 1890) return deep ? 0.6 : 0.8;
  if (y <= 1900) return deep ? 0.3 : 0.6;
  return deep ? 0.2 : 0.4;
}

// ── The people ──
// Era groups' people, for years with no written story: [name, who, quote].
export type EraPerson = readonly [name: string, line: string, quote: string];
export const ERA_PEOPLE: Readonly<Record<string, readonly EraPerson[]>> = {
  'property-men': [['Nathaniel Brooks', '45, farmer with ninety acres, Hampshire County, Massachusetts', 'I own my land free and clear. That gives me a stake in the country, and a vote to show for it.']],
  'no-property': [['Patrick Doyle', '27, dockworker, New York City', 'New York lets a man vote for the Assembly only if he pays enough rent. I pay less, so I have no say in who picks our electors.'],
    ['Samuel Tuttle', '31, journeyman cooper, Baltimore, Maryland', 'I pay my taxes in sweat. The law says a man needs fifty acres before his opinion counts.']],
  enslaved: [['Hannah', '30, enslaved cook, Albemarle County, Virginia', 'The Constitution counts me as three-fifths of a person, so Virginia gets more electors for owning me. I get no say at all.'],
    ['Cato', '40, enslaved blacksmith, Charleston, South Carolina', 'I am hired out, and my master keeps the wages. The men who make the laws own the men who live under them.']],
  women: [['Abigail Foster', '36, farm wife, Litchfield County, Connecticut', 'My husband votes the way his father did. I read the newspapers aloud to him in the evening.'],
    ['Harriet Lowell', '24, mill worker, Lowell, Massachusetts', 'I work thirteen hours a day at the looms and pay my board from my own wages. The men who set our hours are elected by men.'],
    ['Nora Brennan', '41, laundress, Chicago, Illinois', 'The saloon on our corner takes half of what my husband earns. If I could vote, it would be gone by spring.'],
    ['Ida Lindgren', '32, stenographer, Minneapolis, Minnesota', 'The boy who delivers my newspaper turns twenty-one this year and gets the vote before I do.']],
  'north-men': [['Caleb Morse', '47, farmer, Oneida County, New York', 'My father voted, and his father fought the British for the right to. I haven’t missed an election.'],
    ['Henry Voss', '39, carpenter, Cincinnati, Ohio', 'I vote for the party that fought for the Union. Most of the men in my ward do.']],
  'south-men': [['William Hardee', '44, farmer, Wilkes County, Georgia', 'My people have voted Democratic since Jackson. I don’t see a reason to stop.']],
  'south-white': [['Robert Dunn', '47, cotton farmer, Hill County, Texas', 'Cotton is cheap and the railroads take half of it. Down here the Democrats are the only party that counts.'],
    ['Earl Cobb', '46, mill hand, Spartanburg, South Carolina', 'I paid my poll tax this year. Most of the men at the mill didn’t, and can’t vote.']],
  freedmen: [['Jacob Wells', '30, sharecropper, Hinds County, Mississippi', 'I voted for Grant the first time anyone ever asked me anything. The Klan came to the schoolhouse the next week.']],
  'black-south': [['Henry Toussaint', '48, dockworker, New Orleans, Louisiana', 'They moved the polling place three times this year and never told us where.'],
    ['Albert Mayes', '50, farmer, Lowndes County, Alabama', 'The poll tax adds up for every year you missed, back to twenty-one. I would owe a month’s wages to vote once.'],
    ['Ruth Jenkins', '34, schoolteacher, Sunflower County, Mississippi', 'The registrar asked me how many bubbles are in a bar of soap. I teach algebra. I did not get registered.']],
  'black-north': [['Leon Carter', '29, packinghouse worker, Chicago, Illinois', 'My folks came up from Mississippi so we could vote. In Chicago nobody asks me to count the bubbles in a bar of soap.']],
  immigrants: [['Michael Brennan', '31, canal laborer, Buffalo, New York', 'The ward boss found me work the week I landed. He’ll want my vote the day I’m naturalized.'],
    ['Giuseppe Russo', '28, bricklayer, Providence, Rhode Island', 'Four years here. One more and I can be naturalized. Until then the ward boss talks to me like I already vote.']],
  north: [['Helen Kowalski', '38, telephone operator, Cleveland, Ohio', 'My mother never got to vote. I haven’t missed an election since I could.']],
  youth: [['Frank Doyle', '19, sailor, Norfolk, Virginia', 'I’ve been in the Navy a year. Old enough to fight, not old enough to vote.']],
  white: [['Karen Mills', '51, insurance agent, Columbus, Ohio', 'I split my ticket most years. This time I went with whoever I trust on the economy.']],
  black: [['James Whitfield', '58, bus driver, Atlanta, Georgia', 'My father couldn’t vote in this state. I have never missed an election, and neither has anyone in my house.']],
  latino: [['Ana Morales', '34, dental hygienist, San Antonio, Texas', 'My parents became citizens when I was ten. They took me to the polls with them every time.']],
  young: [['Kevin Tran', '22, line cook, San Jose, California', 'I registered at the DMV and forgot about it. My roommate dragged me to the polls.']],
  felony: [['Marcus Webb', '41, roofer, Tallahassee, Florida', 'I served my time years ago. I pay taxes and coach Little League, and I still can’t vote.']],
};
