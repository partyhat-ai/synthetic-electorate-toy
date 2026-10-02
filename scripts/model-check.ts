// Prints the sample model's outcome for every what-if of every story
// election (src/lib/simulacra/stories.ts), to check the model outside the
// page: history's electoral vote, then each what-if's.
//   pnpm dlx tsx scripts/model-check.ts
import { electionOf } from '../src/lib/simulacra/history';
import { _model } from '../src/lib/simulacra/sample';
import { STORIES } from '../src/lib/simulacra/stories';

const ev = (r: { ev: { A: number; B: number; O: number } }) => `${r.ev.A}–${r.ev.B}${r.ev.O ? `–${r.ev.O}` : ''}`;

for (const year of Object.keys(STORIES).map(Number)) {
  const e = electionOf(year);
  const history = _model.rerun(year);
  if (!e || !history) continue;
  const [a, b] = e.candidates;
  console.log(`\n${year}  ${a.short} over ${b?.short ?? 'no one'}: ${ev(history)} as it happened`);
  for (const w of _model.whatIfsFor(year)) {
    const r = _model.rerun(year, [w.key]);
    if (!r) continue;
    const flips = r.states.filter((s) => s.flipped).length;
    const winner = r.winner ? (e.candidates.find((c) => c.key === r.winner)?.short ?? 'Others') : 'no majority';
    console.log(`  ${w.key.padEnd(14)} ${ev(r).padEnd(12)} ${winner.padEnd(12)} ${String(flips).padStart(2)} flipped  (${r.confidence})`);
  }
}
