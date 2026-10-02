import { describe, expect, test } from 'vitest';
import { parseFrameMessage, parseHostMessage } from './messages';

const stage = { right: 312, bottom: 40, width: 200, height: 260 };

describe('page → frame', () => {
  test.each([
    { type: 'robot:stage', stage },
    { type: 'robot:stage', stage: null },
    { type: 'robot:running', on: true },
    { type: 'robot:running', on: false },
    { type: 'robot:walk', on: true },
  ])('parses $type', (message) => {
    expect(parseHostMessage(message)).toEqual(message);
  });

  test('the parsed stage keeps every field', () => {
    const parsed = parseHostMessage({ type: 'robot:stage', stage });
    expect(parsed?.type === 'robot:stage' ? parsed.stage : null).toEqual(stage);
  });

  test.each([
    ['a string for a flag', { type: 'robot:walk', on: 'true' }],
    ['a stage missing its height', { type: 'robot:stage', stage: { ...stage, height: undefined } }],
    ['a stage with zero width', { type: 'robot:stage', stage: { ...stage, width: 0 } }],
    ['a stage with an infinite edge', { type: 'robot:stage', stage: { ...stage, right: Number.POSITIVE_INFINITY } }],
    ['a stage with NaN', { type: 'robot:stage', stage: { ...stage, bottom: Number.NaN } }],
    ['the old overlay protocol', { type: 'mecha-overlay:paint', paint: 'rerun' }],
    ['a frame-bound message', { type: 'robot:ready' }],
    ['a devtools message', { source: 'react-devtools-bridge', payload: {} }],
    ['a bare string', 'robot:walk'],
    ['null', null],
    ['undefined', undefined],
    ['a number', 7],
  ])('rejects %s', (_label, message) => {
    expect(parseHostMessage(message)).toBeNull();
  });
});

describe('frame → page', () => {
  test.each([
    { type: 'robot:ready' },
    { type: 'robot:anchors', anchors: { centerX: 412.5, feetY: 618 } },
    { type: 'robot:anchors', anchors: null },
  ])('parses $type', (message) => {
    expect(parseFrameMessage(message)).toEqual(message);
  });

  test.each([
    ['anchors without feet', { type: 'robot:anchors', anchors: { centerX: 1 } }],
    ['anchors with a string', { type: 'robot:anchors', anchors: { centerX: '1', feetY: 2 } }],
    ['anchors left out', { type: 'robot:anchors' }],
    ['the old ready', { type: 'mecha-overlay:ready' }],
    ['a page-bound message', { type: 'robot:walk', on: true }],
    ['an array', [{ type: 'robot:ready' }]],
    ['null', null],
  ])('rejects %s', (_label, message) => {
    expect(parseFrameMessage(message)).toBeNull();
  });
});
