// The what-if section's pure parts (WhatIf.svelte and its pieces): what the
// robot's bubble carries and the kinds' wording.
import type { Kind, WhatIf } from './schemas';

/** A button in the bubble; `key` comes back through onaction. */
export interface Action {
  readonly key: string;
  readonly label: string;
  readonly primary?: boolean;
}

/** What the robot says. quote / by: someone from a group, in their own words. */
export interface Message {
  readonly text?: string;
  readonly detail?: string;
  readonly quote?: string;
  readonly by?: string;
  readonly actions?: readonly Action[];
  readonly busy?: boolean;
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
