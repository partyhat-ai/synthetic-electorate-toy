// Number formats for Simulacra Americana.
const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });

/** 4100000 → "4.1M"; a missing or non-finite number → "—". */
export const fmtCompact = (n: number | null | undefined): string =>
  n != null && Number.isFinite(n) ? compact.format(n) : '—';
