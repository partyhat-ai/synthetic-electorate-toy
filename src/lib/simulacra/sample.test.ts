import { describe, expect, test } from 'vitest';
import { ELECTION_YEARS } from './geo';
import { electionOf } from './history';
import { _model, UNOPPOSED } from './sample';

describe('the sample model', () => {
  test.each(ELECTION_YEARS)('an unchanged rerun of %i reproduces history', (y) => {
    const e = electionOf(y);
    const r = _model.rerun(y);
    expect(e).not.toBeNull();
    expect(r).not.toBeNull();
    if (!e || !r) return;
    expect(r.winner).toBe(e.winner);
    expect(r.ev.A).toBe(e.candidates[0].ev);
    expect(r.ev.B).toBe(e.candidates[1]?.ev ?? 0);
    expect(r.states.filter((s) => s.flipped)).toEqual([]);
    expect(new Map(r.states.map((s) => [s.code, s.won]))).toEqual(new Map(e.states.map((s) => [s.code, s.won])));
  });

  test('1789, unopposed, has no runner-up and doesn’t crash', () => {
    expect(electionOf(1789)?.unopposed).toBe(true);
    expect(_model.national(1789)).toEqual(UNOPPOSED);
    expect(_model.rerun(1789)?.winner).toBe('A');
  });
});
