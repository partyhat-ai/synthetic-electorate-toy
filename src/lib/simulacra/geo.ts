// Simulacra Americana's geography: every election year, and the tile map's
// grid with the year each state first cast electoral votes. Who won what is
// in history.ts.

/** Every presidential election, 1788–89 (drawn as 1789) to 2024. */
export const ELECTION_YEARS: readonly number[] = [1789, ...Array.from({ length: 59 }, (_, i) => 1792 + i * 4)];

export interface UsState {
  readonly code: string;
  readonly name: string;
  /** Tile row and column on the map grid. */
  readonly row: number;
  readonly col: number;
  /** The first presidential election the state cast electoral votes in. */
  readonly first: number;
}

// [code, name, row, col, first presidential election cast]. A 12 × 8 square
// tile grid, west to east, north to south; `first` is the first election
// after admission (a state admitted before Election Day votes that year).
type Raw = readonly [code: string, name: string, row: number, col: number, first: number];
const RAW: readonly Raw[] = [
  ['AK', 'Alaska', 0, 0, 1960], ['ME', 'Maine', 0, 11, 1820],
  ['WI', 'Wisconsin', 1, 6, 1848], ['VT', 'Vermont', 1, 10, 1792], ['NH', 'New Hampshire', 1, 11, 1789],
  ['WA', 'Washington', 2, 1, 1892], ['ID', 'Idaho', 2, 2, 1892], ['MT', 'Montana', 2, 3, 1892], ['ND', 'North Dakota', 2, 4, 1892],
  ['MN', 'Minnesota', 2, 5, 1860], ['IL', 'Illinois', 2, 6, 1820], ['MI', 'Michigan', 2, 7, 1840], ['NY', 'New York', 2, 9, 1789],
  ['MA', 'Massachusetts', 2, 10, 1789],
  ['OR', 'Oregon', 3, 1, 1860], ['NV', 'Nevada', 3, 2, 1864], ['WY', 'Wyoming', 3, 3, 1892], ['SD', 'South Dakota', 3, 4, 1892],
  ['IA', 'Iowa', 3, 5, 1848], ['IN', 'Indiana', 3, 6, 1816], ['OH', 'Ohio', 3, 7, 1804], ['PA', 'Pennsylvania', 3, 8, 1789],
  ['NJ', 'New Jersey', 3, 9, 1789], ['CT', 'Connecticut', 3, 10, 1789], ['RI', 'Rhode Island', 3, 11, 1792],
  ['CA', 'California', 4, 1, 1852], ['UT', 'Utah', 4, 2, 1896], ['CO', 'Colorado', 4, 3, 1876], ['NE', 'Nebraska', 4, 4, 1868],
  ['MO', 'Missouri', 4, 5, 1824], ['KY', 'Kentucky', 4, 6, 1792], ['WV', 'West Virginia', 4, 7, 1864], ['VA', 'Virginia', 4, 8, 1789],
  ['MD', 'Maryland', 4, 9, 1789], ['DE', 'Delaware', 4, 10, 1789],
  ['AZ', 'Arizona', 5, 2, 1912], ['NM', 'New Mexico', 5, 3, 1912], ['KS', 'Kansas', 5, 4, 1864], ['AR', 'Arkansas', 5, 5, 1836],
  ['TN', 'Tennessee', 5, 6, 1796], ['NC', 'North Carolina', 5, 7, 1792], ['SC', 'South Carolina', 5, 8, 1789],
  ['DC', 'District of Columbia', 5, 9, 1964],
  ['OK', 'Oklahoma', 6, 4, 1908], ['LA', 'Louisiana', 6, 5, 1812], ['MS', 'Mississippi', 6, 6, 1820], ['AL', 'Alabama', 6, 7, 1820],
  ['GA', 'Georgia', 6, 8, 1789],
  ['HI', 'Hawaii', 7, 0, 1960], ['TX', 'Texas', 7, 4, 1848], ['FL', 'Florida', 7, 8, 1848],
];

export const STATES: readonly UsState[] = RAW.map(([code, name, row, col, first]) => ({ code, name, row, col, first }));
export const STATE_BY_CODE: ReadonlyMap<string, UsState> = new Map(STATES.map((s) => [s.code, s]));
export const GRID = { cols: 12, rows: 8 } as const;
