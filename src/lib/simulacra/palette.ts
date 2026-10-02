// Chart colour for Simulacra Americana.
//
// The host app's dark mode is a filter over the whole page (invert(1)
// hue-rotate(180deg) saturate(1.5)), and light mode drops it. So a chart
// colour is authored twice: light mode uses the palette's light step as-is;
// dark mode uses the value that filter turns into the palette's dark step
// (solved for, and checked against Chrome's rendered pixels). Everything
// neutral — ink, hairlines, washes — is authored once in light values and
// inverts on its own, like the rest of the page.
//
// Steps are the dataviz reference palette. The page colours the winner and
// the runner-up and folds everyone else into "Other": every era's pair is
// validated (CVD and normal-vision separation, both modes, on this page's
// surfaces), and a third or fourth candidate never needs its own hue.

export type Hue =
  | 'blue'
  | 'orange'
  | 'aqua'
  | 'violet'
  | 'green'
  | 'red'
  | 'other'
  | 'good'
  | 'warning'
  | 'critical';

/** 'k' = black text on screen, 'w' = white. */
type Ink = 'k' | 'w';

// hue: [light step, dark-mode authored, label ink on the fill: light, dark],
// the ink by contrast with the fill.
const HUES: Readonly<Record<Hue, readonly [string, string, Ink, Ink]>> = {
  blue: ['#2a78d6', '#5488c7', 'k', 'k'],
  orange: ['#eb6834', '#d47f5d', 'k', 'k'],
  aqua: ['#1baf7a', '#3d9677', 'k', 'k'],
  violet: ['#4a3aa7', '#716aad', 'w', 'k'],
  green: ['#008300', '#63ba63', 'w', 'w'],
  red: ['#e34948', '#c06b6b', 'k', 'k'],
  // A neutral, authored once and left to invert: charcoal on the light page,
  // a light grey on the dark one — apart from every hue in lightness, so it
  // survives colour blindness beside red and aqua.
  other: ['#4d4c48', '#4d4c48', 'w', 'k'],
  // Status (fixed meaning; always with an icon and a label).
  good: ['#0ca30c', '#3fa43f', 'w', 'w'],
  warning: ['#fab219', '#764600', 'k', 'k'],
  critical: ['#d03b3b', '#f28f8f', 'w', 'w'],
};

/** The colour to author for `hue` in the current mode; no hue → "other". */
export const paint = (hue: Hue | undefined, light: boolean): string => {
  const h = HUES[hue ?? 'other'];
  return light ? h[0] : h[1];
};

/** Label ink to author on a `hue` fill: white or black on screen, whichever reads. */
export function onPaint(hue: Hue | undefined, light: boolean): string {
  const h = HUES[hue ?? 'other'];
  const black = (light ? h[2] : h[3]) === 'k';
  // Dark mode inverts what's authored: black on screen is authored white.
  return black === light ? '#000000' : '#ffffff';
}

/** The party families that own a hue somewhere on the timeline. */
export type Family =
  | 'federalist'
  | 'democratic-republican'
  | 'democratic'
  | 'national-republican'
  | 'whig'
  | 'republican';

interface Era {
  readonly when: (parties: ReadonlySet<Family | null | undefined>) => boolean;
  readonly hues: readonly Hue[];
  readonly own: Readonly<Partial<Record<Family, Hue>>>;
}

// The earliest era: everything before the Democrats, and the fallback.
const FOUNDING: Era = {
  when: () => true,
  hues: ['aqua', 'violet', 'orange'],
  own: { 'democratic-republican': 'aqua', federalist: 'violet' },
};

// Each era's validated triple and the parties that own a hue in it.
const ERAS: readonly Era[] = [
  { when: (p) => p.has('republican'), hues: ['red', 'blue', 'green'], own: { republican: 'red', democratic: 'blue' } },
  {
    when: (p) => p.has('democratic') || p.has('whig') || p.has('national-republican'),
    hues: ['blue', 'orange', 'aqua'],
    own: { democratic: 'blue', whig: 'orange', 'national-republican': 'orange' },
  },
  FOUNDING,
];

export interface HueCandidate {
  readonly key: string;
  readonly party?: Family | null | undefined;
}

/**
 * Hue per candidate key for one election. Parties keep their colour across
 * the timeline (Democrats blue, Republicans red); anyone else takes the era's
 * free hue, largest share first; past three, "other".
 * @param weight e.g. electoral votes by key
 */
export function candidateHues(
  candidates: readonly HueCandidate[] = [],
  weight: Readonly<Record<string, number>> = {},
): Map<string, Hue> {
  const parties = new Set(candidates.map((c) => c.party));
  const era = ERAS.find((e) => e.when(parties)) ?? FOUNDING;
  const order = [...candidates].sort(
    (a, b) => (weight[b.key] ?? 0) - (weight[a.key] ?? 0) || a.key.localeCompare(b.key),
  );
  const out = new Map<string, Hue>();
  const used = new Set<Hue>();
  for (const c of order) {
    const h = c.party ? era.own[c.party] : undefined;
    if (h && !used.has(h)) {
      out.set(c.key, h);
      used.add(h);
    }
  }
  for (const c of order) {
    if (out.has(c.key)) continue;
    const h = era.hues.find((x) => !used.has(x));
    if (h) {
      out.set(c.key, h);
      used.add(h);
    } else out.set(c.key, 'other');
  }
  return out;
}
