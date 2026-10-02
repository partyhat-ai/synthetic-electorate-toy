"""Small numeric tools: raking, apportionment, logit arithmetic, metrics."""
from __future__ import annotations

import math

import numpy as np
from scipy import stats as sps

EPS = 1e-6


def logit(p):
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


def expit(x):
    return 1 / (1 + np.exp(-x))


# ── Raking (iterative proportional fitting) ──

def ipf(seed: np.ndarray, margins: dict, tol: float = 1e-9, max_iter: int = 500) -> np.ndarray:
    """Rake `seed` (any shape) to the given margins.

    margins: {axes tuple: target array with that shape after summing the other
    axes}. Returns the fitted table. Cells that are zero in the seed stay zero
    (structural zeros are respected), which is how an impossible combination is
    kept impossible.
    """
    table = seed.astype(float).copy()
    for _ in range(max_iter):
        worst = 0.0
        for axes, target in margins.items():
            other = tuple(i for i in range(table.ndim) if i not in axes)
            current = table.sum(axis=other)
            ratio = np.divide(target, current, out=np.zeros_like(current, dtype=float), where=current > 0)
            shape = [table.shape[i] if i in axes else 1 for i in range(table.ndim)]
            table *= ratio.reshape(shape)
            worst = max(worst, float(np.max(np.abs(current - target))))
        if worst < tol * max(1.0, float(table.sum())):
            break
    return table


# ── Apportionment (for population what-ifs) ──

def huntington_hill(pops: dict, seats: int = 435, minimum: int = 1) -> dict:
    """Method of equal proportions (used for the House since the 1940 apportionment)."""
    alloc = {s: minimum for s in pops}
    import heapq
    heap = [(-p / math.sqrt(minimum * (minimum + 1)), s) for s, p in pops.items()]
    heapq.heapify(heap)
    for _ in range(seats - minimum * len(pops)):
        _, s = heapq.heappop(heap)
        alloc[s] += 1
        n = alloc[s]
        heapq.heappush(heap, (-pops[s] / math.sqrt(n * (n + 1)), s))
    return alloc


def webster(pops: dict, seats: int, minimum: int = 1) -> dict:
    """Major fractions (Webster/Sainte-Laguë), for eras that used it."""
    alloc = {s: minimum for s in pops}
    import heapq
    heap = [(-p / (2 * minimum + 1), s) for s, p in pops.items()]
    heapq.heapify(heap)
    for _ in range(seats - minimum * len(pops)):
        _, s = heapq.heappop(heap)
        alloc[s] += 1
        heapq.heappush(heap, (-pops[s] / (2 * alloc[s] + 1), s))
    return alloc


def electoral_votes(house: dict, dc: int = 0) -> dict:
    ev = {s: n + 2 for s, n in house.items()}
    if dc:
        ev['DC'] = dc
    return ev


# ── Metrics ──

def rmse(a, b, w=None) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    w = np.ones_like(a) if w is None else np.asarray(w, float)
    return float(np.sqrt(np.sum(w * (a - b) ** 2) / np.sum(w)))


def mae(a, b) -> float:
    return float(np.mean(np.abs(np.asarray(a, float) - np.asarray(b, float))))


def spearman(a, b) -> float:
    return float(sps.spearmanr(a, b).statistic)


def tvd(p, q) -> float:
    p, q = np.asarray(p, float), np.asarray(q, float)
    p, q = p / p.sum(), q / q.sum()
    return float(0.5 * np.abs(p - q).sum())


def brier(prob, outcome) -> float:
    prob, outcome = np.asarray(prob, float), np.asarray(outcome, float)
    return float(np.mean((prob - outcome) ** 2))


def interval(x, level: float = 0.8, axis=0):
    lo = (1 - level) / 2
    return np.quantile(x, lo, axis=axis), np.quantile(x, 1 - lo, axis=axis)


def bayes_ols(X: np.ndarray, y: np.ndarray, draws: int, rng: np.random.Generator,
              prior_mean=None, prior_sd=None):
    """Conjugate normal regression with an optional independent normal prior.

    Returns (beta_draws [draws × k], sigma_draws [draws], summary dict). With
    no prior this is the flat-prior posterior (a multivariate t for beta).
    """
    n, k = X.shape
    if prior_sd is None:
        P = np.zeros((k, k))
        m0 = np.zeros(k)
    else:
        P = np.diag(1 / np.asarray(prior_sd, float) ** 2)
        m0 = np.asarray(prior_mean, float)
    # Profile sigma from the flat-prior fit, then draw.
    beta_hat, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta_hat
    dof = max(n - k, 1)
    s2 = float(resid @ resid) / dof
    sig2 = s2 * dof / rng.chisquare(dof, size=draws)
    betas = np.empty((draws, k))
    for i, v in enumerate(sig2):
        A = X.T @ X / v + P
        cov = np.linalg.inv(A)
        mean = cov @ (X.T @ y / v + P @ m0)
        betas[i] = rng.multivariate_normal(mean, cov)
    return betas, np.sqrt(sig2), {'beta_hat': beta_hat.tolist(), 'resid_sd': math.sqrt(s2), 'n': n, 'k': k}
