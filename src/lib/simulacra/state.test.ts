import { describe, expect, test } from 'vitest';
import { SimError, type SimulacraApi } from './api';
import type { ElectionResponse } from './schemas';
import { addEdit, isDirty, randomStory, readParams, toggled, urlForYear } from './state';
import { PageState } from './state.svelte';

describe('the pure parts', () => {
  test('isDirty: typed words always; with no rerun, anything chosen or dragged; else a different choice', () => {
    expect(isDirty(null, [], ' x ', undefined)).toBe(true);
    expect(isDirty(null, [], '', undefined)).toBe(false);
    expect(isDirty(null, ['league'], '', undefined)).toBe(true);
    const shown = { ran: ['league'] };
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

  test('the URL: sample, and an election year or none', () => {
    const p = (q: string) => readParams(new URLSearchParams(q));
    expect(p('sample=1&year=1896')).toEqual({ sample: true, year: 1896 });
    expect(p('sample=true&year=1897').year).toBeNull();
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
};

/** A server that answers every year and never starts a run. */
function fakeApi(): SimulacraApi {
  const no = () => Promise.reject(new SimError('failed', 'The simulation server answered 500.', 500));
  return {
    sample: false,
    election: async () => ELECTION,
    startRun: no,
    run: no,
    stopRun: async () => undefined,
    voter: no,
  };
}

describe('PageState', () => {
  test('a new year starts fresh', async () => {
    const page = new PageState({ api: fakeApi(), year: 1920 });
    await page.loadSim(1920);
    expect(page.server).toBe('online');
    page.toggle('league');
    page.editSlice('women', { A: 0.1, home: -0.1 });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(page.runError).toBe('The simulation server answered 500.');

    page.setYear(1896);
    expect(page.year).toBe(1896);
    expect(page.view).toBe('history');
    expect(page.runError).toBeNull();
    expect(page.edits).toBeUndefined();
    expect(page.selected).toEqual([]);
    expect(page.sim).toBeNull();
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

  test('no simulation service: the page says so', async () => {
    const page = new PageState({
      api: { ...fakeApi(), election: () => Promise.reject(new SimError('unsupported', 'This server has no simulation service yet.', 404)) },
      year: 1920,
    });
    await page.loadSim(1920);
    expect(page.server).toBe('unsupported');
    expect(page.simFailed).toBe('This server has no simulation service yet.');
  });
});
