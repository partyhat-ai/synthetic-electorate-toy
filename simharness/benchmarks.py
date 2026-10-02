"""Held-out benchmarks. Only the validation stage (Run.evaluate) imports this
module; the backbone and the agents never do (checked by
test_benchmarks_isolated in tests/test_prereg.py, which greps the package).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import CACHE
from .evaluate import check

CW_STATES = ['CT', 'IL', 'MA', 'MI', 'NY']


def corder_wolbrecht() -> pd.DataFrame:
    b = pd.read_csv(CACHE / 'benchmarks/corder_wolbrecht_turnout_by_sex.csv')
    return b[(b.year == 1920) & b.state.isin(CW_STATES)].set_index('state')


def natural_experiment(fit, inp, extras) -> list:
    dg = fit.diagnostics
    states = dg['states']
    idx = {s: i for i, s in enumerate(states)}
    cw = corder_wolbrecht()
    # Corder–Wolbrecht's "eligible" counts are all adults 21+ (they equal the
    # census 21+ totals, non-citizens included), so the like-for-like
    # comparison divides the backbone's women's votes by all women 21+. The
    # citizen-denominator rate is reported alongside (`backbone_citizen`).
    c = fit.cells
    all_f = np.zeros((fit.world.adults.shape[0], len(states)))
    fem = (c.sex == 'F').to_numpy()
    sidx = np.array([idx[s] for s in c.state])
    np.add.at(all_f, (slice(None), sidx[fem]), fit.world.adults[:, fem])
    wt = dg['votes_F'] / np.maximum(all_f, 1)
    wt_cit = dg['votes_F'] / np.maximum(dg['F20'], 1)
    rows, inside = [], []
    for s in CW_STATES:
        d = wt[:, idx[s]]
        lo, hi = np.quantile(d, 0.05), np.quantile(d, 0.95)
        est = float(cw.loc[s, 'women_turnout'])
        rows.append({'state': s, 'backbone': round(float(np.median(d)) * 100, 1), 'lo90': round(lo * 100, 1),
                     'hi90': round(hi * 100, 1), 'corder_wolbrecht': round(est * 100, 1),
                     'cw_lo95': round(float(cw.loc[s, 'women_turnout_lo95']) * 100, 1),
                     'cw_hi95': round(float(cw.loc[s, 'women_turnout_hi95']) * 100, 1),
                     'backbone_citizen': round(float(np.median(wt_cit[:, idx[s]])) * 100, 1),
                     'method': 'ratio (women voted in 1916)' if s in inp.women16 else 'residual (1916 men-only)'})
        inside.append(lo <= est <= hi)
    mae = float(np.mean([abs(r['backbone'] - r['corder_wolbrecht']) for r in rows]))
    cover = float(np.mean(inside))
    out = [check('N1', 'Backbone women\'s turnout vs Corder–Wolbrecht (1920)', {'mae_points': round(mae, 1), 'coverage_90': cover, 'rows': rows},
                 'MAE ≤ 8 points and ≥ 70% inside the 90% interval', mae <= 8 and cover >= 0.7)]

    return out
