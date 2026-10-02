"""What people typed into the page, and what the robot couldn't model.

    python3 scripts/harness/sessions-report.py                 # everything logged

Reads sessions/requests.jsonl (written by serve/simulacra.js in dev), the
intake queue's outcomes (sessions/queue-done.jsonl) and today's spend
(sessions/spend.jsonl). Clusters are keyword guesses, good enough to pick the
next fix; `run whatif` does the real reading.
"""
import argparse
import collections
import json
import re
import time
from pathlib import Path

SESSIONS = Path(__file__).resolve().parents[2] / 'sessions'

KINDS = [
    ('candidate or entrant', r'\b(ran|runs?|running|candidate|independent|third[- ]party|nominee|nominated|ticket|instead of)\b'),
    ('franchise change', r'\b(vote[ds]?|voting|suffrage|franchise|ballot|poll tax|literacy|enfranchis|disenfranchis|allowed to)\b'),
    ('event or scandal', r'\b(scandal|war|strike|riot|died|death|assassinat|depression|crash|panic|flu|pandemic|lynch|bomb|revealed)\b'),
    ('policy', r'\b(prohibition|tariff|tax|law|act|policy|treaty|bonus|union|wage|price|immigration quota)\b'),
    ('demographic shift', r'\b(population|migration|migrat|immigrants?|moved|more people|fewer|census|birth)\b'),
    ("another year's issue", r'\b(1[789]\d\d|20[0-2]\d)\b'),
]


def kind(text):
    t = text.lower()
    for name, pat in KINDS:
        if name == "another year's issue":
            if any(y != '1920' for y in re.findall(pat, t)):
                return name
        elif re.search(pat, t):
            return name
    return 'other'


def rows(name, since):
    p = SESSIONS / name
    if not p.exists():
        return []
    out = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    return [r for r in out if not since or r.get('ts', '') >= since]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--since', default='', help='ISO time; only requests at or after it')
    a = ap.parse_args()
    reqs = rows('requests.jsonl', a.since)
    typed = [r for r in reqs if (r.get('text') or '').strip()]
    unknown = [r for r in typed if r.get('unknown')]
    print(f'requests: {len(reqs)} ({len(typed)} with typed text)')
    print(f'unknown: {len(unknown)}' + (f' ({len(unknown) / len(typed):.0%} of typed)' if typed else ''))
    missing = [r for r in reqs if not r.get('exists')]
    if missing:
        print(f'combinations not computed: {len(missing)} ({", ".join(sorted({r["combo"] for r in missing})[:6])})')
    clusters = collections.defaultdict(list)
    for r in unknown:
        clusters[kind(r['unknown'])].append(r['unknown'])
    if clusters:
        print('\nunknowns by kind:')
        for k, v in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
            print(f'  {len(v):3d}  {k}: ' + '; '.join(f'"{t}"' for t, _ in collections.Counter(v).most_common(3)))
    print('\ntop typed texts:')
    for t, n in collections.Counter(r['text'].strip().lower() for r in typed).most_common(10):
        mark = '?' if any(r.get('unknown') and r['text'].strip().lower() == t for r in typed) else ' '
        print(f'  {n:3d} {mark} {t}')
    done = rows('queue-done.jsonl', a.since)
    if done:
        print('\nintake outcomes:')
        for r in done[-10:]:
            print(f'  {r["status"]:13s} {r.get("key") or "":28s} ${r.get("dollars") or 0:<7} "{r["text"]}"')
    day = time.strftime('%Y-%m-%d')
    spend = [r for r in rows('spend.jsonl', '') if r['day'] == day]
    if spend:
        by = collections.Counter()
        for r in spend:
            by[r['stage']] += r['dollars']
        print(f'\nspent today: ${sum(by.values()):.3f} (' + ', '.join(f'{k} ${v:.3f}' for k, v in by.most_common()) + ')')


if __name__ == '__main__':
    main()
