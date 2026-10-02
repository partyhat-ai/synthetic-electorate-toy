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
    # General years (general_fit): the election year, the states where women could
    # vote for president at that election, and the voting age (21; 18 from 1972).
    year: int = 1920
    women_vote: set = field(default_factory=set)
    voting_age: int = 21
    # state → fraction of that state's Black / white adults legally able to vote
    # (slavery, free-Black exclusion, property and taxpaying tests; empty = 1).
    black_can: dict = field(default_factory=dict)
    white_can: dict = field(default_factory=dict)
    # States whose electors the legislature chose (no popular vote that year).
    no_popular: set = field(default_factory=set)


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


def _black_south_bound(D, S, sidx, south_state, black, south_cell, female, votes_cell, share, can_eff, t, R, Dm, O, T, shift_R,
                       solver=None):
    """C3b (in place): Black Southern voters split like Black voters outside the
    South, bounded by the state's certified ledger; the rest of the state is
    re-calibrated. Returns how many draws hit the bound, per state.
    solver: (v, shift, tR, tO) → (pR, pO); _solve by default (fit, carry_forward)."""
    solver = solver or _solve
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
            if R[s] <= 0 or Dm[s] <= 0:
                # A major party off the state's ballot (general years only).
                nb_s[0] *= R[s] > 0
                nb_s[1] *= Dm[s] > 0
                nb_s = nb_s / nb_s.sum() if nb_s.sum() > 0 else np.array([0.0, 0.0, 1.0])
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
            pR, pO = solver(v, shift_R[d, o_idx], tR, max(tO, 0.0))
            share[d, o_idx, 0], share[d, o_idx, 2], share[d, o_idx, 1] = pR, pO, 1 - pR - pO
    return bound_hits


WHITE_GROUPS = ('native_white', 'foreign_white_naturalized', 'foreign_white_alien')


def legal_can(inp: Inputs, year: int) -> tuple[np.ndarray, list]:
    """Fraction of each cell legally able to vote, and the reason for the rest.

    Any year: aliens only where inp.alien_voting; 'other' × inp.other_citizen;
    Black adults × inp.black_can[state] (slavery, free-Black exclusion); white
    adults × inp.white_can[state] (property and taxpaying tests). Women: 1916
    by women16, 1920 barred only where registration closed (closed_1920);
    any other year only in inp.women_vote — except that after 1920 an empty
    women_vote means the 19th Amendment everywhere (so 1916/1920/1924 calls
    return exactly what they did before general years existed)."""
    c = inp.cells
    can = np.ones(len(c))
    reason = [''] * len(c)
    women_rule = year not in (1916, 1920) and (year < 1920 or bool(inp.women_vote))
    for i, r in enumerate(c.itertuples()):
        if r.group == 'foreign_white_alien' and r.state not in inp.alien_voting:
            can[i], reason[i] = 0.0, 'noncitizen'
        elif r.group == 'other':
            can[i] = inp.other_citizen.get(r.state, 1.0)
            reason[i] = 'native_status' if can[i] < 1 else ''
        f = inp.black_can.get(r.state, 1.0) if r.group == 'black' else (
            inp.white_can.get(r.state, 1.0) if r.group in WHITE_GROUPS else 1.0)
        if f != 1.0:
            can[i] *= f
            reason[i] = reason[i] or ('race_law' if r.group == 'black' else 'property_tax')
        if r.sex == 'F':
            if year == 1916 and r.state not in inp.women16:
                can[i], reason[i] = 0.0, 'sex'
            if year == 1920 and r.state in inp.closed_1920:
                can[i], reason[i] = 0.0, 'registration_closed'
            if women_rule and r.state not in inp.women_vote:
                can[i], reason[i] = 0.0, 'sex'
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


def carry_forward(base: Fit, inp: Inputs, year: int, seed: int) -> Fit:
    """A later election with no natural experiment of its own (1924): the base
    year's fit supplies the group structure, and the new year's returns
    calibrate it exactly.

    Per draw d (the base fit's draw d):
      P   adults: the base cells aged to election day (data.population) with
          fresh census noise.
      X   Black Southern exclusion: the base year's relative turnout t_bs.
      T   turnout: the base year's cell turnout in logits, plus one shift per
          state (all groups and both sexes alike) solved so the state's total
          votes match. So the base year's women-to-men and group ratios carry
          forward [I]; Corder–Wolbrecht 1924 is held out to check that.
          Cells that couldn't vote in the base year (Georgia and Mississippi
          women in 1920) start from their state's men times the median
          women-to-men turnout ratio of the other Southern states.
      C   choice: the base year's tilts (women δ, Black voters β_B), then the
          same exact calibration (C3, C3b) to the year's R, D and other votes.
          A third candidate's vote (La Follette) is spread evenly across a
          state's groups: within-state differences in it aren't identified.
    """
    rng = np.random.default_rng(seed + year)
    c = inp.cells.reset_index(drop=True)
    assert (c[['state', 'sex', 'group']].to_numpy() == base.cells[['state', 'sex', 'group']].to_numpy()).all()
    states = base.diagnostics['states']
    S, C = len(states), len(c)
    D = base.world.t.shape[0]
    sidx = np.array([states.index(s) for s in c.state])
    female = (c.sex == 'F').to_numpy()
    black = (c.group == 'black').to_numpy()
    south_state = np.array([s in SOUTH for s in states])
    south_cell = south_state[sidx]
    y = year % 100
    ret = inp.returns.loc[states]
    T, R, Dm, O = (ret[f'{k}{y}'].to_numpy() for k in ('T', 'R', 'D', 'O'))

    def per_state(x):
        out = np.zeros((x.shape[0], S))
        np.add.at(out, (slice(None), sidx), x)
        return out

    cv = {'native_white': 0.02, 'foreign_white_naturalized': 0.04, 'foreign_white_alien': 0.05, 'black': 0.05, 'other': 0.08}
    cv_c = c.group.map(cv).to_numpy()
    a = c.adults20.to_numpy()[None, :] * np.exp(rng.normal(0, 1, (D, C)) * cv_c - cv_c ** 2 / 2)

    can1, reason = legal_can(inp, year)
    can = np.broadcast_to(can1, (D, C)).copy()
    t_bs = base.params['t_black_south_rel']
    excluded = np.zeros((D, C))
    bs = black & south_cell
    excluded[:, bs] = can[:, bs] * (1 - t_bs[:, None])
    can_eff = can - excluded

    # T: turnout prior from the base year, one logit shift per state.
    t0 = base.world.t.copy()
    male_of = {(r.state, r.group): i for i, r in c.iterrows() if r.sex == 'M'}
    mate = np.array([male_of.get((r.state, r.group), i) for i, r in c.iterrows()])
    sw = female & south_cell & (t0.mean(axis=0) > 0)
    ratio = np.median(np.where(sw[None, :], t0 / np.maximum(t0[:, mate], 1e-6), np.nan)[:, sw], axis=1)
    gap = (t0 <= 0) & (can_eff > 0) & female[None, :]
    t0 = np.where(gap, t0[:, mate] * ratio[:, None], t0)
    lt = logit(np.clip(t0, 1e-4, 0.995))
    elig = a * can_eff
    lo, hi = np.full((D, S), -8.0), np.full((D, S), 8.0)
    for _ in range(60):
        mid = (lo + hi) / 2
        v = per_state(elig * expit(lt + mid[:, sidx]))
        over = v > T[None, :]
        hi, lo = np.where(over, mid, hi), np.where(over, lo, mid)
    k = (lo + hi) / 2
    t = np.where(elig > 0, expit(lt + k[:, sidx]), 0.0)
    votes_cell = elig * t

    # C: the base year's tilts, recalibrated exactly.
    delta, beta_B = base.params['delta'], base.params['beta_B']
    shift_R = female[None, :] * delta[:, None] + black[None, :] * beta_B[:, None]
    share = np.zeros((D, C, 3))
    for d in range(D):
        for s in range(S):
            idx = np.where(sidx == s)[0]
            v = votes_cell[d, idx]
            if v.sum() <= 0:
                continue
            pR, pO = _solve(v, shift_R[d, idx], R[s] / T[s] * v.sum(), O[s] / T[s] * v.sum())
            share[d, idx, 0], share[d, idx, 2], share[d, idx, 1] = pR, pO, 1 - pR - pO
    bound_hits = _black_south_bound(D, S, sidx, south_state, black, south_cell, female, votes_cell, share, can_eff, t,
                                    R, Dm, O, T, shift_R)
    world = World(adults=a, can=can_eff, t=t, share=share, barred_by={'legal': 1 - can, 'excluded': can - can_eff})
    cells = c.assign(region=c.state.map(REGION_OF), south=south_cell, legal_reason=reason)
    F = per_state(a * can_eff * female[None, :])
    diag = {'states': states, 'base_year': base.diagnostics.get('year', 1920), 'turnout_shift': k,
            'women_turnout': per_state(votes_cell * female[None, :]) / np.maximum(F, 1),
            'men_turnout': per_state(votes_cell * ~female[None, :]) / np.maximum(per_state(a * can_eff * ~female[None, :]), 1),
            'black_south_bound_share': dict(zip(states, (bound_hits / D).tolist())), 'gap_ratio': ratio}
    params = {'delta': delta, 'beta_B': beta_B, 't_black_south_rel': t_bs, 'turnout_shift': k}
    return Fit(world=world, cells=cells, params=params, diagnostics=diag)


# ── General years (general_fit): every year without 1920's natural experiment or a base year ──
#
# Priors are (year, mean, sd) knots, linear between knots and flat beyond the
# ends; every one is [I] (an assumption from the literature, not estimated
# here). Sources and judgement calls: notes/B.md.

# Turnout, logit offset against native white adults of the same state and sex.
WOMEN_TURNOUT = [(1789, -1.3, 0.4), (1916, -1.3, 0.4), (1920, -1.3, 0.3), (1928, -1.0, 0.3), (1940, -0.7, 0.25),
                 (1952, -0.45, 0.2), (1964, -0.24, 0.1), (1972, -0.09, 0.08), (1980, 0.0, 0.08), (1992, 0.09, 0.06),
                 (2008, 0.18, 0.06), (2024, 0.16, 0.06)]       # against men: C–W 2016; ANES; CPS P20
NAT_TURNOUT = [(1789, -0.3, 0.3), (2024, -0.3, 0.25)]          # Merriam–Gosnell 1924; CPS naturalized vs native
ALIEN_TURNOUT = [(1789, -0.6, 0.4), (2024, -0.6, 0.4)]         # declarant aliens where legal (to 1926)
OTHER_TURNOUT = [(1789, -0.3, 0.4), (2024, -0.3, 0.4)]
BLACK_TURNOUT = [(1789, 0.0, 0.4), (1960, 0.0, 0.3), (1964, -0.5, 0.2), (1976, -0.5, 0.15), (1984, -0.25, 0.15),
                 (1992, -0.4, 0.15), (2000, -0.2, 0.15), (2004, -0.3, 0.15), (2008, -0.06, 0.12), (2012, 0.09, 0.12),
                 (2016, -0.24, 0.12), (2020, -0.37, 0.12), (2024, -0.45, 0.2)]   # CPS P20, citizen basis
# Black Southern exclusion: share of legally eligible Black adults in the
# eleven ex-Confederate states kept from voting (beta draws; 0 = none).
BLACK_SOUTH_EXCLUDED = [(1866, 0.0, 0.0), (1868, 0.15, 0.1), (1872, 0.1, 0.08), (1876, 0.2, 0.1), (1880, 0.35, 0.12),
                        (1888, 0.4, 0.12), (1892, 0.55, 0.12), (1896, 0.6, 0.12), (1900, 0.75, 0.1),
                        (1904, 0.884, 0.104), (1944, 0.884, 0.104),     # 1920 fit's t_bs posterior (0.116 ± 0.104)
                        (1948, 0.77, 0.08), (1952, 0.67, 0.08), (1956, 0.6, 0.08), (1960, 0.52, 0.08),
                        (1964, 0.41, 0.08), (1968, 0.25, 0.07), (1972, 0.15, 0.06), (1976, 0.1, 0.05), (1980, 0.0, 0.0)]
BOUND_YEARS = (1892, 1964)     # C3b accounting bound (_black_south_bound) applies in these years

# Choice, logit tilt toward R (vs D) against white / native voters of the same state.
DELTA_1920 = (-0.662, 0.272)   # backbone.fit(1920), 400 draws: posterior mean, sd of δ (DISCLOSURES B4)
WOMEN_TILT = [(1789, *DELTA_1920), (1940, *DELTA_1920), (1944, 0.0, 0.3), (1948, 0.05, 0.25), (1952, 0.2, 0.2),
              (1956, 0.25, 0.2), (1960, 0.1, 0.2), (1964, -0.08, 0.2), (1968, 0.0, 0.2), (1972, 0.0, 0.2),
              (1976, 0.15, 0.2), (1980, -0.38, 0.15), (1984, -0.28, 0.15), (1988, -0.31, 0.15), (1992, -0.12, 0.15),
              (1996, -0.37, 0.15), (2000, -0.46, 0.15), (2004, -0.28, 0.15), (2008, -0.24, 0.15), (2012, -0.37, 0.15),
              (2016, -0.52, 0.15), (2020, -0.47, 0.15), (2024, -0.43, 0.15)]   # Gallup 1944–76; exit polls 1980–
BLACK_TILT = [(1789, 0.5, 1.0), (1852, 0.5, 1.0), (1856, 1.5, 1.0), (1864, 1.5, 1.0), (1868, 2.5, 1.0), (1876, 2.5, 1.0),
              (1880, 1.5, 1.0), (1928, 1.5, 1.0), (1932, 1.0, 0.7), (1936, -0.4, 0.6), (1940, -0.55, 0.5),
              (1944, -0.6, 0.5), (1948, -1.1, 0.5), (1952, -1.6, 0.5), (1956, -0.8, 0.5), (1960, -0.8, 0.5),
              (1964, -2.4, 0.4), (1968, -2.2, 0.4), (1972, -2.65, 0.4), (1976, -1.7, 0.4), (1980, -2.2, 0.4),
              (1984, -2.9, 0.4), (1988, -2.6, 0.4), (1992, -2.15, 0.4), (1996, -2.0, 0.4), (2000, -2.55, 0.4),
              (2004, -2.4, 0.4), (2008, -3.4, 0.4), (2012, -3.15, 0.4), (2016, -2.9, 0.4), (2020, -2.5, 0.4),
              (2024, -2.1, 0.4)]
NAT_TILT = [(1789, -0.5, 0.6), (1892, -0.5, 0.5), (1896, 0.0, 0.5), (1924, 0.0, 0.5), (1928, -0.6, 0.4),
            (1960, -0.6, 0.4), (1964, -0.2, 0.4), (1988, -0.2, 0.4), (1992, -0.4, 0.4), (2024, -0.3, 0.4)]
OTHER_TILT = [(1789, 0.0, 0.7), (2024, 0.0, 0.7)]

POP_CV = {'native_white': 0.02, 'foreign_white_naturalized': 0.04, 'foreign_white_alien': 0.05, 'black': 0.05, 'other': 0.08}


def prior_at(table, year):
    """(mean, sd) of a knot table at `year`."""
    ys = np.array([k[0] for k in table], float)
    return float(np.interp(year, ys, [k[1] for k in table])), float(np.interp(year, ys, [k[2] for k in table]))


def _draw_normal(rng, table, year, D):
    m, s = prior_at(table, year)
    return m + s * rng.normal(0, 1, D)


def _draw_beta(rng, table, year, D):
    m, s = prior_at(table, year)
    if m <= 0:
        return np.zeros(D)
    s = min(s, 0.99 * np.sqrt(m * (1 - m)))
    k = m * (1 - m) / s ** 2 - 1
    return rng.beta(m * k, (1 - m) * k, D)


def _solve_ledger(v, shift, tgt, iters=1000, tol=1e-11):
    """_solve for any ledger, vectorised over draws: v [D, n] votes, shift [D, n]
    the R tilt (D as reference), tgt [D, 3] R, D, O votes. A party with no votes
    gets share exactly 0; the base is the state's largest party, so near-unanimous
    and minor-party-majority states converge. Returns shares [D, n, 3]."""
    Dn, n = v.shape
    tgt = np.maximum(tgt, 0.0)
    act = tgt[0] > 0
    P = np.zeros((Dn, n, 3))
    if not act.any():
        P[..., 1] = 1.0
        return P
    base = int(np.argmax(tgt[0]))
    if act.sum() == 1:
        P[..., base] = 1.0
        return P
    sh = np.zeros((Dn, n, 3))
    sh[..., 0] = shift
    a = np.zeros((Dn, 3))
    upd = [j for j in range(3) if act[j] and j != base]
    total = v.sum(axis=1)
    for _ in range(iters):
        u = a[:, None, :] + sh
        u = np.where(act[None, None, :], u - u[..., base:base + 1], -np.inf)
        e = np.exp(u - u.max(axis=2, keepdims=True))
        P = e / e.sum(axis=2, keepdims=True)
        cur = (v[..., None] * P).sum(axis=1)
        if (np.abs(cur - tgt)[:, act] <= tol * total[:, None] + 1e-9).all():
            break
        for j in upd:
            a[:, j] += np.log(tgt[:, j] / np.maximum(cur[:, j], 1e-300))
    return P


def _solve_scalar(v, shift, tR, tO):
    """_solve's signature on _solve_ledger (for _black_south_bound in general years)."""
    tgt = np.array([[tR, max(v.sum() - tR - tO, 0.0), tO]])
    P = _solve_ledger(v[None, :], shift[None, :], tgt)[0]
    return P[:, 0], P[:, 2]


def general_fit(inp: Inputs, year: int, draws: int, seed: int, delta_draws: np.ndarray | None = None,
                pop_cv: dict | None = None) -> Fit:
    """Any year with neither 1920's natural experiment nor a base year.

    Per draw d:
      L   legal: legal_can(inp, year) (women_vote, black_can, white_can,
          alien_voting, other_citizen); legislature states (no_popular) cast 0.
      X   Black Southern exclusion (1868–1976): a beta draw of the share kept
          from voting, era prior BLACK_SOUTH_EXCLUDED [I]; Reconstruction low.
      T   turnout: group logit offsets drawn from era priors (women, naturalized,
          aliens, Black, other) [I], plus one shift per state (bisection) so the
          state's votes are exactly R + D + O. If the ledger exceeds 97% of the
          eligible, the state's adults are scaled up (flagged).
      C   choice: R tilts drawn from era priors (women δ, Black β_B, naturalized
          β_N, other β_O) [I]; per state the R, D and O intercepts are solved
          exactly (_solve_ledger: zero-vote parties get 0). O is spread like
          carry_forward (one intercept per state). 1892–1964: the C3b bound.
      delta_draws: optional δ draws from a 1920 fit to use for 1920–1940 in
          place of the summary prior DELTA_1920.
      pop_cv: census-noise CVs by group (POP_CV by default; zeros for run.uncertainty_budget).
    """
    rng = np.random.default_rng(seed + year)
    D = draws
    yy = year % 100
    c0 = inp.cells.reset_index(drop=True)
    acol = 'adults20' if 'adults20' in c0 else 'adults'
    can0, reason0 = legal_can(inp, year)

    # ── Ledger: R, D, O per state; targets are R + D + O (verify checks those) ──
    rr = inp.returns
    col = lambda k: rr[f'{k}{yy}'] if f'{k}{yy}' in rr else pd.Series(0.0, index=rr.index)
    led = pd.DataFrame({k: pd.to_numeric(col(k), errors='coerce') for k in 'RDOTP'}).fillna(0.0)
    if f'O{yy}' not in rr:
        led['O'] = (led['T'] - led['R'] - led['D']).clip(lower=0)
    ev_idx = set(map(str, getattr(inp.ev, 'index', [])))
    keep = set(map(str, led.index)) | ev_idx | set(inp.no_popular)
    dropped = sorted(set(c0.state) - keep)
    c0 = c0[~c0.state.isin(dropped)].reset_index(drop=True) if dropped else c0
    if dropped:
        m_keep = ~inp.cells.reset_index(drop=True).state.isin(dropped).to_numpy()
        can0, reason0 = can0[m_keep], [r for r, k in zip(reason0, m_keep) if k]
    states = sorted(set(map(str, led.index)) | set(c0.state) | (ev_idx & set(inp.no_popular)))
    missing = sorted(set(states) - set(map(str, led.index)))
    led = led.reindex(states).fillna(0.0)
    for s in inp.no_popular:
        if s in led.index:
            led.loc[s, ['R', 'D', 'O', 'T', 'P']] = 0.0
    R, Dm, O = (led[k].to_numpy(float) for k in 'RDO')
    R, Dm, O = np.maximum(R, 0), np.maximum(Dm, 0), np.maximum(O, 0)
    T = R + Dm + O
    t_mismatch = {s: float(a - b) for s, a, b in zip(states, led['T'], T) if abs(a - b) > 0.5 and a > 0}

    # ── Synthetic cells: a state with votes but no population cells ──
    women_ok = lambda s: year >= 1920 or s in inp.women_vote
    pop_s = c0.groupby('state')[acol].sum()
    syn_rows = []
    for s, tv in zip(states, T):
        if tv > 0 and pop_s.get(s, 0.0) <= 0:
            sexes = ['M', 'F'] if women_ok(s) else ['M']
            for x in sexes:
                syn_rows.append({'state': s, 'sex': x, 'group': 'native_white', acol: tv / 0.6 / len(sexes)})
    c = c0.assign(synthetic=False)
    if syn_rows:
        c = pd.concat([c, pd.DataFrame(syn_rows).assign(synthetic=True)], ignore_index=True)
        can0 = np.concatenate([can0, np.ones(len(syn_rows))])
        reason0 = list(reason0) + [''] * len(syn_rows)
    S, C = len(states), len(c)
    sidx = np.array([states.index(s) for s in c.state])
    female = (c.sex == 'F').to_numpy()
    grp = c.group.to_numpy()
    black, nat, alien, other = (grp == 'black'), (grp == 'foreign_white_naturalized'), (grp == 'foreign_white_alien'), (grp == 'other')
    south_state = np.array([s in SOUTH for s in states])
    south_cell = south_state[sidx]
    no_pop = np.array([s in inp.no_popular for s in states])

    def per_state(x):
        out = np.zeros((x.shape[0], S))
        np.add.at(out, (slice(None), sidx), x)
        return out

    # ── P: population draws ──
    cv_c = c.group.map(pop_cv or POP_CV).fillna(0.0 if pop_cv else 0.05).to_numpy()
    a = c[acol].fillna(0.0).to_numpy(float)[None, :] * np.exp(rng.normal(0, 1, (D, C)) * cv_c - cv_c ** 2 / 2)

    # ── L, X: legal and practical eligibility ──
    can = np.broadcast_to(can0, (D, C)).copy()
    reason = list(reason0)
    contradict = []
    for s in np.where((T > 0) & ((a * can).sum(axis=0) @ np.eye(S)[sidx] <= 0))[0]:
        # Votes cast where the coded rules bar everyone: the rules lose (men first).
        m = (sidx == s) & ~female if ((sidx == s) & ~female & (a[0] > 0)).any() else (sidx == s)
        can[:, m] = 1.0
        for i in np.where(m)[0]:
            reason[i] = ''
        contradict.append(states[s])
    x_bs = _draw_beta(rng, BLACK_SOUTH_EXCLUDED, year, D) if year >= 1868 else np.zeros(D)
    bs = black & south_cell
    excluded = np.zeros((D, C))
    excluded[:, bs] = can[:, bs] * x_bs[:, None]
    can_eff = can - excluded

    # ── T: turnout ──
    pri = {'women_turnout': WOMEN_TURNOUT, 'naturalized_turnout': NAT_TURNOUT, 'alien_turnout': ALIEN_TURNOUT,
           'black_turnout': BLACK_TURNOUT, 'other_turnout': OTHER_TURNOUT}
    dr = {k: _draw_normal(rng, tab, year, D) for k, tab in pri.items()}
    off = (female[None, :] * dr['women_turnout'][:, None] + nat[None, :] * dr['naturalized_turnout'][:, None]
           + alien[None, :] * dr['alien_turnout'][:, None] + black[None, :] * dr['black_turnout'][:, None]
           + other[None, :] * dr['other_turnout'][:, None])
    elig = a * can_eff
    E = per_state(elig)
    cap = 0.97
    need = np.where(E > 0, T[None, :] / np.maximum(cap * E, 1e-9), 1.0)
    grow = np.maximum(need, 1.0)
    scaled = (grow > 1).mean(axis=0)
    a = a * grow[:, sidx]
    elig = a * can_eff
    lo, hi = np.full((D, S), -30.0), np.full((D, S), 30.0)
    for _ in range(100):
        mid = (lo + hi) / 2
        v = per_state(elig * expit(off + mid[:, sidx]))
        over = v > T[None, :]
        hi, lo = np.where(over, mid, hi), np.where(over, lo, mid)
    k = (lo + hi) / 2
    t = np.where(elig > 0, expit(off + k[:, sidx]), 0.0)
    t[:, (T <= 0)[sidx]] = 0.0
    V = per_state(elig * t)
    t = np.minimum(t * np.where(V > 0, T[None, :] / np.maximum(V, 1e-300), 0.0)[:, sidx], 1.0)
    votes_cell = elig * t

    # ── C: choice ──
    if delta_draws is not None and 1920 <= year <= 1940:
        delta = np.asarray(delta_draws, float)[np.arange(D) % len(delta_draws)]
    else:
        delta = _draw_normal(rng, WOMEN_TILT, year, D)
    beta_B = _draw_normal(rng, BLACK_TILT, year, D)
    beta_N = _draw_normal(rng, NAT_TILT, year, D)
    beta_O = _draw_normal(rng, OTHER_TILT, year, D)
    shift_R = (female[None, :] * delta[:, None] + black[None, :] * beta_B[:, None]
               + (nat | alien)[None, :] * beta_N[:, None] + other[None, :] * beta_O[:, None])
    share = np.zeros((D, C, 3))
    share[..., 1] = 1.0
    ledger = np.stack([R, Dm, O], axis=1)
    for s in range(S):
        idx = np.where(sidx == s)[0]
        if len(idx) == 0 or T[s] <= 0:
            continue
        v = votes_cell[:, idx]
        tgt = ledger[s][None, :] / T[s] * v.sum(axis=1, keepdims=True)
        share[:, idx, :] = _solve_ledger(v, shift_R[:, idx], tgt)
    bound_hits = np.zeros(S)
    nsb_votes = votes_cell[:, black & ~south_cell].sum(axis=1)
    bound_on = BOUND_YEARS[0] <= year <= BOUND_YEARS[1] and bs.any() and bool((nsb_votes > 0).all())
    if bound_on:
        bound_hits = _black_south_bound(D, S, sidx, south_state & (T > 0), black, south_cell, female, votes_cell, share,
                                        can_eff, t, R, Dm, O, np.maximum(T, 1e-9), shift_R, solver=_solve_scalar)

    world = World(adults=a, can=can_eff, t=t, share=share, barred_by={'legal': 1 - can, 'excluded': can - can_eff})
    # AK and HI (from 1960) aren't in geo.REGION_OF yet: 'west' so cohort merging has a region.
    cells = c.assign(region=c.state.map(REGION_OF).fillna('west'), south=south_cell, legal_reason=reason)
    F = per_state(a * can_eff * female[None, :])
    M = per_state(a * can_eff * ~female[None, :])
    vF, vM = per_state(votes_cell * female[None, :]), per_state(votes_cell * ~female[None, :])
    prior_used = {k: prior_at(tab, year) for k, tab in
                  {**pri, 'black_south_excluded': BLACK_SOUTH_EXCLUDED, 'women_tilt': WOMEN_TILT,
                   'black_tilt': BLACK_TILT, 'naturalized_tilt': NAT_TILT, 'other_tilt': OTHER_TILT}.items()}
    P = led['P'].to_numpy(float)
    diag = {
        'states': states, 'year': year, 'method': 'general_fit', 'old_states': sorted(inp.women_vote),
        'priors': prior_used,
        'no_popular': sorted(s for s, n in zip(states, no_pop) if n),
        'missing_returns': missing,
        'dropped_cell_states': dropped,
        'synthetic_cell_states': sorted({r['state'] for r in syn_rows}),
        'legal_rules_contradicted': contradict,
        'T_column_mismatch': t_mismatch,
        'zero_party': {p: [s for s, x, tv in zip(states, arr, T) if tv > 0 and x <= 0]
                       for p, arr in (('R', R), ('D', Dm), ('O', O))},
        'other_majority': [s for s, o, tv in zip(states, O, T) if tv > 0 and o > 0.5 * tv],
        'third_candidate_share_of_O': {s: float(p / o) for s, p, o in zip(states, P, O) if o > 0 and p > 0},
        'adults_scaled_share': dict(zip(states, scaled.tolist())),
        'turnout_shift': k,
        'women_turnout': vF / np.maximum(F, 1), 'men_turnout': vM / np.maximum(M, 1),
        'votes_F': vF, 'votes_M': vM, 'F20': F, 'M20': M, 'T20': T,
        'black_south_bound_on': bound_on,
        'black_south_bound_share': dict(zip(states, (bound_hits / D).tolist())),
    }
    params = {'delta': delta, 'beta_B': beta_B, 'beta_N': beta_N, 'beta_O': beta_O,
              't_black_south_rel': 1 - x_bs, 'turnout_shift': k, **{f'off_{k_}': v_ for k_, v_ in dr.items()}}
    return Fit(world=world, cells=cells, params=params, diagnostics=diag)
