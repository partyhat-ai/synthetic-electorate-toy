import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, test } from 'vitest';
import { LIMITED_MESSAGE } from './api';
import { type SayInput, say, sourcesOf, traceOf } from './narrator';
import { type Bundle, BundleSchema, type RunResult } from './schemas';
import { electionFor, type ShownRun } from './state';

const ROOT = fileURLToPath(new URL('../../..', import.meta.url));
const bundle = BundleSchema.parse(JSON.parse(readFileSync(join(ROOT, 'tests', 'fixtures', 'bundle.example.json'), 'utf8')));

/** A run as the server answers it (serve/simulacra.ts compute): the bundle's run plus the briefs behind it. */
function served(b: Bundle, keys: readonly string[]): RunResult {
  const base = b.runs[[...keys].sort().join('+')];
  if (!base) throw new Error(`no run for ${keys.join('+')}`);
  const told = Object.fromEntries(keys.flatMap((k) => (b.told?.[k] ? [[k, b.told[k]]] : [])));
  return { ...base, told, ...(b.pre ? { pre: b.pre } : {}) };
}

describe('traceOf', () => {
  test('two chosen what-ifs: applied, what changed, the brief, what voters were told, the interviews, the research, the count', () => {
    const res = served(bundle, ['league', 'no-19th']);
    expect(traceOf(res, '', ['league', 'no-19th'], 1920)).toEqual([
      'Applied: The Senate Ratifies the League, The 19th Amendment Fails.',
      'What changed: The Senate ratifies the peace treaty with its reservations in March 1920, and the League is no longer a campaign issue.',
      'What changed: Tennessee votes the suffrage amendment down, so women can vote for president only where their own state already let them.',
      'Briefed: Each voter got a life, a home state and the ballot, dated November 1, 1920. Each read 3 real newspaper items from that year. Candidates appeared as neutral letters, not names.',
      'Pre-interviewed: 12 synthetic voters, in 1920 as it was. This set the baseline.',
      'Told the voters: The Senate Ratifies the League. “In March 1920 the Senate ratified the peace treaty with its reservations, and the United States took its seat in the League of Nations this spring. The treaty is settled, and neither party proposes to reopen it.” Taken off the platforms: League of Nations.',
      'Told the voters: The 19th Amendment Fails. “In August the Tennessee legislature voted the woman suffrage amendment down, and it has not been ratified.”',
      'Asked again: 4 people in 2 groups, now with the change. Each heard one of 3 wordings of the question.',
      'Measured: Each person’s answer with the change, minus their answer without it.',
      "What historians found (9 findings, strong evidence): No source measures the League's effect on 1920 voting. Sources give qualitative accounts: the League and Wilson hurt Cox, Irish and German Americans left the Democrats (partly over wartime grievances), and Harding won 60.3% to 34.1% on low turnout. No group-level numbers.",
      'Against history: On the Republican two-party share, the sources point the same way as the interviews (-0.1 points), without numbers.',
      'The numbers: the 1920 census voting-age tables and certified returns; every draw reproduces 1920 exactly before the change.',
      'How sure: I reran it 100 times with different population and parameter draws.',
      "Low confidence: The interviews' answer changes sign with the question's wording, though the record points the same way.",
      'Counted: 4 states.',
    ]);
  });

  test('typed words: how they were read, no Applied line, and one what-if told without a lead', () => {
    const lines = traceOf(served(bundle, ['league']), 'what if the league passed', [], 1920);
    expect(lines[0]).toBe('Read: “what if the league passed” as The Senate Ratifies the League.');
    expect(lines.some((l) => l.startsWith('Applied:'))).toBe(false);
    expect(lines.find((l) => l.startsWith('Told the voters:'))).toMatch(/^Told the voters: “In March 1920/);
  });

  test('a staged what-if: the real items it takes out and the news from its world', () => {
    const told = (removed: number) => ({
      league: { facts: ['The treaty is settled.'], removed, items: [{ date: '1920-10-01', text: 'Geneva cheers.' }, { date: '1920-10-02', text: 'Delegates sail.' }] },
    });
    const line = (removed: number) =>
      traceOf({ ...served(bundle, ['league']), told: told(removed) }, '', ['league'], 1920).find((l) => l.startsWith('Told the voters:'));
    expect(line(2)).toBe(
      'Told the voters: “The treaty is settled.” Took out 2 newspaper items the change makes false. Their newspapers also carried: “Geneva cheers.” “Delegates sail.”',
    );
    expect(line(1)).toContain(' Took out 1 newspaper item the change makes false.');
    expect(line(0)).not.toContain('Took out');
  });

  test('a reinterpreted change leads its explanation, with what changed', () => {
    const base = served(bundle, ['league']);
    const reread = 'Not quite what you asked: the League passing reads as the Senate ratifying the treaty.';
    const lines = traceOf({ ...base, howIGotThis: [...(base.howIGotThis ?? []), reread] }, 'what if the league passed', [], 1920);
    const at = lines.indexOf(reread);
    expect(at).toBeGreaterThan(0);
    expect(at).toBeLessThan(lines.findIndex((l) => l.startsWith('Briefed:')));
    expect(lines.filter((l) => l === reread)).toHaveLength(1);
  });

  test('no interviews: no brief and no pre-interview', () => {
    const res = { ...served(bundle, ['no-19th']), cohortEffects: [] };
    const lines = traceOf(res, '', ['no-19th'], 1920);
    expect(lines.some((l) => l.startsWith('Briefed:') || l.startsWith('Pre-interviewed:') || l.startsWith('Asked again:'))).toBe(false);
  });

  test('sources: the research behind the applied what-ifs, and the data not already cited', () => {
    const s = sourcesOf(served(bundle, ['league']));
    expect(s?.research.length).toBeGreaterThan(0);
    expect(s?.research.every((r) => typeof r.text === 'string' && r.text.length > 0)).toBe(true);
  });
});

const ELECTION = electionFor(1920);
const NAMES = { A: 'Harding', B: 'Cox', O: 'Others' };
const BASE: SayInput = {
  server: 'online',
  year: 1920,
  election: ELECTION,
  run: null,
  running: false,
  runError: null,
  simFailed: null,
  sim: { slices: bundle.election.slices, whatIfs: bundle.election.whatIfs },
  toggled: null,
  whatIfs: bundle.election.whatIfs,
  slice: null,
  showing: 'history',
  result: null,
  names: NAMES,
  person: null,
  finding: false,
  draft: '',
  shown: Infinity,
  sample: false,
};

describe('say', () => {
  test('the server first: connecting, no service, too many requests', () => {
    expect(say({ ...BASE, server: 'connecting' })).toEqual({ text: 'Getting 1920’s voters ready.', busy: true });
    const none = say({ ...BASE, server: 'unsupported' });
    expect(none.text).toBe('This server has no simulation service yet, so I can’t rerun elections here.');
    expect(none.actions?.map((a) => a.key)).toEqual(['sample', 'retry']);
    const limited = say({ ...BASE, server: 'limited' });
    expect(limited.text).toBe(LIMITED_MESSAGE);
    expect(limited.actions?.map((a) => a.key)).toEqual(['retry']);
  });

  test('the greeting, a tapped suggestion, then a rerun coming out step by step', () => {
    expect(say(BASE).text).toBe('Change one thing about 1920 and I’ll rerun it.');
    expect(say(BASE).detail).toBe('Pick a counterfactual or type your own.\nTap a group to meet someone in it.');
    expect(say({ ...BASE, toggled: 'league' }).detail).toBe('What people care about, low confidence. Press Rerun to see what happens.');
    const res = served(bundle, ['league']);
    const trace = traceOf(res, '', ['league'], 1920);
    const shown: ShownRun = { ...res, runId: 'r1', keys: ['league'], text: '', trace, ask: '', ran: ['league'] };
    const working = say({ ...BASE, result: shown, showing: 'whatif', shown: 1 });
    expect(working.busy).toBe(true);
    expect(working.steps?.map((s) => s.state)).toEqual(['done', 'doing']);
    const verdict = say({ ...BASE, result: shown, showing: 'whatif' });
    expect(verdict.text).toBe(res.summary.replaceAll('the voters I interviewed', 'the voters'));
    expect(verdict.text).toContain('the voters lean');
    expect(verdict.steps).toHaveLength(trace.length);
    expect(say({ ...BASE, result: shown }).text).toBe('This is 1920 as it happened. Switch to Rerun to see yours.');
  });
});
