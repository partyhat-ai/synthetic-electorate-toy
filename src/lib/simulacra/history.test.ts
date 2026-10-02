import { describe, expect, test } from 'vitest';
import { ELECTION_YEARS, STATE_BY_CODE } from './geo';
import { electionOf } from './history';

// Years whose per-state electoral votes don't sum to the electoral votes cast,
// with the per-state sum the table holds: these list the electors each state
// was allotted, not those who voted (1789: New York chose none; 1864: one
// Nevada elector didn't vote). Pinned so a data change shows.
const ALLOTTED_NOT_CAST: Readonly<Record<number, number>> = {
  1789: 73,
  1792: 135,
  1808: 176,
  1812: 218,
  1816: 221,
  1820: 236,
  1832: 288,
  1864: 234,
};

// States whose votes were counted before geo.ts's `first` year (both were
// counted "in the alternative" before admission), so the map leaves their
// tile empty that year. Pinned until the data owner decides which is right.
const COUNTED_EARLY: ReadonlySet<string> = new Set(['1820 MO', '1836 MI']);

describe('electionOf', () => {
  test.each(ELECTION_YEARS)('%i: 51 or fewer real states, a majority, electors summing to the total', (y) => {
    const e = electionOf(y);
    expect(e).not.toBeNull();
    if (!e) return;
    expect(e.year).toBe(y);
    expect(e.states.length).toBeLessThanOrEqual(51);
    expect(new Set(e.states.map((s) => s.code)).size).toBe(e.states.length);
    for (const s of e.states) {
      expect(STATE_BY_CODE.has(s.code), s.code).toBe(true);
      // A state votes only once it's in the Union.
      if (!COUNTED_EARLY.has(`${y} ${s.code}`)) expect(STATE_BY_CODE.get(s.code)?.first, s.code).toBeLessThanOrEqual(y);
      expect(s.ev, s.code).toBeGreaterThan(0);
    }
    expect(e.majority).toBe(Math.floor(e.total / 2) + 1);
    const sum = e.states.reduce((a, s) => a + s.ev, 0);
    expect(sum).toBe(ALLOTTED_NOT_CAST[y] ?? e.total);
  });

  test('the winner is A, the runner-up B, and unopposed years have no B', () => {
    for (const y of ELECTION_YEARS) {
      const e = electionOf(y);
      if (!e) continue;
      expect(e.candidates[0].key).toBe('A');
      expect(e.unopposed).toBe(e.candidates[1]?.key !== 'B');
    }
    expect(ELECTION_YEARS.filter((y) => electionOf(y)?.unopposed)).toEqual([1789, 1792, 1820]);
  });

  test('a year with no election is null', () => {
    expect(electionOf(1790)).toBeNull();
  });

  test('every winner and runner-up has a name and a portrait', () => {
    for (const y of ELECTION_YEARS) {
      for (const c of electionOf(y)?.candidates.slice(0, 2) ?? []) {
        expect(c.name.length, `${y} ${c.key}`).toBeGreaterThan(0);
        expect(c.portrait, `${y} ${c.key}`).toMatch(/^https:\/\/upload\.wikimedia\.org\//);
      }
    }
  });
});
