"""The page's contract: what serialize emits and the bundle the page reads.

tests/fixtures/bundle.example.json is shared with the page's zod schema
(src/lib/simulacra/schemas.ts).
"""
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from simharness import serialize
from simharness.serialize import SLICES, Bundle, BundleError

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


def _synthetic_fit(rng):
    """Every combination of the attributes slice_of reads, each in two states."""
    rows = [{'state': st, 'group': g, 'south': south, 'sex': sx}
            for st, south in (('NY', False), ('IL', False), ('GA', True), ('TX', True))
            for g in ('native_white', 'foreign_white_naturalized', 'foreign_white_alien', 'black', 'other')
            for sx in 'MF']
    cells = pd.DataFrame(rows)
    n = len(cells)
    share = rng.dirichlet([3, 3, 1], size=(2, n))
    world = SimpleNamespace(adults=rng.uniform(5e4, 9e5, (2, n)), can=rng.uniform(0, 1, (2, n)),
                            t=rng.uniform(0.2, 0.9, (2, n)), share=share)
    return SimpleNamespace(cells=cells), world


def test_slices_partition_adults():
    """The page's slices are a partition: their adults sum to every adult 21+,
    and each slice's barred + home + A + B + O is all of it. Checked on a
    synthetic cell table with every group × region × sex."""
    rng = np.random.default_rng(7)
    fit, world = _synthetic_fit(rng)
    keys = fit.cells.apply(serialize.slice_of, axis=1)
    assert set(keys) == {k for k, _ in SLICES}
    for point in (0, 1):
        out = serialize.slices(fit, world, point, {})
        assert len({s['key'] for s in out}) == len(out)
        total = world.adults[point].sum()
        assert abs(sum(s['adults'] for s in out) * 1e6 - total) <= 0.0005e6 * len(out)
        for s in out:
            assert abs(s['barred'] + s['home'] + s['A'] + s['B'] + s['O'] - 1) < 5e-4 * 5
