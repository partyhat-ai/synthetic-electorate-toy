import { describe, expect, test } from 'vitest';
import { ELECTION_YEARS, GRID, STATE_BY_CODE, STATES } from './geo';

describe('geo', () => {
  test('60 elections, every four years from 1792, 1789 first', () => {
    expect(ELECTION_YEARS.length).toBe(60);
    expect(ELECTION_YEARS[0]).toBe(1789);
    expect(ELECTION_YEARS.at(-1)).toBe(2024);
    for (let i = 2; i < ELECTION_YEARS.length; i++) expect((ELECTION_YEARS[i] ?? 0) - (ELECTION_YEARS[i - 1] ?? 0)).toBe(4);
  });

  test('the grid covers every state, one tile each', () => {
    expect(STATES.length).toBe(51);
    const cells = new Set<string>();
    for (const s of STATES) {
      expect(s.row, s.code).toBeGreaterThanOrEqual(0);
      expect(s.row, s.code).toBeLessThan(GRID.rows);
      expect(s.col, s.code).toBeGreaterThanOrEqual(0);
      expect(s.col, s.code).toBeLessThan(GRID.cols);
      cells.add(`${s.row},${s.col}`);
    }
    expect(cells.size).toBe(STATES.length);
    expect(STATE_BY_CODE.size).toBe(STATES.length);
  });
});
