"""Benchmark isolation and the evaluate-stage checks (EVAL.md)."""
import re
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

import simharness
from simharness import evaluate
from simharness.stats import expit, logit

PKG = Path(simharness.__file__).resolve().parent


def test_benchmarks_isolated():
    """Only evaluate-stage code may read held-out benchmarks: no other module
    imports benchmarks.py or opens a path under benchmarks/."""
    bad = re.compile(r"import\s+benchmarks|from\s+\.\s+import\s+[^\n]*\bbenchmarks\b|['\"]benchmarks/")
    for f in PKG.glob('*.py'):
        if f.name == 'benchmarks.py':
            continue
        hits = [l.strip() for l in f.read_text().splitlines() if bad.search(l)]
        if f.name == 'pipeline.py':
            # inside Run.verify (Corder–Wolbrecht) and Run.evaluate only
            assert [h.split('#')[0].strip() for h in hits] == ['from . import benchmarks'] * 2, hits
        else:
            assert not hits, (f.name, hits)


def _holdout_world():
    """Eight states, two draws' worth of identical numbers. The training old
    states share one κ = 0.3 exactly, so κ's spread is zero and every quantity
    below is deterministic. CA is a held-out old state (women voted in 1916)."""
    D = 20
    states = ['WA', 'KS', 'CA', 'IL', 'PA', 'MN', 'OH', 'GA', 'AL', 'TX']
    old = {'WA', 'KS', 'CA'}
    south = {'GA', 'AL', 'TX'}
    holdout = ['CA', 'OH', 'TX']
    kappa = 0.3
    t16 = {'WA': 400., 'KS': 500., 'CA': 450., 'IL': 300., 'PA': 280., 'MN': 320., 'OH': 310., 'GA': 120., 'AL': 110., 'TX': 130.}
    e16 = np.full(len(states), 1000.)
    e20 = np.array([1000., 1000., 1200., 1000., 1000., 1000., 1000., 1000., 1000., 1000.])
    t20 = np.array([expit(logit(t16[s] / 1000.) + kappa) * e20[i] if s in old else
                    (180. if s in south else 520. + 10 * i) for i, s in enumerate(states)])
    adults20 = {s: e20[i] / 2 for i, s in enumerate(states)}
    cells = pd.DataFrame([{'state': s, 'sex': sx, 'group': 'native_white', 'adults20': adults20[s], 'adults16': 500.}
                          for s in states for sx in 'MF'])
    rep = lambda v: np.repeat(np.asarray(v, float)[None, :], D, 0)  # noqa: E731
    dg = {'states': states, 'old_states': sorted(old),
          'E16': rep(e16), 'E20': rep(e20), 'T16': np.array([t16[s] for s in states]), 'T20': t20,
          'M20': rep([600.] * len(states)), 'F20': rep([600.] * len(states)),
          'm16': rep([0.2 if s == 'CA' else 0.5 for s in states]),
          'votes_F': rep([150. + 7 * i for i in range(len(states))])}
    fit = SimpleNamespace(diagnostics=dg, cells=cells,
                          world=SimpleNamespace(adults=rep(cells.adults20.to_numpy())))
    r16 = [0.55, 0.45, 0.48, 0.52, 0.6, 0.5, 0.53, 0.25, 0.2, 0.3]
    r20 = [0.62, 0.66, 0.70, 0.60, 0.68, 0.59, 0.61, 0.32, 0.27, 0.36]
    returns = pd.DataFrame({'R16': [x * 1000 for x in r16], 'D16': [(1 - x) * 1000 for x in r16],
                            'R20': [x * 1000 for x in r20], 'D20': [(1 - x) * 1000 for x in r20]}, index=states)
    inp = SimpleNamespace(returns=returns, women16=old, closed_1920=set(),
                          ev=pd.Series({s: 5 + i for i, s in enumerate(states)}))
    return fit, inp, holdout, kappa, t16, e20, D


def test_old_suffrage_states_use_projected_1916():
    """B2 for an old suffrage state projects its 1916 turnout per eligible adult
    (women included) by κ; it doesn't rebuild 1920 from men's-only 1916 turnout
    (EVAL.md, deviations)."""
    fit, inp, holdout, kappa, t16, e20, D = _holdout_world()
    ho = evaluate.holdout(fit, inp, holdout, D, 1920)
    row = next(r for r in ho['rows'] if r['state'] == 'CA')
    adults = e20[2]  # CA: two cells of e20 / 2 adults each
    projected = expit(logit(t16['CA'] / 1000.) + kappa) * e20[2] / adults * 100
    assert row['turnout_backbone'] == round(projected, 1)
    # The men-only reading (m16 = 0.2, then women at ρ ∈ [0.05, 1.5] of men's rate) can't reach it.
    m20 = expit(logit(0.2) + kappa)
    men_only_max = m20 * 600 * (1 + 1.5) / adults * 100
    assert projected > men_only_max + 5
    assert {c['id'] for c in ho['checks']} == {'B1', 'B2', 'B3', 'B4', 'B5'}
