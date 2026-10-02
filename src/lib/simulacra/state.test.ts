import { describe, expect, test } from 'vitest';
import type { Outcome, SimulacraApi } from './api';
import type { ElectionResponse } from './schemas';
import { addEdit, apiOptionsFor, askOf, isDirty, randomStory, readParams, toggled, urlForYear } from './state';
import { PageState } from './state.svelte';

describe('askOf', () => {
  test('the same what-ifs in any order, the same words with any spacing: the same ask', () => {
    expect(askOf(['no-19th', 'league'], '  women stay home ', undefined)).toBe(askOf(['league', 'no-19th'], 'women stay home', undefined));
  });

  test('different what-ifs, words or dots: a different ask', () => {
    const base = askOf(['league'], '', undefined);
    expect(askOf(['league', 'no-19th'], '', undefined)).not.toBe(base);
    expect(askOf(['league'], 'and more', undefined)).not.toBe(base);
    expect(askOf(['league'], '', { women: { A: 0.1, home: -0.1 } })).not.toBe(base);
  });

  test('no edits and empty edits ask the same; the keys passed in are left alone', () => {
    const keys = ['b', 'a'];
    expect(askOf(keys, '', undefined)).toBe(askOf(keys, '', {}));
    expect(keys).toEqual(['b', 'a']);
  });
});

describe('the pure parts', () => {
  test('isDirty: typed words always; with no rerun, anything chosen or dragged; else anything changed since', () => {
    expect(isDirty(null, [], ' x ', undefined)).toBe(true);
    expect(isDirty(null, [], '', undefined)).toBe(false);
    expect(isDirty(null, ['league'], '', undefined)).toBe(true);
    const shown = { ask: askOf(['league'], '', undefined) };
    expect(isDirty(shown, ['league'], '  ', undefined)).toBe(false);
    expect(isDirty(shown, ['league', 'no-19th'], '', undefined)).toBe(true);
  });

  test('addEdit sums each fraction over drags, per group', () => {
    const one = addEdit(undefined, 'women', { A: 0.1, home: -0.1 });
    const two = addEdit(one, 'women', { A: 0.05, B: -0.05 });
    const three = addEdit(two, 'men', { O: 0.02, home: -0.02 });
    expect(three).toEqual({ women: { A: 0.15000000000000002, home: -0.1, B: -0.05 }, men: { O: 0.02, home: -0.02 } });
    expect(one).toEqual({ women: { A: 0.1, home: -0.1 } });
  });

  test('toggled adds or removes one key', () => {
    expect(toggled(['a'], 'b')).toEqual(['a', 'b']);
    expect(toggled(['a', 'b'], 'a')).toEqual(['b']);
  });

  test('the URL: sample, simapi in dev only, an election year or none', () => {
    const p = (q: string, dev = true) => readParams(new URLSearchParams(q), dev);
    expect(p('sample=1&year=1896')).toEqual({ sample: true, simapi: null, year: 1896 });
    expect(p('sample=true&year=1897').year).toBeNull();
    expect(p('simapi=http://localhost:8787').simapi).toBe('http://localhost:8787');
    expect(p('simapi=http://localhost:8787', false).simapi).toBeNull();
    expect(apiOptionsFor('http://localhost:8787')).toEqual({ base: 'http://localhost:8787/api/simulacra' });
    expect(apiOptionsFor(null)).toEqual({});
    expect(urlForYear('http://x.test/?sample=1&year=1896', 1896)).toBeNull();
    expect(urlForYear('http://x.test/?sample=1', 1912)).toBe('http://x.test/?sample=1&year=1912');
  });

  test('randomStory never repeats the year it leaves', () => {
    for (const r of [0, 0.3, 0.6, 0.999]) expect(randomStory(1896, () => r)).not.toBe(1896);
  });
});

const ELECTION: ElectionResponse = {
  slices: [{ key: 'women', label: 'Women', adults: 27, barred: 0, home: 0.5, A: 0.3, B: 0.15, O: 0.05 }],
  whatIfs: [{ key: 'league', label: 'The League', kind: 'issue', detail: 'The Senate ratifies.', slices: ['women'] }],
  simulated: true,
};

/** A server that answers every year and never starts a run. */
function fakeApi(): SimulacraApi & { elections: number[] } {
  const elections: number[] = [];
  const no: Outcome<never> = { kind: 'error', reason: 'failed', message: 'The simulation server answered 500.', status: 500 };
  return {
    sample: false,
    elections,
    election: async (y) => {
      elections.push(y);
      return { kind: 'ok', value: ELECTION };
    },
    startRun: async () => no,
    run: async () => no,
    stopRun: async () => ({ kind: 'ok', value: null }),
    voter: async () => no,
  };
}

describe('PageState', () => {
  test('edits and chosen what-ifs per year survive switching years', async () => {
    const api = fakeApi();
    const page = new PageState({ api, year: 1920 });
    await page.loadSim(1920);
    expect(page.server).toBe('online');
    page.toggle('league');
    page.editSlice('women', { A: 0.1, home: -0.1 });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(page.runError).toBe('The simulation server answered 500.');
    const asked = page.askOf(1920, ['league'], '');

    page.setYear(1896);
    expect(page.year).toBe(1896);
    expect(page.view).toBe('history');
    expect(page.runError).toBeNull();
    expect(page.edits.get(1896)).toBeUndefined();
    expect(page.selected).toEqual([]);

    page.setYear(1920);
    expect(page.edits.get(1920)).toEqual({ women: { A: 0.1, home: -0.1 } });
    expect(page.selected).toEqual(['league']);
    expect(page.askOf(1920, ['league'], '')).toBe(asked);
    expect(page.dirty).toBe(true);
  });

  test('reset clears only the year on show', async () => {
    const page = new PageState({ api: fakeApi(), year: 1920 });
    await page.loadSim(1920);
    page.toggle('league');
    page.setYear(1896);
    await page.loadSim(1896);
    page.toggle('league');
    page.reset();
    expect(page.chosen.get(1896)).toEqual([]);
    expect(page.chosen.get(1920)).toEqual(['league']);
  });

  test('the URL follows the year once it is ready', () => {
    const urls: string[] = [];
    let href = 'http://x.test/?sample=1';
    const page = new PageState({
      api: fakeApi(),
      year: 1920,
      href: () => href,
      replaceUrl: (u) => {
        urls.push(u);
        href = u;
      },
    });
    page.setYear(1912);
    expect(urls).toEqual([]);
    page.urlReady = true;
    page.syncUrl();
    page.setYear(1916);
    page.syncUrl();
    expect(urls).toEqual(['http://x.test/?sample=1&year=1912', 'http://x.test/?sample=1&year=1916']);
  });

  test('no simulation service: the page says so, and a year loads once', async () => {
    const api = fakeApi();
    const page = new PageState({
      api: { ...api, election: async () => ({ kind: 'unsupported', message: 'This server has no simulation service yet.' }) },
      year: 1920,
    });
    await page.loadSim(1920);
    expect(page.server).toBe('unsupported');
    expect(page.simFailed).toBe('This server has no simulation service yet.');
    const ok = new PageState({ api, year: 1920 });
    await ok.loadSim(1920);
    await ok.loadSim(1920);
    expect(api.elections).toEqual([1920]);
  });
});
