"""The page's contract: what serialize emits and the bundle the server reads.

tests/fixtures/bundle.example.json is shared with serve/simulacra.test.ts (zod);
regenerate it with `python3 scripts/harness/bundle_fixture.py`.
"""
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from simharness import serialize
from simharness.config import ROOT
from simharness.serialize import SLICES, Bundle, BundleError, Result

FIXTURE = Path(__file__).resolve().parent / 'fixtures/bundle.example.json'
SERVED = sorted((ROOT / 'serve/bundles').glob('*.json'))


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


def test_served_bundles_parse():
    """Every bundle the server serves fits the contract."""
    if not SERVED:
        pytest.skip('no bundles in serve/bundles/')
    for f in SERVED:
        b = Bundle.from_dict(json.loads(f.read_text()))
        assert b.year == int(f.stem), f


def test_result_matches_serialize():
    """serialize.result plus publish's extras is exactly a Result."""
    raw = json.loads(FIXTURE.read_text())['runs']['league']
    n = 3
    summary = {'ev_point': [300.0, 200.0, 31.0], 'state_winner_point': [0, 1, 0], 'state_margin_point': [5.0, 2.5, 30.0],
               'state_margin_range': [(1.0, 9.0)] * n, 'state_p_flip': [0.1, 0.4, 0.0],
               'ev_range': {'R': (290, 310), 'D': (190, 210), 'O': (31, 31)},
               'draws_won': {'R': 400, 'D': 0, 'O': 0}, 'draws_no_majority': 0, 'draws': 400,
               'popular_point': [10.0, 8.0, 1.0], 'popular_range': [(9, 11), (7, 9), (1, 1)]}
    publish_extras = {k: raw[k] for k in ('assumptions', 'howIGotThis', 'sources', 'confidenceTier', 'confidenceLabel',
                                          'confidenceFlags', 'confidenceReasons', 'evidence', 'mode', 'runId', 'validation',
                                          'cohortEffects')}
    out = serialize.result(names=['NY', 'GA', 'OH'], summary=summary, base_winner=[0, 0, 0], slices_out=raw['slices'],
                           text='t', confidence='low', applied=raw['applied'], extras=publish_extras)
    r = Result.from_dict(json.loads(json.dumps(out, default=float)))
    assert r.winner == 'A' and [s.won for s in r.states] == ['A', 'B', 'A']
    assert set(out) == set(raw)  # the same keys a published result has


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
    synthetic cell table with every group × region × sex, and on every served
    bundle (its state × slice tables against its slices)."""
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
    if not SERVED:
        pytest.skip('no bundles in serve/bundles/ for the published check')
    for f in SERVED:
        b = json.loads(f.read_text())
        for key, result in b['runs'].items():
            by_slice = {}
            for row in b['tables'][key]:
                by_slice[row['slice']] = by_slice.get(row['slice'], 0.0) + row['adults']
            sl = {s['key']: s['adults'] for s in result['slices']}
            assert set(by_slice) == set(sl), (f.name, key)
            for k, adults in sl.items():
                assert abs(by_slice[k] / 1e6 - adults) <= 6e-4, (f.name, key, k)
