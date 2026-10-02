"""Validation of the 1920 prototype (EVAL.md). Benchmarks are read only here.

Every check returns {id, name, value, threshold, pass, note}. `pass` is True,
False, or None ("not run", with the reason in `note`).
"""
from __future__ import annotations

import numpy as np

from .geo import SOUTH
from .stats import bayes_ols, brier, expit, logit, rmse, spearman


def check(id_, name, value, threshold, ok, note=''):
    return {'id': id_, 'name': name, 'value': value, 'threshold': threshold, 'pass': ok, 'note': note}


def r1_reproduction(fit, inp, state_votes) -> dict:
    """state_votes [D, S, 3] from the unchanged world."""
    states = fit.diagnostics['states']
    cert = np.array(inp.returns.reindex(states)[['R20', 'D20', 'O20']].fillna(0), dtype=float)
    err = np.abs(state_votes - cert[None, :, :])
    worst = float(err.max())
    ev = inp.ev.reindex(states).fillna(0).to_numpy()
    winners = state_votes.argmax(axis=2)
    ev_r = (ev[None, :] * (winners == 0)).sum(axis=1)
    ev_d = (ev[None, :] * (winners == 1)).sum(axis=1)
    ok = worst <= 1.0 and bool(np.all(ev_r == 404)) and bool(np.all(ev_d == 127))
    return check('R1', 'Unchanged rerun reproduces every state exactly', round(worst, 4),
                 '≤ 1 vote per state and party in every draw; EV 404–127 in every draw', ok,
                 f'EV R range {int(ev_r.min())}–{int(ev_r.max())}, D range {int(ev_d.min())}–{int(ev_d.max())}; {state_votes.shape[0]} draws')


def holdout(fit, inp, holdout_states: list, draws: int, seed: int) -> dict:
    """B1–B5: predict held-out states from training states only."""
    rng = np.random.default_rng(seed + 7)
    dg = fit.diagnostics
    states = dg['states']
    idx = {s: i for i, s in enumerate(states)}
    H = [idx[s] for s in holdout_states]
    Tr = [i for i in range(len(states)) if states[i] not in holdout_states]
    ret = inp.returns.loc[states]
    old = np.array([s in inp.women16 for s in states])
    closed = np.array([s in inp.closed_1920 for s in states])
    south = np.array([s in SOUTH for s in states])
    E16, E20 = dg['E16'], dg['E20']
    T16, T20 = dg['T16'], dg['T20']
    M20, F20, m16 = dg['M20'], dg['F20'], dg['m16']
    D = E16.shape[0]

    # κ from training old states only
    tr_old = [i for i in Tr if old[i]]
    k = logit(T20[None, tr_old] / E20[:, tr_old]) - logit(T16[None, tr_old] / E16[:, tr_old])
    kap = k.mean(axis=1)[:, None] + rng.normal(0, 1, (D, len(states))) * k.std(axis=1, ddof=1)[:, None]
    m20 = expit(logit(m16) + kap)
    # ρ from training new non-Southern states
    tr_new = [i for i in Tr if not old[i] and not south[i] and not closed[i]]
    W = T20[None, tr_new] - m20[:, tr_new] * M20[:, tr_new]
    rho = np.clip(W / np.maximum(F20[:, tr_new], 1) / m20[:, tr_new], 0.05, 1.5)
    rho_d = rho[np.arange(D), rng.integers(0, len(tr_new), D)]
    votes_hat = m20 * M20 + np.where(closed, 0, rho_d[:, None] * m20 * F20)
    # Old states: 1916 votes already included women's, so project turnout per
    # eligible adult by κ, as the backbone's T1 does. (Fixed after the first
    # evaluation used men's-only m16 here; see EVAL.md, deviations.)
    t_old = expit(logit(T16[None, :] / E16) + kap) * E20
    votes_hat = np.where(old[None, :], t_old, votes_hat)
    sidx = np.array([idx[s] for s in fit.cells.state])
    A = np.zeros((D, len(states)))
    np.add.at(A, (slice(None), sidx), fit.world.adults)
    turn_hat = votes_hat / A
    turn_act = T20[None, :] / A
    # Persistence: 1916 votes ÷ 1916 adults
    A16 = np.zeros(len(states))
    np.add.at(A16, sidx, fit.cells.adults16.to_numpy())
    turn_persist = T16 / A16

    # Two-party share: swing + women's tilt, fitted on training states
    rd16 = logit((ret.R16 / (ret.R16 + ret.D16)).to_numpy())
    rd20 = logit((ret.R20 / (ret.R20 + ret.D20)).to_numpy())
    f_hat = np.where(~old & ~closed, 1 - (m20 * M20) / np.maximum(votes_hat, 1), 0.0)
    pred = np.empty((D, len(H)))
    for d in range(D):
        f_tr = np.where(~old & ~closed, dg['votes_F'][d] / T20, 0.0)
        X = np.column_stack([~south, south, f_tr]).astype(float)[Tr]
        b, sig, _ = bayes_ols(X, (rd20 - rd16)[Tr], 1, rng)
        Xh = np.column_stack([~south, south, f_hat[d]]).astype(float)[H]
        pred[d] = rd16[H] + Xh @ b[0] + rng.normal(0, sig[0], len(H))
    share_hat = expit(np.median(pred, axis=0)) * 100
    actual = expit(rd20[H]) * 100
    # Baselines
    w = (ret.R20 + ret.D20).to_numpy()
    persist = expit(rd16[H]) * 100
    swing = np.average((rd20 - rd16)[Tr], weights=w[Tr])
    uniform = expit(rd16[H] + swing) * 100
    us_sd = float(np.std((rd20 - rd16)[Tr] - swing, ddof=1))
    # Demographic regression (no lag)
    comp = composition(fit, states)
    Xd = np.column_stack([np.ones(len(states)), south, comp['black'], comp['foreign'], comp['new_women']])
    bd, *_ = np.linalg.lstsq(Xd[Tr], rd20[Tr], rcond=None)
    demo = expit(Xd[H] @ bd) * 100

    p_win = (pred > 0).mean(axis=0)
    p_us = 1 - _norm_cdf(-(rd16[H] + swing) / us_sd)
    won = (rd20[H] > 0).astype(float)
    ev = inp.ev.loc[holdout_states].to_numpy()
    ev_pred = float(np.sum(ev * (share_hat > 50)))
    ev_act = float(np.sum(ev * won))
    close = [s for s, a in zip(holdout_states, actual) if abs(a - 50) * 2 < 5]
    ev_tol = float(min(inp.ev.loc[close])) if close else 0.0

    b1 = rmse(share_hat, actual)
    b2 = rmse(np.median(turn_hat[:, H], axis=0) * 100, np.median(turn_act[:, H], axis=0) * 100)
    b2p = rmse(turn_persist[H] * 100, np.median(turn_act[:, H], axis=0) * 100)
    rows = [{'state': s, 'actual': round(float(a), 2), 'backbone': round(float(p), 2), 'persistence': round(float(q), 2),
             'uniform_swing': round(float(u), 2), 'demographic': round(float(g), 2), 'p_R_win': round(float(pw), 3),
             'turnout_actual': round(float(np.median(turn_act[:, i]) * 100), 1),
             'turnout_backbone': round(float(np.median(turn_hat[:, i]) * 100), 1),
             'turnout_persistence': round(float(turn_persist[i] * 100), 1)}
            for s, a, p, q, u, g, pw, i in zip(holdout_states, actual, share_hat, persist, uniform, demo, p_win, H)]
    checks = [
        check('B1', 'Holdout two-party RMSE (points)', {'backbone': round(b1, 2), 'uniform_swing': round(rmse(uniform, actual), 2),
              'persistence': round(rmse(persist, actual), 2), 'demographic': round(rmse(demo, actual), 2)},
              'backbone ≤ uniform swing and ≤ persistence', b1 <= rmse(uniform, actual) and b1 <= rmse(persist, actual)),
        check('B2', 'Holdout turnout RMSE (points of adults 21+)', {'backbone': round(b2, 2), 'persistence': round(b2p, 2)},
              'backbone ≤ persistence', b2 <= b2p),
        check('B3', 'Holdout Spearman ρ, two-party share', round(spearman(share_hat, actual), 3), '≥ 0.8',
              spearman(share_hat, actual) >= 0.8),
        check('B4', 'Holdout Brier score, state winner', {'backbone': round(brier(p_win, won), 4), 'uniform_swing': round(brier(p_us, won), 4)},
              'backbone ≤ uniform swing', brier(p_win, won) <= brier(p_us, won)),
        check('B5', 'Holdout electoral-vote error (Harding)', abs(ev_pred - ev_act), f'≤ {ev_tol:g}',
              abs(ev_pred - ev_act) <= ev_tol, f'predicted {ev_pred:g}, actual {ev_act:g}; states decided by < 5 points: {close or "none"}'),
    ]
    return {'checks': checks, 'rows': rows}


def _norm_cdf(x):
    from scipy.stats import norm
    return norm.cdf(x)


def composition(fit, states) -> dict:
    c = fit.cells
    a = c.groupby('state').adults20.sum()
    blk = c[c.group == 'black'].groupby('state').adults20.sum().reindex(states, fill_value=0) / a.reindex(states)
    fb = c[c.group.str.startswith('foreign')].groupby('state').adults20.sum().reindex(states, fill_value=0) / a.reindex(states)
    nw = c[(c.sex == 'F') & (c.group != 'foreign_white_alien')].groupby('state').adults20.sum().reindex(states, fill_value=0) / a.reindex(states)
    old = fit.diagnostics['old_states']
    nw = nw.where(~nw.index.isin(old), 0.0)
    return {'black': blk.to_numpy(), 'foreign': fb.to_numpy(), 'new_women': nw.to_numpy()}
