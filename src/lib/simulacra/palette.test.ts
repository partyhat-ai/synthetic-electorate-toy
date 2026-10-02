import { describe, expect, test } from 'vitest';
import { electionOf } from './history';
import { candidateHues, onPaint, paint } from './palette';

describe('candidateHues', () => {
  test('parties keep their colour; the 4th candidate and beyond fold into Other', () => {
    // 1860: Lincoln (R), Breckinridge (Southern Democrat), Bell, Douglas.
    const e = electionOf(1860);
    expect(e).not.toBeNull();
    if (!e) return;
    const hues = candidateHues(
      e.candidates.map((c) => ({ key: c.key, party: c.family })),
      Object.fromEntries(e.candidates.map((c) => [c.key, c.ev])),
    );
    expect(hues.get('A')).toBe('red');
    expect(hues.get('B')).toBe('blue');
    // Bell (39 EV) takes the era's free hue; Douglas (12 EV), fourth, is Other.
    expect(hues.get('C')).toBe('green');
    expect(hues.get('D')).toBe('other');
  });

  test('a party already holding its hue doesn’t take it twice', () => {
    const hues = candidateHues([
      { key: 'A', party: 'democratic' },
      { key: 'B', party: 'democratic' },
      { key: 'C', party: 'whig' },
    ]);
    expect(hues.get('A')).toBe('blue');
    expect(hues.get('C')).toBe('orange');
    expect(hues.get('B')).toBe('aqua');
  });

  test('the founding era: Democratic-Republicans aqua, Federalists violet', () => {
    const hues = candidateHues([
      { key: 'A', party: 'democratic-republican' },
      { key: 'B', party: 'federalist' },
    ]);
    expect([hues.get('A'), hues.get('B')]).toEqual(['aqua', 'violet']);
  });
});

describe('paint and onPaint', () => {
  test('light and dark steps differ; no hue is Other', () => {
    expect(paint('blue', true)).toBe('#2a78d6');
    expect(paint('blue', false)).toBe('#5488c7');
    expect(paint(undefined, true)).toBe(paint('other', true));
  });

  test('label ink inverts with the mode', () => {
    // Violet: white on screen in light mode, black on screen (authored white) in dark.
    expect(onPaint('violet', true)).toBe('#ffffff');
    expect(onPaint('violet', false)).toBe('#ffffff');
    // Blue: black on screen in both, so authored black in light and white in dark.
    expect(onPaint('blue', true)).toBe('#000000');
    expect(onPaint('blue', false)).toBe('#ffffff');
  });
});
