"""The statistical backbone: turnout and choice by cell, calibrated exactly.

1920 has no survey, so the backbone is hierarchical ecological inference on
state returns against census makeup, identified by the 1916 → 1920 suffrage
natural experiment. Every step has a posterior draw; every draw is calibrated
so that the unchanged world reproduces each state's certified R, D and other
votes exactly (product promise 1).

Turnout, per draw d:
  T1  κ: the change in logit turnout per eligible adult from 1916 to 1920 in
      the "old" states, where women could already vote for president in 1916
      and the legal electorate's makeup didn't change. Drawn from the
      predictive distribution across those states (mean and between-state
      spread).
  T2  In the "new" states, men's 1920 turnout = expit(logit(1916 turnout) + κ);
      women's votes are the residual, W = T20 − m20·M20, and women's turnout
      w = W / F20. Georgia and Mississippi, where women couldn't register in
      time, are a placebo: W there should be about 0.
  T3  In the old states, men and women are split with the ratio w/m drawn
      from the new states outside the South (no within-state evidence).
  T4  Within a state and sex, groups differ by a logit offset. Black
      Southerners' turnout comes from a Goodman regression of 1916 men's
      turnout on the Black share of eligible men across the eleven Southern
      states; elsewhere groups share the state-sex rate (an assumption, named).
      Black Southerners' shortfall against white turnout in their own state and
      sex is counted as exclusion (reason: extralegal_exclusion), not choice.
  T5  Calibration: a logit shift per state and sex so the state's total votes
      match exactly.

Choice, per draw d:
  C1  δ, women's logit tilt toward R: regression across states of the 1916 →
      1920 change in logit two-party R share on f, the share of 1920 votes cast
      by newly enfranchised women (0 in old states), with South/non-South
      intercepts. Re-fitted per draw because f depends on the turnout draw.
  C2  β_B, Black voters' logit shift toward R relative to white voters of the
      same state: prior N(1.5, 1.0) [I], updated by a Goodman regression across
      non-Southern states. The prior encodes the documented loyalty of Black
      voters to the Republican party before 1932; its size is an assumption.
  C3  Calibration: per state, intercepts for R and for other are solved by
      iterative scaling so R, D and other match the certified votes exactly.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .aggregate import World
from .geo import REGION_OF, SOUTH
from .stats import bayes_ols, expit, logit

GROUPS = ['native_white', 'foreign_white_naturalized', 'foreign_white_alien', 'black', 'other']


@dataclass
class Inputs:
    cells: pd.DataFrame      # state, sex, group, adults20, adults16
    returns: pd.DataFrame    # index state; R16 D16 O16 T16 R20 D20 O20 T20
    women16: set             # states where women could vote for president in Nov 1916
    women_pre19: set         # states where women could vote for president in Nov 1920 without the 19th
    closed_1920: set         # states where women couldn't register in time for Nov 1920
    alien_voting: set        # states where declarant aliens could vote in 1920
    ev: pd.Series            # 1920 electoral votes by state
    other_citizen: dict = field(default_factory=dict)  # state → citizen share of 'other' adults


@dataclass
class Fit:
    world: World             # the calibrated unchanged world, all draws
    cells: pd.DataFrame
    params: dict             # per-draw parameter arrays
    diagnostics: dict


def _solve(v, shift, tR, tO, iters=300):
    """Intercepts for R and other so a group of cells casts exactly tR and tO
    of its votes v (iterative scaling on a multinomial logit, D as base)."""
    aR, aO = 0.0, 0.0
    total = v.sum()
    for _ in range(iters):
        eR = np.exp(aR + shift)
        eO = np.exp(aO) * np.ones_like(eR)
        den = 1 + eR + eO
        pR, pO = eR / den, eO / den
        curR, curO = (v * pR).sum(), (v * pO).sum()
        if abs(curR - tR) < 1e-7 * total and abs(curO - tO) < 1e-7 * total + 1e-9:
            break
        aR += np.log(max(tR, 1e-12) / max(curR, 1e-12))
        aO += np.log(max(tO, 1e-12) / max(curO, 1e-12)) if tO > 0 else -50
    return pR, pO


def _black_south_bound(D, S, sidx, south_state, black, south_cell, female, votes_cell, share, can_eff, t, R, Dm, O, T, shift_R):
    """C3b (in place): Black Southern voters split like Black voters outside the
    South, bounded by the state's certified ledger; the rest of the state is
    re-calibrated. Returns how many draws hit the bound, per state."""
    nsb, bsc = black & ~south_cell, black & south_cell
    bound_hits = np.zeros(S)
    for d in range(D):
        vn = votes_cell[d, nsb]
        nb_nat = (vn[:, None] * share[d, nsb, :]).sum(axis=0) / max(vn.sum(), 1e-9)
        for s in np.where(south_state)[0]:
            nb = nb_nat
            idx = np.where(sidx == s)[0]
            b_idx, o_idx = idx[bsc[idx]], idx[~bsc[idx]]
            vb = votes_cell[d, b_idx]
            if vb.sum() <= 0:
                continue
            # Only parties on the state's certified ledger; minor-party share
            # capped at 80% of the state's minor-party vote.
            nb_s = nb.copy()
            o_cap = 0.8 * O[s] / max(vb.sum(), 1e-9)
            if nb_s[2] > o_cap:
                nb_s[:2] *= (1 - o_cap) / max(nb_s[0] + nb_s[1], 1e-9)
                nb_s[2] = o_cap
            nb = nb_s
            scale = min(1.0, 0.8 * R[s] / max(vb.sum() * nb[0], 1e-9), 0.8 * Dm[s] / max(vb.sum() * nb[1], 1e-9))
            if scale < 1.0:
                bound_hits[s] += 1
                for sex_m in (female, ~female):
                    bi = b_idx[sex_m[b_idx]]
                    oi = o_idx[sex_m[o_idx]]
                    lost = votes_cell[d, bi].sum() * (1 - scale)
                    can_eff[d, bi] *= scale
                    votes_cell[d, bi] *= scale
                    vo = votes_cell[d, oi].sum()
                    if vo > 0:
                        t[d, oi] *= 1 + lost / vo
                        votes_cell[d, oi] *= 1 + lost / vo
                vb = votes_cell[d, b_idx]
            share[d, b_idx, :] = nb
            v = votes_cell[d, o_idx]
            tR = R[s] / T[s] * votes_cell[d, idx].sum() - vb.sum() * nb[0]
            tO = O[s] / T[s] * votes_cell[d, idx].sum() - vb.sum() * nb[2]
            pR, pO = _solve(v, shift_R[d, o_idx], tR, max(tO, 0.0))
            share[d, o_idx, 0], share[d, o_idx, 2], share[d, o_idx, 1] = pR, pO, 1 - pR - pO
    return bound_hits


def legal_can(inp: Inputs, year: int) -> tuple[np.ndarray, list]:
    """Fraction of each cell legally able to vote, and the reason for the rest.

    Aliens only where inp.alien_voting; 'other' × inp.other_citizen. Women:
    1916 by women16, 1920 barred only where registration closed (closed_1920)."""
    c = inp.cells
    can = np.ones(len(c))
    reason = [''] * len(c)
    for i, r in enumerate(c.itertuples()):
        if r.group == 'foreign_white_alien' and r.state not in inp.alien_voting:
            can[i], reason[i] = 0.0, 'noncitizen'
        elif r.group == 'other':
            can[i] = inp.other_citizen.get(r.state, 1.0)
            reason[i] = 'native_status' if can[i] < 1 else ''
        if r.sex == 'F':
            if year == 1916 and r.state not in inp.women16:
                can[i], reason[i] = 0.0, 'sex'
            if year == 1920 and r.state in inp.closed_1920:
                can[i], reason[i] = 0.0, 'registration_closed'
    return can, reason


def fit(inp: Inputs, draws: int, seed: int, pop_cv: dict | None = None, beta_b_prior_only: bool = False) -> Fit:
    rng = np.random.default_rng(seed)
    c = inp.cells.reset_index(drop=True)
    states = sorted(inp.returns.index)
    S, C, D = len(states), len(c), draws
    sidx = np.array([states.index(s) for s in c.state])
    female = (c.sex == 'F').to_numpy()
    south_state = np.array([s in SOUTH for s in states])
    south_cell = south_state[sidx]
    black = (c.group == 'black').to_numpy()
    ret = inp.returns.loc[states]

    # ── Population draws: census undercount and interpolation error [I] ──
    cv = pop_cv or {'native_white': 0.02, 'foreign_white_naturalized': 0.04, 'foreign_white_alien': 0.05,
                    'black': 0.05, 'other': 0.08}
    cv_c = c.group.map(cv).to_numpy()
    noise = np.exp(rng.normal(0, 1, (D, C)) * cv_c - cv_c ** 2 / 2)
    a20 = c.adults20.to_numpy()[None, :] * noise
    a16 = c.adults16.to_numpy()[None, :] * noise * np.exp(rng.normal(0, 0.02, (D, C)))

    can16, _ = legal_can(inp, 1916)
    can20, reason20 = legal_can(inp, 1920)

    def per_state(x, mask=None):
        """Sum [D, C] over cells into [D, S]."""
        m = np.ones(C, bool) if mask is None else mask
        out = np.zeros((x.shape[0], S))
        np.add.at(out, (slice(None), sidx[m]), x[:, m])
        return out

    E16 = per_state(a16 * can16)
    E20 = per_state(a20 * can20)
    M16 = per_state(a16 * can16, ~female)
    M20 = per_state(a20 * can20, ~female)
    F20 = per_state(a20 * can20, female)
    T16 = ret.T16.to_numpy()[None, :]
    T20 = ret.T20.to_numpy()[None, :]

    old = np.array([s in inp.women16 for s in states])
    new = ~old
    closed = np.array([s in inp.closed_1920 for s in states])

    # T1: κ from the old states, predictive draw per state
    k_old = logit(T20 / E20)[:, old] - logit(T16 / E16)[:, old]           # [D, n_old]
    k_mean = k_old.mean(axis=1)
    k_sd = k_old.std(axis=1, ddof=1)
    n_old = old.sum()
    kappa_mean = k_mean + rng.standard_t(max(n_old - 1, 1), D) * k_sd / np.sqrt(n_old)
    kappa = kappa_mean[:, None] + rng.normal(0, 1, (D, S)) * k_sd[:, None]   # state-level predictive

    # T2: men's and women's turnout in new states
    m16 = T16 / np.maximum(M16, 1)
    m20_pred = expit(logit(m16) + kappa)
    W = T20 - m20_pred * M20
    w_raw = W / np.maximum(F20, 1)
    women_resid = w_raw.copy()                                               # kept for N1/N2
    # ρ = w/m, used for the old states (T3) from new non-Southern states
    ref = new & ~south_state & ~closed
    rho_new = np.clip(w_raw[:, ref] / m20_pred[:, ref], 0.05, 1.5)
    rho_draw = rho_new[np.arange(D), rng.integers(0, ref.sum(), D)]

    # State-sex turnout targets (votes cast by men, by women)
    votes_M = np.where(new, np.clip(m20_pred * M20, 0, T20), 0.0)
    votes_M = np.where(closed[None, :], T20, votes_M)
    # Old states: split with the drawn ratio
    m_old = T20 / np.maximum(M20 + rho_draw[:, None] * F20, 1)
    votes_M = np.where(old[None, :], m_old * M20, votes_M)
    # Neither sex may exceed 98% turnout of its eligible adults; any excess
    # (a draw of the old-state ratio that doesn't fit a high-turnout state)
    # moves to the other sex, so the state total stays exact.
    cap_M, cap_F = 0.98 * M20, 0.98 * F20
    votes_M = np.minimum(votes_M, cap_M)
    votes_M = np.maximum(votes_M, T20 - cap_F)
    votes_F = T20 - votes_M
    clipped = ((W < 0) & new[None, :] & ~closed[None, :]).mean(axis=0)

    # T4: Black Southern turnout (Goodman on 1916 men, 11 Southern states),
    # drawn from the regression posterior truncated to its logical bounds
    # [0, white rate] (Goodman with Duncan–Davis bounds).
    from scipy.stats import truncnorm
    blk_men16 = per_state(a16 * can16, ~female & black) / np.maximum(M16, 1)
    t_bs = np.empty(D)
    goodman_south = {}
    for d in range(D):
        X = np.column_stack([np.ones(south_state.sum()), blk_men16[d, south_state]])
        y = m16[d, south_state]
        _, _, info = bayes_ols(X, y, 1, rng)
        b0, b1 = info['beta_hat']
        cov = info['resid_sd'] ** 2 * np.linalg.inv(X.T @ X)
        white = max(b0, 1e-3)
        mu, sd = b0 + b1, float(np.sqrt(cov[0, 0] + cov[1, 1] + 2 * cov[0, 1]))
        a_, b_ = (0 - mu) / sd, (white - mu) / sd
        black_rate = float(truncnorm.rvs(a_, b_, loc=mu, scale=sd, random_state=rng))
        t_bs[d] = black_rate / white
        if d == 0:
            goodman_south = {'white_rate': float(b0), 'black_rate_unbounded': float(mu), 'black_rate_se': sd}

    # Build the world: can, t, and the exclusion split
    can = np.broadcast_to(can20, (D, C)).copy()
    excluded = np.zeros((D, C))
    bs = black & south_cell
    excluded[:, bs] = can[:, bs] * (1 - t_bs[:, None])
    can_eff = can - excluded
    # Calibrate a logit shift per state and sex so votes match exactly.
    t = np.zeros((D, C))
    for d in range(D):
        for sex, target in (('M', votes_M[d]), ('F', votes_F[d])):
            m = (c.sex == sex).to_numpy()
            for s in range(S):
                cells_s = np.where(m & (sidx == s))[0]
                elig = a20[d, cells_s] * can_eff[d, cells_s]
                if elig.sum() <= 0 or target[s] <= 0:
                    t[d, cells_s] = 0.0
                    continue
                t[d, cells_s] = min(target[s] / elig.sum(), 1.0)
    # Cells with all eligible voting at t>1 would be clipped; flag them
    over = (votes_M / np.maximum(M20, 1) > 1).mean(axis=0)

    # C1: women's tilt δ (per draw, re-fitted on this draw's f)
    rd16 = logit(ret.R16 / (ret.R16 + ret.D16)).to_numpy()
    rd20 = logit(ret.R20 / (ret.R20 + ret.D20)).to_numpy()
    y = rd20 - rd16
    delta = np.empty(D)
    swing_ns = np.empty(D)
    swing_s = np.empty(D)
    for d in range(D):
        f = np.where(new & ~closed, votes_F[d] / T20[0], 0.0)
        X = np.column_stack([~south_state, south_state, f]).astype(float)
        b, _, _ = bayes_ols(X, y, 1, rng)
        swing_ns[d], swing_s[d], delta[d] = b[0]

    # C2: Black voters' shift β_B: prior N(1.5, 1.0) [I] updated by a Goodman
    # regression across non-Southern states with region intercepts (so region
    # doesn't stand in for race) and the 1916 share as a covariate.
    blk_votes = per_state((a20 * can_eff * t), black) / T20
    ns = ~south_state
    reg_dummies = np.column_stack([[REGION_OF[s] == g for s in states] for g in ('northeast', 'midwest', 'west', 'border')]).astype(float)
    beta_B = np.empty(D)
    for d in range(D):
        X = np.column_stack([reg_dummies[ns], rd16[ns], blk_votes[d, ns]])
        b, _, _ = bayes_ols(X, rd20[ns], 1, rng, prior_mean=[0, 0, 0, 0, 1, 1.5], prior_sd=[10, 10, 10, 10, 10, 1.0])
        beta_B[d] = b[0, -1] if not beta_b_prior_only else rng.normal(1.5, 1.0)  # sensitivity: prior only

    # C3: exact calibration of shares
    share = np.zeros((D, C, 3))
    shift_R = np.where(female, 1, 0)[None, :] * delta[:, None] + black[None, :] * beta_B[:, None]
    votes_cell = a20 * can_eff * t
    R20, O20 = ret.R20.to_numpy(), ret.O20.to_numpy()
    D20 = ret.D20.to_numpy()
    for d in range(D):
        for s in range(S):
            idx = np.where(sidx == s)[0]
            v = votes_cell[d, idx]
            if v.sum() <= 0:
                continue
            pR, pO = _solve(v, shift_R[d, idx], R20[s] / T20[0, s] * v.sum(), O20[s] / T20[0, s] * v.sum())
            share[d, idx, 0], share[d, idx, 2], share[d, idx, 1] = pR, pO, 1 - pR - pO

    # C3b: Black Southern voters split like Black voters outside the South
    # (the assumption `fifteenth` borrows), subject to an accounting bound:
    # their votes for either major party can't exceed 80% of that party's
    # certified vote in the state (in South Carolina Harding got 2,610 votes).
    # Where the bound binds, Black Southern turnout is lowered, the difference
    # is counted as exclusion, and the state's other voters of the same sex
    # make up the total. The rest of the state is then re-calibrated.
    bound_hits = _black_south_bound(D, S, sidx, south_state, black, south_cell, female, votes_cell, share, can_eff, t,
                                    R20, D20, O20, T20[0], shift_R)
    excluded = can - can_eff

    barred_by = {
        'legal': a20 * 0 + (1 - can),
        'excluded': excluded,
    }
    world = World(adults=a20, can=can_eff, t=t, share=share, barred_by=barred_by)
    cells = c.assign(region=c.state.map(REGION_OF), south=south_cell, legal_reason=reason20)
    params = {'kappa_mean': kappa_mean, 'rho': rho_draw, 't_black_south_rel': t_bs, 'delta': delta,
              'beta_B': beta_B, 'swing_nonsouth': swing_ns, 'swing_south': swing_s}
    diag = {
        'states': states,
        'old_states': [s for s, o in zip(states, old) if o],
        'women_turnout_resid': women_resid,      # [D, S] women's implied turnout (N1/N2)
        'men_turnout_pred': m20_pred,
        'women_negative_share': dict(zip(states, clipped.tolist())),
        'men_turnout_over_1': dict(zip(states, over.tolist())),
        'goodman_south_first_draw': goodman_south,
        'black_south_bound_share': dict(zip(states, (bound_hits / D).tolist())),
        'E16': E16, 'E20': E20, 'T16': T16[0], 'T20': T20[0], 'm16': m16,
        'votes_F': votes_F, 'votes_M': votes_M, 'F20': F20, 'M20': M20,
    }
    return Fit(world=world, cells=cells, params=params, diagnostics=diag)
