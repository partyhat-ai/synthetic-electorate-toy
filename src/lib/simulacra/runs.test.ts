import { describe, expect, test } from 'vitest';
import type { Outcome, SimulacraApi } from './api';
import { type ActiveRun, createRunner, type Finished, POLL_MS, pollRun } from './runs';
import type { RunResult, RunStatus } from './schemas';

const RESULT: RunResult = {
  ev: { A: 300, B: 231, O: 0 },
  winner: 'A',
  states: [{ code: 'TN', won: 'B', flipped: true, margin: -0.4 }],
  slices: [],
  summary: 'Tennessee flips.',
  confidence: 'low',
  applied: [{ key: 'league', label: 'The Senate Ratifies the League', kind: 'issue' }],
  unknown: null,
};

const ok = <T>(value: T): Outcome<T> => ({ kind: 'ok', value });
const running = (done: number): Outcome<RunStatus> => ok({ status: 'running', done, total: 48 });
const done = (result: RunResult = RESULT): Outcome<RunStatus> => ok({ status: 'done', done: 48, total: 48, result });

/** A clock that only moves when the loop sleeps. */
function fakeClock() {
  let t = 0;
  const waits: number[] = [];
  return {
    waits,
    now: () => t,
    sleep: async (ms: number) => {
      waits.push(ms);
      t += ms;
    },
  };
}

/** api.run answers from `answers` in turn, repeating the last. */
function fakeRun(answers: Outcome<RunStatus>[]) {
  const ids: string[] = [];
  return {
    ids,
    run: async (id: string): Promise<Outcome<RunStatus>> => {
      ids.push(id);
      const next = answers.length > 1 ? answers.shift() : answers[0];
      if (!next) throw new Error('no answer');
      return next;
    },
  };
}

describe('pollRun', () => {
  test('polls until done, reporting progress', async () => {
    const clock = fakeClock();
    const api = fakeRun([running(10), running(20), running(30), done()]);
    const progress: number[] = [];
    const end = await pollRun(api, 'r1', { ...clock, current: () => true, onProgress: (r) => progress.push(r.done) });
    expect(end).toEqual({ kind: 'done', result: RESULT });
    expect(progress).toEqual([10, 20, 30]);
    expect(clock.waits).toEqual([POLL_MS, POLL_MS, POLL_MS, POLL_MS]);
    expect(api.ids).toEqual(['r1', 'r1', 'r1', 'r1']);
  });

  test('an indeterminate answer keeps polling', async () => {
    const clock = fakeClock();
    const unsure: Outcome<RunStatus> = { kind: 'indeterminate', message: 'No answer in time.' };
    const api = fakeRun([unsure, unsure, done()]);
    const end = await pollRun(api, 'r1', { ...clock, current: () => true });
    expect(end.kind).toBe('done');
    expect(api.ids).toHaveLength(3);
  });

  test('a failed run and an error both end it, with the reason', async () => {
    const clock = fakeClock();
    const failed = await pollRun(fakeRun([ok({ status: 'failed', error: 'Stopped.' })]), 'r1', { ...clock, current: () => true });
    expect(failed).toEqual({ kind: 'failed', message: 'Stopped.' });
    const offline: Outcome<RunStatus> = { kind: 'error', reason: 'offline', message: 'Can’t reach the simulation server.', status: 0 };
    const lost = await pollRun(fakeRun([offline]), 'r1', { ...clock, current: () => true });
    expect(lost).toEqual({ kind: 'failed', message: 'Can’t reach the simulation server.' });
  });

  test('a run the page dropped stops without another call', async () => {
    const clock = fakeClock();
    const api = fakeRun([running(1)]);
    const end = await pollRun(api, 'r1', { ...clock, current: () => false });
    expect(end).toEqual({ kind: 'dropped' });
    expect(api.ids).toHaveLength(0);
  });
});

/** A page for the runner: its run, and what it was told. */
function fakePage(api: SimulacraApi) {
  const clock = fakeClock();
  let run: ActiveRun | null = null;
  const seen: (ActiveRun | null)[] = [];
  const finished: Finished[] = [];
  const failed: string[] = [];
  const runner = createRunner({
    api,
    ...clock,
    getRun: () => run,
    setRun: (r) => {
      run = r;
      seen.push(r);
    },
    finished: (f) => {
      run = null;
      finished.push(f);
    },
    failed: (m) => failed.push(m),
  });
  return { runner, clock, seen, finished, failed, run: () => run };
}

function fakeApi(runAnswers: Outcome<RunStatus>[], start: Outcome<{ id: string }> = ok({ id: 'r1' })) {
  const stopped: string[] = [];
  const asked: unknown[] = [];
  const runs = fakeRun(runAnswers);
  const api: SimulacraApi = {
    sample: false,
    election: async () => ok({ slices: [], whatIfs: [] }),
    startRun: async (year, ask) => {
      asked.push({ year, ...ask });
      return start;
    },
    run: runs.run,
    stopRun: async (id) => {
      stopped.push(id);
      return ok(null);
    },
    voter: async () => ({ kind: 'error', reason: 'missing', message: 'No one.', status: 404 }),
  };
  return { api, stopped, asked };
}

const REQUEST = { year: 1920, keys: [], text: 'what if the league passed', edits: {}, total: 48, labels: [] };

describe('createRunner', () => {
  test('on done, the page gets the result and what was asked', async () => {
    const { api, asked } = fakeApi([running(10), done()]);
    const page = fakePage(api);
    await page.runner.start(REQUEST);
    expect(asked).toEqual([{ year: 1920, whatIfs: [], text: 'what if the league passed', edits: {} }]);
    expect(page.finished).toEqual([{ year: 1920, id: 'r1', result: RESULT, keys: [], text: 'what if the league passed' }]);
    expect(page.seen.map((r) => r && { id: r.id, done: r.done })).toEqual([
      { id: null, done: 0 },
      { id: 'r1', done: 0 },
      { id: 'r1', done: 10 },
    ]);
  });

  test('a start that may have landed is reported, not resubmitted', async () => {
    const { api, asked } = fakeApi([done()], { kind: 'indeterminate', message: 'The simulation server didn’t answer in time.' });
    const page = fakePage(api);
    await page.runner.start(REQUEST);
    expect(asked).toHaveLength(1);
    expect(page.failed).toEqual(['The simulation server didn’t answer in time.']);
    expect(page.run()).toBeNull();
  });

  test('stop drops the run and tells the server', async () => {
    const { api, stopped } = fakeApi([running(1)]);
    const page = fakePage(api);
    const started = page.runner.start(REQUEST);
    // Let it start and poll once, then stop it.
    await Promise.resolve();
    await Promise.resolve();
    page.runner.stop();
    await started;
    expect(page.run()).toBeNull();
    expect(page.finished).toEqual([]);
    expect(page.failed).toEqual([]);
    expect(stopped.length).toBeLessThanOrEqual(1);
  });
});
