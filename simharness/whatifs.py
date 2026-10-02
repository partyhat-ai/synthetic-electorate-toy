"""The what-ifs: each edits one layer of the calibrated world and names its
assumption, its mode (backbone-only or agent effect), and the settled facts a
counterfactual brief writes into a person's world.

Mode, by kind:
- franchise   backbone only. New voters turn out and choose like a named,
              observed group; agents supply quotes and a cross-check.
- population  backbone only, plus reapportionment from the counterfactual
              census (stats.huntington_hill / webster).
- issue       agent paired differences shift the groups the change reaches;
              shrunk by cohort bias (paired.py).
"""
from __future__ import annotations

import numpy as np

from .aggregate import World
from .geo import SOUTH, STATE_NAME
from .stats import expit, logit


def _northern_black_share(fit, world: World) -> np.ndarray:
    """[D, 3] vote shares of Black voters outside the South, this world."""
    c = fit.cells
    m = ((c.group == 'black') & ~c.south).to_numpy()
    v = (world.adults * world.can * world.t)[:, m]
    return (v[..., None] * world.share[:, m, :]).sum(axis=1) / np.maximum(v.sum(axis=1), 1e-9)[:, None]


def no_19th(fit, world: World, inp) -> World:
    w = world.copy()
    c = fit.cells
    m = ((c.sex == 'F') & ~c.state.isin(inp.women_pre19)).to_numpy()
    w.barred_by['legal'][:, m] = 1.0
    w.barred_by['excluded'][:, m] = 0.0
    w.can[:, m] = 0.0
    return w


def fifteenth(fit, world: World, inp) -> World:
    w = world.copy()
    c = fit.cells
    m = ((c.group == 'black') & c.south).to_numpy()
    w.can[:, m] = w.can[:, m] + w.barred_by['excluded'][:, m]
    w.barred_by['excluded'][:, m] = 0.0
    nb = _northern_black_share(fit, world)
    w.share[:, m, :] = nb[:, None, :]
    return w


def everyone(fit, world: World, inp) -> World:
    w = world.copy()
    c = fit.cells.reset_index(drop=True)
    nb = _northern_black_share(fit, world)
    bs = ((c.group == 'black') & c.south).to_numpy()
    w.share[:, bs, :] = nb[:, None, :]
    # Non-citizens choose like naturalized citizens of their own state and sex.
    key = {(r.state, r.sex): i for i, r in c.iterrows() if r.group == 'foreign_white_naturalized'}
    for i, r in c.iterrows():
        if r.group == 'foreign_white_alien' and (r.state, r.sex) in key:
            w.share[:, i, :] = world.share[:, key[(r.state, r.sex)], :]
    w.can[:] = 1.0
    w.t[:] = 1.0
    for k in w.barred_by:
        w.barred_by[k][:] = 0.0
    return w


def apply_effects(fit, world: World, cohort_of_cell: list, eff: dict) -> World:
    """Issue what-ifs: logit shifts per cohort, per draw (eff[k]['draws'])."""
    w = world.copy()
    D = w.t.shape[0]
    for i, k in enumerate(cohort_of_cell):
        if k not in eff or not (w.can[:, i] > 0).any():
            continue
        e = eff[k]['draws']
        j = np.arange(D) % len(e['dt'])
        dt, dr, do = e['dt'][j], e['dr'][j], e['do'][j]
        w.t[:, i] = expit(logit(w.t[:, i]) + dt)
        R, Dm, O = w.share[:, i, 0], w.share[:, i, 1], w.share[:, i, 2]
        r2 = expit(logit(R / np.maximum(R + Dm, 1e-12)) + dr)
        o = expit(logit(O) + do)
        w.share[:, i, 0] = (1 - o) * r2
        w.share[:, i, 1] = (1 - o) * (1 - r2)
        w.share[:, i, 2] = o
    return w


# ── Facts written into a counterfactual brief (never phrased as a change) ──

def facts_no_19th(agent: dict, inp) -> dict:
    s = agent['state']
    facts = ['In August the Tennessee legislature voted the woman suffrage amendment down, and it has not been ratified.']
    elig = None
    if agent['sex'] == 'F':
        if s in inp.women_pre19:
            elig = f'{STATE_NAME.get(s, s)} law already lets women vote for president, so this person can vote this year.'
        else:
            elig = f'Women cannot vote for president in {STATE_NAME.get(s, s)} this year.'
    # Items about women registering after the amendment's ratification would
    # contradict this world; drop them.
    drop = {'T1', 'T7'} if (agent['sex'] == 'F' and s not in inp.women_pre19) else set()
    return {'facts': facts, 'eligibility': elig, 'drop_topics': drop, 'drop_after': '1920-08-18'}


def facts_fifteenth(agent: dict, inp) -> dict:
    s = agent['state']
    if s not in SOUTH:
        return {'facts': [], 'eligibility': None, 'drop_topics': set()}
    facts = [f'Since the Supreme Court struck down {STATE_NAME.get(s, s)}\'s poll tax and registration test in 1919, and '
             'federal registrars were sent to every Southern county, Black citizens register and vote on the same '
             'terms as white citizens.']
    elig = None
    closed = getattr(inp, 'closed_1920', set())
    if agent['group'] == 'black':
        if agent['sex'] == 'F' and s in closed:
            elig = f'Registration in {STATE_NAME.get(s, s)} closed before women could enrol, so this person cannot vote for president this year.'
        else:
            elig = 'This person is registered and can vote this year.'
    return {'facts': facts, 'eligibility': elig, 'drop_topics': {'T5'} if agent['group'] == 'black' else set()}


def facts_league(agent: dict, inp) -> dict:
    return {
        'facts': ['In March 1920 the Senate ratified the peace treaty with its reservations, and the United States '
                  'took its seat in the League of Nations this spring. The treaty is settled, and neither party '
                  'proposes to reopen it.'],
        'eligibility': None,
        'drop_topics': {'T2'},
        'platform_override': {'League of Nations': None},  # both parties' League planks removed
    }


REGISTRY = {
    'no-19th': {
        'label': 'The 19th Amendment Fails', 'kind': 'franchise', 'mode': 'backbone', 'apply': no_19th,
        'facts': facts_no_19th, 'slices': ['women'],
        'detail': 'Tennessee votes the suffrage amendment down, so women can vote for president only where their own state already let them.',
        'assumption': 'Women in states without their own presidential suffrage can\'t vote. Everyone else turns out and chooses exactly as in 1920; men\'s votes don\'t change.',
        'borrowed': None,
    },
    'fifteenth': {
        'label': 'Enforce the 15th Amendment', 'kind': 'franchise', 'mode': 'backbone', 'apply': fifteenth,
        'facts': facts_fifteenth, 'slices': ['black-south'],
        'detail': 'Black Southerners vote as freely as white Southerners: no literacy tests, poll taxes or terror.',
        'assumption': 'Black adults in the eleven former Confederate states turn out at the rate white adults of their own state and sex did in 1920, and split like Black voters outside the South in 1920.',
        'borrowed': 'Black voters outside the South in 1920',
    },
    'league': {
        'label': 'The Senate Ratifies the League', 'kind': 'issue', 'mode': 'agents', 'apply': None,
        'facts': facts_league, 'slices': ['men', 'women', 'south-white', 'immigrants'],
        'detail': 'The Senate ratifies the peace treaty with its reservations in March 1920, and the League is no longer a campaign issue.',
        'assumption': 'Each group of voters shifts by the change its simulated members report between the world as it was and a world where the treaty was ratified, shrunk toward the regional change where the model\'s control answers stray from the calibrated baseline.',
        'borrowed': None,
    },
    'everyone': {
        'label': 'Everyone Votes', 'kind': 'franchise', 'mode': 'backbone', 'apply': everyone,
        'facts': None, 'slices': [],
        'detail': 'Every adult can vote, and turns out.',
        'assumption': 'Every adult votes. Non-citizens choose like naturalized citizens of their state and sex; Black Southerners like Black voters outside the South; everyone else as their group did in 1920.',
        'borrowed': 'naturalized citizens of the same state and sex; Black voters outside the South',
    },
}
