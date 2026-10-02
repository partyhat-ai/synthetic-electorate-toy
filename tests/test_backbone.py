"""The statistical backbone's building blocks (stats.py)."""
import numpy as np

from simharness import stats


def test_ipf_hits_margins():
    rng = np.random.default_rng(0)
    seed = rng.uniform(0.5, 2, (3, 4, 2))
    m0 = np.array([10., 20., 30.])
    m12 = rng.uniform(1, 5, (4, 2))
    m12 *= m0.sum() / m12.sum()
    t = stats.ipf(seed, {(0,): m0, (1, 2): m12})
    assert np.allclose(t.sum(axis=(1, 2)), m0)
    assert np.allclose(t.sum(axis=0), m12)


def test_apportionment_totals():
    pops = {'A': 1000, 'B': 2500, 'C': 400, 'D': 9100}
    for f in (stats.huntington_hill, stats.webster):
        a = f(pops, 20)
        assert sum(a.values()) == 20 and min(a.values()) >= 1
    assert stats.huntington_hill(pops, 20)['D'] > stats.huntington_hill(pops, 20)['A']
