"""Held-out benchmarks. Only the validation stage imports this module; the
backbone and the agents never do (checked by test_benchmarks_isolated in
tests/test_prereg.py, which greps the package).
"""
from __future__ import annotations

import pandas as pd

from .config import CACHE

CW_STATES = ['CT', 'IL', 'MA', 'MI', 'NY']


def corder_wolbrecht() -> pd.DataFrame:
    b = pd.read_csv(CACHE / 'benchmarks/corder_wolbrecht_turnout_by_sex.csv')
    return b[(b.year == 1920) & b.state.isin(CW_STATES)].set_index('state')

