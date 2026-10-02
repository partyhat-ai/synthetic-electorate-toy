"""Trim a published bundle into the shared contract example.

    python3 scripts/harness/bundle_fixture.py            # serve/bundles/1920.json → tests/fixtures/bundle.example.json

The Python (serialize.Bundle) and TypeScript (zod) sides both test against the
output, so it keeps every key a real bundle has and only cuts the volume: four
states, three what-if combinations plus history, two voters per combination,
two interviews, two newspaper items and one finding per evidence entry.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'serve/bundles/1920.json'
OUT = ROOT / 'tests/fixtures/bundle.example.json'
STATES = ['GA', 'NY', 'OH', 'TN']
KEEP = ['league', 'no-19th']
COMBOS = ['', 'league', 'no-19th', 'league+no-19th']


def trim_evidence(items: list) -> list:
    return [e | {'findings': e['findings'][:1]} for e in items]


def trim_result(r: dict) -> dict:
    return r | {'states': [s for s in r['states'] if s['code'] in STATES],
                'sources': r['sources'][:3], 'evidence': trim_evidence(r['evidence']),
                'cohortEffects': r['cohortEffects'][:2]}


def main() -> None:
    b = json.loads(SRC.read_text())
    out = {
        'year': b['year'],
        'runId': b['runId'],
        'election': {'slices': b['election']['slices'],
                     'whatIfs': [w for w in b['election']['whatIfs'] if w['key'] in KEEP]},
        'runs': {k: trim_result(b['runs'][k]) for k in COMBOS},
        'tables': {k: [r for r in b['tables'][k] if r['state'] in STATES] for k in COMBOS},
        'voters': {k: dict(list(b['voters'][k].items())[:2]) for k in ['', *KEEP] if k in b['voters']},
        'interviews': {'questions': b['interviews']['questions'],
                       'byWhatIf': {k: v[:2] for k, v in b['interviews']['byWhatIf'].items() if k in KEEP}},
        'ev': {s: b['ev'][s] for s in STATES},
        'historyWinner': {s: b['historyWinner'][s] for s in STATES},
        'words': [w for w in b['words'] if w['key'] in KEEP],
        'pre': b['pre'],
        'told': {k: v for k, v in b['told'].items() if k in KEEP},
        'reading': b['reading'][:2],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    print(f'{OUT.relative_to(ROOT)}: {OUT.stat().st_size} bytes', file=sys.stderr)


if __name__ == '__main__':
    main()
