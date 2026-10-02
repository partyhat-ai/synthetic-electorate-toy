"""From cell draws to states, electoral votes, ranges and the draw count.

A World is a set of draw-major arrays over cells (state × sex × group):
    adults [D, C]   adults 21+
    can    [D, C]   the fraction who can vote (legally and in practice)
    t      [D, C]   turnout among those who can
    share  [D, C, 3] R, D, O shares among voters
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

PARTIES = ['R', 'D', 'O']


@dataclass
class World:
    adults: np.ndarray
    can: np.ndarray
    t: np.ndarray
    share: np.ndarray
    # Split of the barred fraction by reason, for slices: {reason: [D, C]}
    barred_by: dict

    def copy(self) -> 'World':
        return replace(self, adults=self.adults.copy(), can=self.can.copy(), t=self.t.copy(),
                       share=self.share.copy(), barred_by={k: v.copy() for k, v in self.barred_by.items()})

    def votes(self) -> np.ndarray:
        """[D, C, 3] votes by cell."""
        return (self.adults * self.can * self.t)[..., None] * self.share


def by_state(world: World, state_index: np.ndarray, n_states: int) -> np.ndarray:
    """[D, S, 3] votes by state."""
    v = world.votes()
    out = np.zeros((v.shape[0], n_states, 3))
    for p in range(3):
        np.add.at(out[:, :, p], (slice(None), state_index), v[:, :, p])
    return out


def outcome(state_votes: np.ndarray, ev: np.ndarray, fixed: np.ndarray | None = None,
            split: np.ndarray | None = None, o_single: np.ndarray | None = None) -> dict:
    """state_votes [D, S, 3]; ev [S] (or [D, S] for reapportionment).
    A state with no votes in a draw (its legislature chose the electors) casts no
    electoral votes, unless fixed [S, 3] gives its electors by party (NaN rows: none):
    then they count as given, and its winner is the party with the most.
    split [S, 3] (NaN rows: none): a state whose electors historically divided (district
    systems, split tickets, ME/NE) divides them as it did while its plurality winner is
    the historical one; a state that flips goes winner-take-all. A fourth column in
    split, when present, is the historical popular winner (MD 1908 went R by 605 votes
    while 6 of its 8 electors were D).
    o_single [S]: the largest single candidate's share of "other" (O lumps several:
    Bell and Breckinridge in 1860); only that candidate can carry a state."""
    if o_single is not None:
        ranked = state_votes * np.concatenate([np.ones((len(o_single), 2)), np.asarray(o_single, dtype=float)[:, None]], axis=1)[None]
        winner = ranked.argmax(axis=2)
    else:
        winner = state_votes.argmax(axis=2)                       # [D, S]
    total = state_votes.sum(axis=2)
    srt = np.sort(state_votes, axis=2)
    margin = (srt[:, :, -1] - srt[:, :, -2]) / np.maximum(total, 1) * 100
    ev = np.broadcast_to(ev, winner.shape)
    none = total <= 0
    if none.any():
        ev = np.where(none, 0, ev)
    ev_by = np.stack([(ev * (winner == p)).sum(axis=1) for p in range(3)], axis=1)  # [D, 3]
    if split is not None:
        sp = np.asarray(split, dtype=float)
        has = ~np.isnan(sp).all(axis=1)
        if has.any():
            sp0 = np.nan_to_num(sp)
            hist = sp0[:, :3].argmax(axis=1)                  # [S] the party with most of the split electors
            if sp.shape[1] > 3:
                hist = np.where(np.isnan(sp[:, 3]), hist, np.nan_to_num(sp[:, 3])).astype(int)
                sp0 = sp0[:, :3]
            keep = has[None, :] & (winner == hist[None, :]) & ~none   # [D, S]
            # Replace those states' winner-take-all electors with the historical division.
            wta = np.stack([(ev * keep * (winner == p)) for p in range(3)], axis=2).sum(axis=1)
            ev_by = ev_by - wta.astype(ev_by.dtype) + (keep[:, :, None] * sp0[None, :, :]).sum(axis=1).astype(ev_by.dtype)
    if fixed is not None and none.any():
        fx = np.nan_to_num(np.asarray(fixed, dtype=float))
        has = ~np.isnan(np.asarray(fixed, dtype=float)).all(axis=1)
        use = none & has[None, :]                             # [D, S]
        ev_by = ev_by + (use[:, :, None] * fx[None, :, :]).sum(axis=1).astype(ev_by.dtype)
        winner = np.where(use, fx.argmax(axis=1)[None, :], winner)
        ev = np.where(use, fx.sum(axis=1)[None, :], ev)
    need = ev.sum(axis=1)[:, None] / 2
    nat_winner = np.where((ev_by > need).any(axis=1), ev_by.argmax(axis=1), -1)
    return {'winner': winner, 'margin': margin, 'ev': ev_by, 'national_winner': nat_winner,
            'popular': state_votes.sum(axis=1), 'total': total}


def summarize(out: dict, base_winner: np.ndarray, level: float = 0.8) -> dict:
    """Point = median draw; ranges = central `level` interval; draw counts."""
    lo, hi = (1 - level) / 2, 1 - (1 - level) / 2
    ev = out['ev']
    D = ev.shape[0]
    # The point run: the draw whose EV split is closest to the median split.
    med = np.median(ev, axis=0)
    point = int(np.argmin(np.abs(ev - med).sum(axis=1)))
    flipped = out['winner'] != base_winner[None, :]
    return {
        'draws': D,
        'point': point,
        'ev_point': ev[point].tolist(),
        'ev_range': {p: [float(np.quantile(ev[:, i], lo)), float(np.quantile(ev[:, i], hi))] for i, p in enumerate(PARTIES)},
        'draws_won': {p: int((out['national_winner'] == i).sum()) for i, p in enumerate(PARTIES)},
        'draws_no_majority': int((out['national_winner'] == -1).sum()),
        'state_winner_point': out['winner'][point].tolist(),
        'state_margin_point': out['margin'][point].tolist(),
        # additive: states with no popular vote in the point draw (legislature-chosen electors)
        'state_no_vote_point': (out['total'][point] <= 0).tolist() if 'total' in out else None,
        'state_margin_range': np.stack([np.quantile(out['margin'], lo, axis=0), np.quantile(out['margin'], hi, axis=0)], axis=1).tolist(),
        'state_p_flip': flipped.mean(axis=0).tolist(),
        'popular_point': out['popular'][point].tolist(),
        'popular_range': np.stack([np.quantile(out['popular'], lo, axis=0), np.quantile(out['popular'], hi, axis=0)], axis=1).tolist(),
        # Signed margin (R minus D, points) for flips and near misses
        'rd_margin': None,
    }


def rd_margin(state_votes: np.ndarray) -> np.ndarray:
    total = np.maximum(state_votes.sum(axis=2), 1)
    return (state_votes[:, :, 0] - state_votes[:, :, 1]) / total * 100
