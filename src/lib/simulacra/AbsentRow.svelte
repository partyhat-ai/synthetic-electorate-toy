<script lang="ts">
  // A group the year has no simulation for, held in its usual place on a
  // narrow window so every year shows five rows (absentGroups in groups.ts):
  // its name, why it's missing, and a faint dashed rule where SliceRow's dots
  // go. Laid out as SliceRow's head, so it's as tall; nothing to tap or drag.
  import type { Absent } from './groups';

  let { absent }: { absent: Absent } = $props();

  const N = 50; // = SliceRow's dots, so the rule spans the same width
</script>

<div class="row" role="group" aria-label="{absent.label}: {absent.why}">
  <div class="head">
    <span class="who">
      <span class="label">{absent.label}</span>
      <span class="cap">{absent.why}</span>
    </span>
    <svg class="strip" viewBox="0 0 {N * 10} 10" preserveAspectRatio="xMinYMid meet" aria-hidden="true">
      <line x1="2" y1="5" x2={N * 10 - 2} y2="5" />
    </svg>
  </div>
</div>

<style>
  /* = SliceRow's narrow head (≤700px: the strip under the name), quieter. */
  .row { position: relative; border-radius: 12px; }
  .head {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    row-gap: 8px;
    align-items: center;
    min-height: 42px;
    padding: 3px 10px;
  }
  .who { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .label { font-size: 14px; font-weight: 600; line-height: 1.25; color: rgba(0, 0, 0, 0.45); }
  .cap { font-size: 12px; color: rgba(0, 0, 0, 0.45); }
  .strip { width: 100%; height: auto; display: block; overflow: visible; }
  .strip line { stroke: rgba(0, 0, 0, 0.18); stroke-width: 1.2; stroke-dasharray: 4 6; stroke-linecap: round; }
  /* 701-760px: SliceRow sets its dots beside the name; so does this. */
  @media (min-width: 701px) {
    .head { grid-template-columns: minmax(160px, 212px) minmax(0, 1fr) 124px; gap: 16px; }
  }
</style>
