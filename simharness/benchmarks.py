"""Held-out benchmarks. Only the validation stages (Run.evaluate, and
Run.verify's Corder–Wolbrecht comparison) import this module; the backbone,
the agents and the publisher never do (checked by test_benchmarks_isolated in
tests/test_prereg.py, which greps the package).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import CACHE
from .evaluate import check

CW_STATES = ['CT', 'IL', 'MA', 'MI', 'NY']


def corder_wolbrecht_any_year() -> pd.DataFrame:
    """Every year and state in the Corder–Wolbrecht file (for `run verify`); empty when it isn't in the cache."""
    f = CACHE / 'benchmarks/corder_wolbrecht_turnout_by_sex.csv'
    return pd.read_csv(f) if f.exists() else pd.DataFrame(columns=['year', 'state'])


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

    # N2 placebo: GA and MS, where women couldn't register in time
    if inp.closed_1920:
        c = fit.cells
        fem_cit = ((c.sex == 'F') & (c.group != 'foreign_white_alien')).to_numpy()
        prow = []
        ok = True
        for s in sorted(inp.closed_1920):
            m = fem_cit & (c.state == s).to_numpy()
            Fc = fit.world.adults[:, m].sum(axis=1)
            W = dg['T20'][idx[s]] - dg['men_turnout_pred'][:, idx[s]] * dg['M20'][:, idx[s]]
            w = W / Fc
            med = float(np.median(w))
            prow.append({'state': s, 'implied_women_turnout': round(med * 100, 1),
                         'lo90': round(float(np.quantile(w, 0.05)) * 100, 1), 'hi90': round(float(np.quantile(w, 0.95)) * 100, 1)})
            ok = ok and abs(med) <= 0.05
        out.append(check('N2', 'Placebo: implied women\'s turnout where women couldn\'t register (GA, MS)', prow, 'within ±5 points of 0', ok,
                         'Documented: franchise/state_franchise_1920.csv women_nov1920_note (NPS).'))
    else:
        out.append(check('N2', 'Placebo (GA, MS)', None, '±5 points', None, 'not run: the registration closure is not documented in the data'))
    return out


def agent_checks(an, fit, run, extras) -> list:
    if not an:
        return [check(i, n, None, t, None, 'not run: no agent answers') for i, n, t in [
            ('N3', 'Agent women\'s turnout vs Corder–Wolbrecht', 'MAE ≤ 10'), ('L1', 'Recall probe', 'reported'),
            ('L2', 'Label swap', '< 20% follow the label'), ('A1', 'Cohort bias', 'reported'),
            ('A2', 'Homogenization index', '≤ 25%'), ('A3', 'Prompt and model sensitivity', 'SD < |effect|; signs agree'),
            ('A4', 'Stereotype audit', '≤ 10%')]]
    out = []
    # N3: agents' stated turnout, women in the C-W states (control, sonnet)
    import json
    agents = json.loads((run.dir / 'agents/agents.json').read_text())
    ans = run.answers()
    cw = corder_wolbrecht()
    rows = []
    for s in CW_STATES:
        pv = [ans[f'control|{a["id"]}|{run.bulk}']['data'].get('p_vote', 0) / 100 for a in agents
              if a['state'] == s and a['sex'] == 'F' and a['group'] != 'foreign_white_alien' and f'control|{a["id"]}|{run.bulk}' in ans]
        if pv:
            c = fit.cells
            f = c[(c.state == s) & (c.sex == 'F')]
            cit = f[f.group != 'foreign_white_alien'].adults20.sum() / f.adults20.sum()
            rows.append({'state': s, 'n': len(pv), 'agents': round(float(np.mean(pv)) * cit * 100, 1),
                         'agents_citizen': round(float(np.mean(pv)) * 100, 1),
                         'corder_wolbrecht': round(float(cw.loc[s, 'women_turnout']) * 100, 1)})
    if rows:
        mae = float(np.mean([abs(r['agents'] - r['corder_wolbrecht']) for r in rows]))
        out.append(check('N3', 'Agents\' stated turnout, women, vs Corder–Wolbrecht', {'mae_points': round(mae, 1), 'rows': rows}, 'MAE ≤ 10 points', mae <= 10,
                         f'{sum(r["n"] for r in rows)} women agents in {len(rows)} of 5 states'))
    else:
        out.append(check('N3', 'Agents\' stated turnout, women, vs Corder–Wolbrecht', None, 'MAE ≤ 10 points', None, 'not run: no women agents drawn in those states'))

    l1 = an['l1']
    out.append(check('L1', 'Recall probe: identifies year / candidates / winner',
                     {'n': l1['n'], 'year': l1['year_rate'], 'candidates': l1['names_rate'], 'winner': l1['winner_rate'],
                      'exposed_cohorts': len(l1['exposed_cohorts'])},
                     'reported; > 50% winner ⇒ memorization-exposed', None,
                     'memorization-exposed nationally' if an['nationally_exposed'] else 'not exposed nationally'))
    l2 = an['l2']
    out.append(check('L2', 'Label swap: choices that follow the label, not the platform', {'n': l2['n'], 'label': l2['label_rate'], 'platform': l2['platform_rate']},
                     '< 20% follow the label', (l2['label_rate'] is not None and l2['label_rate'] < 0.2) if l2['n'] else None,
                     'With the order flipped too, following the display position is the same as following the platform here; the test separates label from platform.'))
    a1 = an['a1']
    big = [x for x in a1 if x['bias_logit'] is not None and abs(x['bias_logit']) > 1.0]
    out.append(check('A1', 'Cohort bias (control vs calibrated backbone, logit)',
                     {'cohorts': len(a1), 'median_abs_bias': round(float(np.median([abs(x['bias_logit']) for x in a1 if x['bias_logit'] is not None])), 3) if a1 else None,
                      'over_1_logit': len(big), 'mean_tvd': round(float(np.mean([x['tvd'] for x in a1])), 3) if a1 else None},
                     'reported; |bias| > 1 ⇒ shrunk', None, f'{len(big)} cohorts shrunk for bias'))
    a2 = an['a2']
    out.append(check('A2', 'Homogenization index', {'index': a2['homogenization_index'], 'eligible_cohorts': a2['eligible_cohorts']},
                     '≤ 25%', (a2['homogenization_index'] <= 0.25) if a2['homogenization_index'] is not None else None))
    for wk, e in an['effects'].items():
        paras = [v['dr'] for v in e['by_paraphrase'].values()]
        sd = float(np.std(paras, ddof=1)) if len(paras) > 1 else None
        shared = e.get('shared_subsample') or {}
        signs = None
        if 'sonnet' in shared and 'opus' in shared:
            signs = bool(np.sign(shared['sonnet']['dr']) == np.sign(shared['opus']['dr']))
        eff = e['national']['dr']['mean']
        ok = (sd is not None and sd < abs(eff) and signs is True) if (sd is not None and signs is not None) else None
        out.append(check(f'A3:{wk}', f'Prompt and model sensitivity, {wk} (two-party logit effect)',
                         {'national_effect': round(eff, 3), 'paraphrase_sd': round(sd, 3) if sd is not None else None,
                          'by_paraphrase': {k: round(v, 3) for k, v in zip(e['by_paraphrase'], paras)},
                          'sonnet_vs_opus': {m: round(v['dr'], 3) for m, v in shared.items()}},
                         'paraphrase SD < |effect| and Sonnet/Opus agree on sign', ok))
    a4 = an['a4']
    out.append(check('A4', 'Stereotype audit: reasons resting on a group label', {'audited': a4['audited'], 'flagged': a4['flagged'], 'rate': a4['rate']},
                     '≤ 10%', a4['rate'] <= 0.10, 'Heuristic first pass (quotes.LABEL_DRIVEN); flagged examples in analysis.json.'))
    return out
