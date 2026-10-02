"""The page's contract: the bundle the page reads.

tests/fixtures/bundle.example.json is shared with the page's zod schema
(src/lib/simulacra/schemas.ts).
"""
import json
from pathlib import Path

import pytest

from simharness.serialize import Bundle, BundleError

FIXTURE = Path(__file__).resolve().parent / 'fixtures/bundle.example.json'


def test_bundle_contract():
    raw = json.loads(FIXTURE.read_text())
    b = Bundle.from_dict(raw)
    assert b.to_dict() == raw  # nothing dropped, nothing invented
    assert '' in b.runs and set(b.runs) == set(b.tables)
    assert {w.key for w in b.election.whatIfs} == {k for key in b.runs for k in key.split('+') if k}
    assert set(b.ev) == set(b.historyWinner) == {s.code for s in b.runs[''].states}
    assert all(r.winner in ('A', 'B', 'O', None) for r in b.runs.values())
    # A missing or unexpected key is an error, at any depth.
    for broken in ({k: v for k, v in raw.items() if k != 'runs'}, raw | {'extra': 1}):
        with pytest.raises(BundleError):
            Bundle.from_dict(broken)
    bad = json.loads(FIXTURE.read_text())
    bad['runs']['league']['states'][0]['color'] = 'red'
    with pytest.raises(BundleError, match=r"runs\['league'\]\.states\[0\]"):
        Bundle.from_dict(bad)

