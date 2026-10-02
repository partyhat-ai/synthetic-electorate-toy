"""Agent cohorts, invented people and their quotes (cohorts.py, quotes.py, scenario.py)."""
import threading

import pandas as pd

from simharness import cohorts
from simharness.quotes import deblind
from simharness.scenario import clean_position


def test_deblind():
    assert deblind('I will vote for Candidate K, not M.', {'K': 'Harding', 'M': 'Cox'}) == 'I will vote for Harding, not Cox.'
    assert deblind('K’s men', {'K': 'Harding'}) == 'K’s men'


def test_clean_position_strips_notes_and_names():
    assert clean_position('Backs the League (inferred: no record).') == 'Backs the League.'
    assert 'Wilson' not in clean_position('Opposes President Wilson on the treaty.')


def _build_with_timeout(cells, seconds=20, **kw):
    out = {}
    t = threading.Thread(target=lambda: out.setdefault('r', cohorts.build(cells, **kw)), daemon=True)
    t.start()
    t.join(seconds)
    assert not t.is_alive(), f'cohorts.build did not finish in {seconds}s with {kw}'
    return out['r']


def test_cohort_merge_terminates_on_degenerate_config():
    """No merge can bring the count under the cap (cap 0; every cohort under
    min_share; a region with no neighbour): the merge folds everything into
    the national cohorts and stops, rather than looping."""
    rows = [{'state': st, 'region': region, 'sex': sex, 'group': group, 'adults20': 1000.0}
            for st, region in (('NY', 'northeast'), ('GA', 'south'), ('XX', 'nowhere'))
            for sex in 'MF' for group in ('native_white', 'black', 'other')]
    cells = pd.DataFrame(rows)
    out, cell_to = _build_with_timeout(cells, cap=0, min_share=1.0, year=1920)
    assert set(cell_to) == set(cells.index)  # every cell lands in exactly one cohort
    assert len(out) == 6  # one national cohort per (sex, group): nothing left to merge
    assert all(c['region'] == 'mixed' for c in out.values())
    assert sum(c['adults'] for c in out.values()) == cells.adults20.sum()


def test_cohort_merge_only_national_cells():
    """Cells already national can't merge: the loop has no keys and stops at once."""
    cells = pd.DataFrame([{'state': 'NY', 'region': 'national', 'sex': s, 'group': 'native_white', 'adults20': 10.0} for s in 'MF'])
    out, _ = _build_with_timeout(cells, cap=1, min_share=1.0, year=1920)
    assert len(out) == 2
