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


def test_corder_wolbrecht_is_held_out_only_where_no_prior_knot_uses_it():
    """DISCLOSURES A11: a general_fit year interpolating from a Corder–Wolbrecht knot isn't scored against it."""
    from simharness.backbone import CW_PRIOR_KNOTS, cw_held_out
    assert CW_PRIOR_KNOTS == (1928, 1940)
    informed = [y for y in range(1916, 1957, 4) if not cw_held_out(y, 'general_fit')]
    assert informed == [1924, 1928, 1932, 1936, 1940, 1944, 1948]
    # 1920 is the natural-experiment fit and 1924 is carried forward from it: no prior knots.
    assert cw_held_out(1920, 'fit') and cw_held_out(1924, 'carry_forward') and cw_held_out(1928, None)
