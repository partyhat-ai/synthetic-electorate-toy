"""Paired control/counterfactual answers → per-cohort effects on the backbone.

For agent i in cohort k, the same persona, seed, paraphrase and model answer
the control brief (the world as it was) and the counterfactual brief (the
world with one settled fact changed). The counterfactual effect is the
within-cohort difference, on the logit scale:

    Δt_k = logit(E[p_vote | cf])  − logit(E[p_vote | control])
    Δr_k = logit(R2 | cf)         − logit(R2 | control)
    Δo_k = logit(O  | cf)         − logit(O  | control)

where R2 is the Republican share of the two-party vote the cohort's agents
expect to cast (Σ p_vote·p_R / Σ p_vote·(p_R+p_D)) and O the minor-party share
of all votes. A bias common to both arms (the model knowing who won, a lean
in the model) cancels in the difference; what doesn't cancel is measured by
the control's distance from the calibrated backbone:

    b_k = logit(R2 | control) − logit(r_k backbone)

and the effect is shrunk by the pre-registered rule (METHOD.md, shrinkage).
"""
from __future__ import annotations

import numpy as np

from .stats import logit

N0 = 8.0          # pre-registered pseudo-count
BIAS_SCALE = 1.0  # pre-registered logit scale for bias shrinkage


def normalize(ans: dict, label_to_party: dict) -> dict | None:
    """One structured answer → {p_vote, R, D, O, choice, able} in party terms."""
    if not ans:
        return None
    able = ans.get('able_to_vote', 'yes')
    pv = max(0.0, min(1.0, float(ans.get('p_vote', 0)) / 100))
    if able == 'no':
        pv = 0.0
    pc = ans.get('p_choice') or {}
    shares = {'R': 0.0, 'D': 0.0, 'O': 0.0}
    for label, v in pc.items():
        party = label_to_party.get(label, 'O') if label != 'other' else 'O'
        shares[party] += max(0.0, float(v))
    tot = sum(shares.values())
    if tot <= 0:
        # An answer with no leanings is kept for turnout only.
        shares = {'R': np.nan, 'D': np.nan, 'O': np.nan}
    else:
        shares = {k: v / tot for k, v in shares.items()}
    c = ans.get('choice', 'none')
    choice = 'home' if (c == 'none' or pv < 0.5) else ('O' if c == 'other' else label_to_party.get(c, 'O'))
    if able == 'no':
        choice = 'barred'
    return {'p_vote': pv, **shares, 'choice': choice, 'able': able}


def cohort_stats(rows: list[dict]) -> dict:
    pv = np.array([r['p_vote'] for r in rows])
    R = np.array([r['R'] for r in rows])
    D = np.array([r['D'] for r in rows])
    O = np.array([r['O'] for r in rows])
    ok = ~np.isnan(R)
    w = pv[ok]
    # Half-count smoothing (Jeffreys-style): a cohort of four who all say 0
    # can't produce an infinite logit difference.
    turnout = float((pv.sum() + 0.5) / (len(pv) + 1)) if len(pv) else np.nan
    if w.sum() <= 0.05:
        return {'turnout': turnout, 'R2': np.nan, 'O': np.nan, 'n': len(rows)}
    r_votes, d_votes, o_votes = (w * R[ok]).sum(), (w * D[ok]).sum(), (w * O[ok]).sum()
    return {
        'turnout': turnout,
        'R2': float((r_votes + 0.5) / (r_votes + d_votes + 1)),
        'O': float((o_votes + 0.5) / (r_votes + d_votes + o_votes + 1)),
        'n': len(rows),
    }


def diff(cf: dict, ctl: dict) -> dict:
    out = {}
    for key, name in (('turnout', 'dt'), ('R2', 'dr'), ('O', 'do')):
        a, b = cf.get(key), ctl.get(key)
        out[name] = float(logit(a) - logit(b)) if (a is not None and b is not None and not np.isnan(a) and not np.isnan(b)) else 0.0
    return out


def floor_spread(boot: dict, point: dict, pairs: dict, draws: int, rng: np.random.Generator) -> dict:
    """D33: who was interviewed is part of the uncertainty. Resampling a cohort's own one or
    two people says almost nothing about the people who might have been drawn instead (one
    person resampled is always that person: no spread at all). So each cohort's draws get at
    least the spread of a mean of n people, with the person-to-person spread estimated from
    every pair in the run: sd_k >= s / sqrt(n_k), where s is the national bootstrap sd
    times sqrt(N). Draws keep their shape where they have one; otherwise normal noise."""
    rows = [(p[0], p[1]) for ps in pairs.values() for p in ps if p[0] and p[1]]
    N = len(rows)
    if N < 2:
        return boot
    nat = {'dt': np.empty(draws), 'dr': np.empty(draws), 'do': np.empty(draws)}
    for j in range(draws):
        s = rng.choice(N, size=N, replace=True)
        dd = diff(cohort_stats([rows[i][1] for i in s]), cohort_stats([rows[i][0] for i in s]))
        for key in nat:
            nat[key][j] = dd[key]
    out = {}
    for k, bd in boot.items():
        n = max(1, point[k]['n'])
        out[k] = {}
        for key, d in bd.items():
            target = float(np.std(nat[key])) * np.sqrt(N / n)
            sd, mu = float(np.std(d)), float(point[k][key])
            if sd >= target or target <= 0:
                out[k][key] = d
            elif sd > 1e-9:
                out[k][key] = mu + (d - float(np.mean(d))) * (target / sd)
            else:
                out[k][key] = mu + rng.normal(0.0, target, len(d))
    return out


def effects(pairs: dict, backbone_r2: dict, region_of: dict, draws: int, rng: np.random.Generator,
            exposed: set | None = None, weights: dict | None = None, floor: bool = False) -> dict:
    """pairs: {cohort: [(control_row, cf_row, paraphrase, model), ...]}.
    floor: widen each cohort's draws to the sampling spread of who was interviewed (D33;
    compiled what-ifs only, so pre-registered numbers are unchanged).

    Returns {'cohorts': {k: {...point estimates, bias, weight, draws: {dt, dr, do: [draws]}}},
             'national': {...}, 'regions': {...}}.
    """
    exposed = exposed or set()
    point, boot = {}, {}
    for k, ps in pairs.items():
        ctl = [p[0] for p in ps if p[0] and p[1]]
        cf = [p[1] for p in ps if p[0] and p[1]]
        if not ctl:
            continue
        c_stats, f_stats = cohort_stats(ctl), cohort_stats(cf)
        d = diff(f_stats, c_stats)
        bias = float(logit(c_stats['R2']) - logit(backbone_r2[k])) if not np.isnan(c_stats['R2']) and k in backbone_r2 else 0.0
        point[k] = {'control': c_stats, 'counterfactual': f_stats, **d, 'bias': bias, 'n': len(ctl)}
        idx = np.arange(len(ctl))
        bd = {'dt': np.empty(draws), 'dr': np.empty(draws), 'do': np.empty(draws)}
        for j in range(draws):
            s = rng.choice(idx, size=len(idx), replace=True)
            dd = diff(cohort_stats([cf[i] for i in s]), cohort_stats([ctl[i] for i in s]))
            for key in bd:
                bd[key][j] = dd[key]
        boot[k] = bd

    if floor:
        boot = floor_spread(boot, point, pairs, draws, rng)
    national_bias = float(np.mean([v['bias'] for v in point.values()])) if point else 0.0

    def weight(n, bias):
        return (n / (n + N0)) * (1.0 / (1.0 + (bias / BIAS_SCALE) ** 2))

    # National effect: adult-weighted mean of cohort effects (per draw).
    ks = list(point)
    wts = np.array([(weights or {}).get(k, 1.0) for k in ks], float)
    nat = {key: np.average([boot[k][key] for k in ks], axis=0, weights=wts) if ks else np.zeros(draws) for key in ('dt', 'dr', 'do')}
    regions = {}
    for r in sorted({region_of[k] for k in ks}):
        rk = [k for k in ks if region_of[k] == r]
        n_r = sum(point[k]['n'] for k in rk)
        b_r = float(np.mean([point[k]['bias'] for k in rk]))
        w_r = weight(n_r, b_r)
        rw = np.array([(weights or {}).get(k, 1.0) for k in rk], float)
        regions[r] = {'weight': w_r, 'bias': b_r, 'n': n_r,
                      'draws': {key: w_r * np.average([boot[k][key] for k in rk], axis=0, weights=rw) + (1 - w_r) * nat[key]
                                for key in ('dt', 'dr', 'do')}}
    cohorts = {}
    for k in ks:
        b = national_bias if k in exposed else point[k]['bias']
        w = weight(point[k]['n'], b)
        reg = regions[region_of[k]]['draws']
        cohorts[k] = {**point[k], 'bias_used': b, 'weight': w, 'exposed': k in exposed,
                      'draws': {key: w * boot[k][key] + (1 - w) * reg[key] for key in ('dt', 'dr', 'do')}}
    return {'cohorts': cohorts, 'regions': regions,
            'national': {key: {'mean': float(np.mean(v)), 'lo': float(np.quantile(v, 0.1)), 'hi': float(np.quantile(v, 0.9))}
                         for key, v in nat.items()},
            'national_bias': national_bias}
