import { describe, expect, test } from 'vitest';
import { SimError, type SimulacraApi } from './api';
import type { ElectionResponse } from './schemas';
import { isDirty, randomStory, readParams, toggled, urlForYear } from './state';
import { PageState } from './state.svelte';

describe('the pure parts', () => {
  test('isDirty: typed words always; with no rerun, anything chosen; else a different choice', () => {
    expect(isDirty(null, [], ' x ')).toBe(true);
    expect(isDirty(null, [], '')).toBe(false);
    expect(isDirty(null, ['league'], '')).toBe(true);
    const shown = { ran: ['league'] };
    expect(isDirty(shown, ['league'], '  ')).toBe(false);
    expect(isDirty(shown, ['league', 'no-19th'], '')).toBe(true);
  });

  test('toggled adds or removes one key', () => {
    expect(toggled(['a'], 'b')).toEqual(['a', 'b']);
    expect(toggled(['a', 'b'], 'a')).toEqual(['b']);
  });

  test('the URL: an election year or none', () => {
    const p = (q: string) => readParams(new URLSearchParams(q));
    expect(p('year=1896')).toEqual({ year: 1896 });
    expect(p('year=1897').year).toBeNull();
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
    page.rerunNow();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(page.runError).toBe('The simulation server answered 500.');

    page.setYear(1896);
    expect(page.year).toBe(1896);
    expect(page.view).toBe('history');
    expect(page.runError).toBeNull();
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
