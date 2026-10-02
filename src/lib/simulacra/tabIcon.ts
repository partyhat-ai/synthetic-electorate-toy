// The tab icon follows the robot's chest blasts: the colour of the last one
// (white before the first), changing once per blast; red, white and blue by
// turns every ICON_CYCLE_MS while a rerun works, then back to that colour. The
// page's own icon (static/favicon.png) comes back when the page goes.

export type BlastKey = 'red' | 'white' | 'blue';

export interface Blast {
  readonly key: BlastKey;
  /** The shot's colour, #rrggbb. */
  readonly hex: string;
}

/** Red, white and blue, in firing order. */
export const BLASTS: readonly [Blast, Blast, Blast] = [
  { key: 'red', hex: '#ff3344' },
  { key: 'white', hex: '#ffffff' },
  { key: 'blue', hex: '#2f6bff' },
];

/** The icon at rest, before any blast. */
export const RESTING: BlastKey = 'white';

/** How often the icon changes colour while a rerun works, ms. */
export const ICON_CYCLE_MS = 400;

const blastAt = (i: number): Blast => BLASTS[((i % BLASTS.length) + BLASTS.length) % BLASTS.length] ?? BLASTS[0];

/**
 * The blast after `fired` blasts, never in the icon's current colour (so each
 * one visibly changes it): the first is red, against the resting white.
 * Returns the blast and the new count.
 */
export function nextBlast(fired: number, current: BlastKey): { blast: Blast; fired: number } {
  const skip = blastAt(fired).key === current ? 1 : 0;
  return { blast: blastAt(fired + skip), fired: fired + skip + 1 };
}

/** The icon's colour at `step` of the working cycle: red, white, blue, red, … */
export function cycleColor(step: number): BlastKey {
  return blastAt(step).key;
}

/** The tab icon in one blast's colour: static/favicon-<key>.png. */
export function iconHref(key: BlastKey): string {
  return `/favicon-${key}.png`;
}

/** What TabIcon needs of the page's `<link rel="icon">`. */
export interface IconLink {
  href: string;
}

/** Timers, injectable for tests. */
export interface Clock {
  setInterval(fn: () => void, ms: number): number;
  clearInterval(id: number): void;
}

const windowClock: Clock = {
  setInterval: (fn, ms) => window.setInterval(fn, ms),
  clearInterval: (id) => window.clearInterval(id),
};

/** Drives one icon link: blasts set its colour, a working rerun cycles it. */
export class TabIcon {
  #link: IconLink;
  #clock: Clock;
  #original: string;
  #color: BlastKey = RESTING;
  #fired = 0;
  #step = 0;
  #timer: number | null = null;

  constructor(link: IconLink, clock: Clock = windowClock) {
    this.#link = link;
    this.#clock = clock;
    this.#original = link.href;
    link.href = iconHref(RESTING);
  }

  /** The icon's colour now (the last blast's, or white). */
  get color(): BlastKey {
    return this.#color;
  }

  /** The next blast: the icon takes its colour (at once, unless a rerun is cycling it). */
  fire(): Blast {
    const { blast, fired } = nextBlast(this.#fired, this.#color);
    this.#fired = fired;
    this.#color = blast.key;
    if (this.#timer === null) this.#link.href = iconHref(blast.key);
    return blast;
  }

  /** A rerun started (cycle red, white, blue) or stopped (back to the last blast's colour). */
  setWorking(on: boolean): void {
    if (on && this.#timer === null) {
      this.#step = 0;
      this.#tick();
      this.#timer = this.#clock.setInterval(() => this.#tick(), ICON_CYCLE_MS);
    } else if (!on && this.#timer !== null) {
      this.#clock.clearInterval(this.#timer);
      this.#timer = null;
      this.#link.href = iconHref(this.#color);
    }
  }

  #tick(): void {
    this.#link.href = iconHref(cycleColor(this.#step));
    this.#step += 1;
  }

  /** Stops cycling and puts the page's own icon back. */
  dispose(): void {
    if (this.#timer !== null) this.#clock.clearInterval(this.#timer);
    this.#timer = null;
    this.#link.href = this.#original;
  }
}
