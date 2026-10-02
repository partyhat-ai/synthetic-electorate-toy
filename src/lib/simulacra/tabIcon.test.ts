import { describe, expect, test } from 'vitest';
import { BLASTS, type BlastKey, type Clock, cycleColor, ICON_CYCLE_MS, iconHref, nextBlast, RESTING, TabIcon } from './tabIcon';

/** A clock the test winds by hand: one interval at a time. */
function manualClock() {
  let fn: (() => void) | null = null;
  let ms = 0;
  const clock: Clock = {
    setInterval(f, every) {
      fn = f;
      ms = every;
      return 1;
    },
    clearInterval() {
      fn = null;
    },
  };
  return { clock, tick: () => fn?.(), running: () => fn !== null, every: () => ms };
}


describe('nextBlast', () => {
  test('against the resting white, the first is red, then white is skipped only when it’s the icon', () => {
    let fired = 0;
    let color = RESTING;
    const seen: string[] = [];
    for (let i = 0; i < 6; i++) {
      const next = nextBlast(fired, color);
      fired = next.fired;
      color = next.blast.key;
      seen.push(color);
    }
    expect(seen).toEqual(['red', 'white', 'blue', 'red', 'white', 'blue']);
  });
  test('never fires the icon’s current colour', () => {
    for (let fired = 0; fired < 9; fired++) {
      for (const { key } of BLASTS) expect(nextBlast(fired, key).blast.key).not.toBe(key);
    }
  });
  test('skipping counts as a turn', () => {
    expect(nextBlast(0, 'red')).toEqual({ blast: BLASTS[1], fired: 2 });
    expect(nextBlast(0, 'blue')).toEqual({ blast: BLASTS[0], fired: 1 });
  });
});

describe('cycleColor', () => {
  test('red, white and blue by turns', () => {
    expect([0, 1, 2, 3, 4, 5].map(cycleColor)).toEqual(['red', 'white', 'blue', 'red', 'white', 'blue']);
  });
});

describe('iconHref', () => {
  test('names the static icon for each blast colour', () => {
    for (const { key } of BLASTS) expect(iconHref(key)).toBe(`/favicon-${key}.png`);
  });
});

describe('TabIcon', () => {
  test('white at rest; each blast turns the icon to its own colour; the page’s icon comes back', () => {
    const link = { href: '/favicon.png' };
    const icon = new TabIcon(link, manualClock().clock);
    expect(link.href).toBe(iconHref('white'));
    expect(icon.fire().hex).toBe('#ff3344');
    expect(link.href).toBe(iconHref('red'));
    expect(icon.fire().key).toBe('white');
    expect(link.href).toBe(iconHref('white'));
    icon.dispose();
    expect(link.href).toBe('/favicon.png');
  });

  test('a working rerun cycles every 0.4s, then the icon returns to the last blast’s colour', () => {
    const link = { href: '/favicon.png' };
    const t = manualClock();
    const icon = new TabIcon(link, t.clock);
    icon.fire(); // red
    icon.setWorking(true);
    expect(t.every()).toBe(ICON_CYCLE_MS);
    const cycle = [link.href];
    for (let i = 0; i < 3; i++) {
      t.tick();
      cycle.push(link.href);
    }
    const order: BlastKey[] = ['red', 'white', 'blue', 'red'];
    expect(cycle).toEqual(order.map(iconHref));
    // A blast while cycling takes its turn but doesn't interrupt the cycle.
    expect(icon.fire().key).toBe('white');
    expect(link.href).toBe(iconHref('red'));
    icon.setWorking(true); // already cycling: no restart
    icon.setWorking(false);
    expect(t.running()).toBe(false);
    expect(link.href).toBe(iconHref('white'));
    icon.setWorking(false);
    expect(link.href).toBe(iconHref('white'));
  });

  test('leaving mid-rerun stops the cycle', () => {
    const link = { href: '/favicon.png' };
    const t = manualClock();
    const icon = new TabIcon(link, t.clock);
    icon.setWorking(true);
    icon.dispose();
    expect(t.running()).toBe(false);
    expect(link.href).toBe('/favicon.png');
  });
});
