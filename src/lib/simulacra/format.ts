// Number formats for Simulacra Americana.
const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });

/** 4100000 → "4.1M"; a missing or non-finite number → "—". */
export const fmtCompact = (n: number | null | undefined): string =>
  n != null && Number.isFinite(n) ? compact.format(n) : '—';

/** 0.523 → "52%"; a missing or non-finite number → "—". */
export const fmtPct = (x: number | null | undefined, digits = 0): string =>
  x != null && Number.isFinite(x) ? `${(x * 100).toFixed(digits)}%` : '—';

/** Points with a sign: 3.25 → "+3.3", −1 → "−1.0"; missing → "—". */
export function fmtPoints(x: number | null | undefined): string {
  if (x == null || !Number.isFinite(x)) return '—';
  const sign = x < 0 ? '−' : '+';
  return `${x === 0 ? '' : sign}${Math.abs(x).toFixed(1)}`;
}
