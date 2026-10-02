import { describe, expect, test } from 'vitest';
import { ELECTION_YEARS } from './geo';
import { electionOf } from './history';
import { SimError } from './api';
import { _model, createSampleApi, UNOPPOSED } from './sample';
import { RunResultSchema, RunStatusSchema, VoterSchema } from './schemas';

const fast = () => Promise.resolve();

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
    expect(r.confidence).toBeNull();
    // The sample's results satisfy the server's contract.
    expect(RunResultSchema.safeParse(r).success).toBe(true);
  });

  test('1789, unopposed, has no runner-up and doesn’t crash', async () => {
    expect(electionOf(1789)?.unopposed).toBe(true);
    expect(_model.national(1789)).toEqual(UNOPPOSED);
    expect(_model.whatIfsFor(1789)).toEqual([]);
    expect(_model.slicesFor(1789).length).toBeGreaterThan(0);
    expect(_model.rerun(1789, ['women'], 'what if women could vote')?.winner).toBe('A');

    let t = 0;
    const api = createSampleApi({ sleep: fast, now: () => t });
    expect((await api.election(1789)).whatIfs).toEqual([]);
    const started = await api.startRun(1789);
    t = 1e6;
    expect((await api.run(started.id)).status).toBe('done');
    const slice = _model.slicesFor(1789)[0]?.key ?? '';
    expect((await api.voter(1789, slice, started.id)).name.length).toBeGreaterThan(0);
  });

  test('every what-if of every year runs and stays inside the contract', () => {
    for (const y of ELECTION_YEARS) {
      for (const w of _model.whatIfsFor(y)) {
        const r = _model.rerun(y, [w.key]);
        expect(RunResultSchema.safeParse(r).success, `${y} ${w.key}`).toBe(true);
        expect(r?.applied.map((a) => a.key)).toEqual([w.key]);
      }
    }
  });

  test('typed words are read as a what-if, or handed back as unknown', () => {
    expect(_model.rerun(1912, [], 'what if Taft dropped out')?.applied.map((a) => a.key)).toEqual(['taft-out']);
    expect(_model.rerun(1912, [], 'what if it rained')?.unknown).toBe('what if it rained');
  });
});

describe('createSampleApi', () => {
  test('a run counts states over time, then is done; a stopped run fails', async () => {
    let t = 0;
    const api = createSampleApi({ sleep: fast, now: () => t });
    const { id } = await api.startRun(2000, { whatIfs: ['nader-out'] });
    t = 45 * 10;
    expect(await api.run(id)).toMatchObject({ status: 'running', done: 10 });
    t = 1e6;
    const done = await api.run(id);
    expect(RunStatusSchema.safeParse(done).success).toBe(true);
    expect(done.status === 'done' && done.result.applied[0]?.key).toBe('nader-out');
    expect(VoterSchema.safeParse(await api.voter(2000, 'felony', id)).success).toBe(true);
    await api.stopRun(id);
    expect(await api.run(id)).toEqual({ status: 'failed', error: 'That run was stopped.' });
  });

  test('an unknown group or year is a missing error, not an empty answer', async () => {
    const api = createSampleApi({ sleep: fast });
    await expect(api.voter(1912, 'nobody')).rejects.toBeInstanceOf(SimError);
    await expect(api.startRun(1790)).rejects.toBeInstanceOf(SimError);
  });
});
