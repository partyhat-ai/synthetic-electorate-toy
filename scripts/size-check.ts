// Fails when any tracked source file is over the line limit.
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

const LIMIT = 1000;
const SOURCE = /\.(ts|svelte|js|mjs|py|css)$/;

const files = execFileSync('git', ['ls-files', '--cached', '--others', '--exclude-standard'], { encoding: 'utf8' })
  .split('\n')
  .filter((f) => SOURCE.test(f));

const over = files
  .map((f) => ({ f, n: readFileSync(f, 'utf8').split('\n').length }))
  .filter(({ n }) => n > LIMIT);

for (const { f, n } of over) console.error(`${f}: ${n} lines (limit ${LIMIT})`);
if (over.length > 0) process.exit(1);
console.log(`size: ${files.length} files, none over ${LIMIT} lines`);
