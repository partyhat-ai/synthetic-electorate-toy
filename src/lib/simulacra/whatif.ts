// The what-if section's pure parts (WhatIf.svelte and its pieces): what the
// robot's bubble carries, the kinds' wording, and how a step's line is set.
import type { Interview, Kind, Reading, Step, WhatIf } from './schemas';

/** A button in the bubble; `key` comes back through onaction. */
export interface Action {
  readonly key: string;
  readonly label: string;
  readonly primary?: boolean;
}

/** What a rerun drew on, for the bubble's Sources. */
export interface BubbleSources {
  /** The dated newspapers in the voters' briefs. */
  readonly reading: readonly Reading[];
  /** The research behind each applied what-if. */
  readonly research: readonly { readonly when: string; readonly text: string }[];
  /** The data, one title per row. */
  readonly data: readonly string[];
}

/**
 * What the robot says. quote / by: someone from a group, in their own words;
 * steps: the robot's working, shown above what it says; interview and
 * sources: shown only while the bubble is opened (More).
 */
export interface Message {
  readonly text?: string;
  readonly detail?: string;
  readonly quote?: string;
  readonly by?: string;
  readonly steps?: readonly Step[] | null;
  readonly actions?: readonly Action[];
  readonly busy?: boolean;
  readonly interview?: Interview | null;
  readonly sources?: BubbleSources | null;
}

/** A what-if's kind, in the chips' tooltips. */
export const KIND_LABEL: Readonly<Partial<Record<Kind, string>>> = {
  franchise: 'Who can vote',
  population: 'Who lives where',
  issue: 'What people care about',
};

/** Whether a what-if reaches the open group (no group open: every one does). */
export const reaches = (w: Pick<WhatIf, 'slices'>, slice: string | null): boolean =>
  !slice || !w.slices.length || w.slices.includes(slice);

const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

/**
 * A step's "Label: text" (or "Label (aside): text") as a row's label and
 * text; the aside leads the text. No label, the text runs the full row.
 */
export function splitStep(t = ''): { readonly label?: string; readonly body: string } {
  const m = /^([A-Z][^:“”"()]{1,44}?)(?:\s*\(([^()]*)\))?:\s+([\s\S]+)$/.exec(t);
  const label = m?.[1];
  const body = m?.[3];
  if (!label || body === undefined) return { body: t };
  const aside = m[2];
  return { label, body: aside ? `${cap(aside)}. ${cap(body)}` : cap(body) };
}

/** A newspaper's date as the key column shows it: "Oct 1". */
export const day = (iso: string): string =>
  new Date(`${iso}T12:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

/** How many different people an interview heard. */
export const peopleIn = (iv: Interview): number =>
  new Set(iv.byWhatIf.flatMap((w) => w.answers.map((a) => a.name + a.line))).size;
