"""The page's contract (api.js), plus additive fields the page may ignore.

Candidate keys follow history.js: A is the winner (1920: Harding, R), B the
runner-up (Cox, D), O everyone else.

Page slices (a partition: every adult 21+ is in exactly one):
  men          Men outside the South (citizens; all races)
  women        Women outside the South (citizens; all races)
  south-white  White Southerners (citizens; includes the few American Indian
               and Asian adults counted in the eleven Southern states)
  black-south  Black Southerners
  immigrants   Immigrants not yet citizens (every region)
"""
from __future__ import annotations

from dataclasses import MISSING, asdict, dataclass, field, fields
from typing import Any

import numpy as np

PARTY_TO_KEY = {0: 'A', 1: 'B', 2: 'O'}   # R → A (Harding), D → B (Cox)
DEM_WON = {0: 'B', 1: 'A', 2: 'O'}        # a D win (1960, 1964, 1976…): D → A, R → B


def key_map(base_ev_point) -> dict:
    """Party index → page key: A is the historical winner (history.js), B the other major party."""
    return DEM_WON if base_ev_point[1] > base_ev_point[0] else PARTY_TO_KEY


def _abo(d: dict) -> dict:
    return {k: d[k] for k in 'ABO' if k in d}

SLICES = [
    ('men', 'Men outside the South'),
    ('women', 'Women outside the South'),
    ('south-white', 'White Southerners'),
    ('black-south', 'Black Southerners'),
    ('immigrants', 'Immigrants not yet citizens'),
]


def slice_of(row) -> str:
    if row.group == 'foreign_white_alien':
        return 'immigrants'
    if row.south:
        return 'black-south' if row.group == 'black' else 'south-white'
    return 'men' if row.sex == 'M' else 'women'


def slices(fit, world, point: int, sources: dict, labels: dict | None = None, key_of: dict = PARTY_TO_KEY) -> list[dict]:
    """labels: the era's slice labels (agentlayer.groups_for(year)['slices']); default SLICES."""
    c = fit.cells
    keys = c.apply(slice_of, axis=1).to_numpy()
    out = []
    a = world.adults[point]
    can = world.can[point]
    t = world.t[point]
    sh = world.share[point]
    for key, label in SLICES:
        label = (labels or {}).get(key, label)
        m = keys == key
        n = a[m].sum()
        if n <= 0:
            continue
        barred = (a[m] * (1 - can[m])).sum() / n
        voted = a[m] * can[m] * t[m]
        home = (a[m] * can[m] * (1 - t[m])).sum() / n
        by_key = {key_of[p]: (voted * sh[m, p]).sum() / n for p in range(3)}
        A, B, O = by_key['A'], by_key['B'], by_key['O']
        out.append({
            'key': key, 'label': label, 'adults': round(n / 1e6, 3),
            'barred': round(float(barred), 4), 'home': round(float(home), 4),
            'A': round(float(A), 4), 'B': round(float(B), 4), 'O': round(float(O), 4),
            'source': sources.get(key),
        })
    return out


def states(names: list, summary: dict, base_winner: list, key_of: dict = PARTY_TO_KEY) -> list[dict]:
    out = []
    for i, code in enumerate(names):
        won = key_of[summary['state_winner_point'][i]]
        out.append({
            'code': code,
            'won': won,
            'flipped': summary['state_winner_point'][i] != base_winner[i],
            'margin': round(summary['state_margin_point'][i], 1),
            # additive
            'marginRange': [round(x, 1) for x in summary['state_margin_range'][i]],
            'pFlip': round(summary['state_p_flip'][i], 3),
        })
    return out


def result(*, names, summary, base_winner, slices_out, text, confidence, applied, extras, key_of: dict = PARTY_TO_KEY) -> dict:
    ev = _abo({key_of[i]: int(round(v)) for i, v in enumerate(summary['ev_point'])})
    nat = max(ev, key=ev.get) if max(ev.values()) > sum(ev.values()) / 2 else None
    return {
        'ev': ev,
        'winner': nat,
        'states': states(names, summary, base_winner, key_of),
        'slices': slices_out,
        'summary': text,
        'confidence': confidence,
        'applied': applied,
        'unknown': None,
        # additive
        'range': _abo({key_of[i]: [int(round(x)) for x in summary['ev_range'][p]] for i, p in enumerate('RDO')}),
        'drawsWon': _abo({key_of[i]: summary['draws_won'][p] for i, p in enumerate('RDO')}) | {
            'none': summary['draws_no_majority'], 'of': summary['draws']},
        'popular': _abo({key_of[i]: int(round(v)) for i, v in enumerate(summary['popular_point'])}),
        'popularRange': _abo({key_of[i]: [int(round(x)) for x in summary['popular_range'][i]] for i in range(3)}),
        **extras,
    }


def fmt_m(n: float) -> str:
    return f'{n / 1e6:.1f} million' if n >= 950_000 else f'{round(n / 1000):,},000'


def closest(names, state_names, summary, base_winner, flipped_only=False):
    """The state the change squeezed most: smallest point margin among states
    whose winner didn't change (or did, if flipped_only)."""
    best = None
    novote = summary.get('state_no_vote_point') or [False] * len(names)
    for i, code in enumerate(names):
        if novote[i]:
            continue  # the legislature chose the electors: no margin to speak of
        f = summary['state_winner_point'][i] != base_winner[i]
        if f != flipped_only:
            continue
        m = summary['state_margin_point'][i]
        if best is None or m < best[1]:
            best = (code, m, summary['state_winner_point'][i])
    return best


def headline_ev(summary, key_of: dict = PARTY_TO_KEY) -> str:
    """Electoral votes, the historical winner's party first (R–D(–O) when R won)."""
    by_key = {key_of[i]: int(round(x)) for i, x in enumerate(summary['ev_point'])}
    a, b, o = by_key['A'], by_key['B'], by_key['O']
    return f'{a}–{b}' + (f'–{o}' if o else '')


def winner_ev(summary, winner: int) -> str:
    """Electoral votes with the new winner first: "272–129" when the result flips."""
    ev = [int(round(x)) for x in summary['ev_point']]
    rest = sorted((i for i in range(3) if i != winner), key=lambda i: (i == 2, -ev[i]))
    out = [ev[winner]] + [ev[i] for i in rest if i != 2 or ev[i]]
    return '–'.join(str(x) for x in out)


def verdict(*, lead: str, names, state_names, cand, summary, base_summary, base_winner, key_of: dict = PARTY_TO_KEY) -> str:
    """The robot's sentence: what changed in people, then what it did."""
    flips = [names[i] for i in range(len(names)) if summary['state_winner_point'][i] != base_winner[i]]
    won = summary['draws_won']
    D = summary['draws']
    nat_point = int(np.argmax(summary['ev_point']))
    base_nat = int(np.argmax(base_summary['ev_point']))
    parts = [lead]
    if not flips and summary['ev_point'] == base_summary['ev_point'] and lead.startswith('Rerun with nothing changed'):
        near = closest(names, state_names, summary, base_winner)
        if near:
            parts.append(f'The closest state was {state_names[near[0]]}, which went to {cand[near[2]]} by {near[1]:.1f} points.')
        parts.append(f'Every one of my {D} reruns reproduces it exactly.')
        return ' '.join(parts)
    if nat_point != base_nat:
        parts.append(f'{cand[nat_point]} wins, {winner_ev(summary, nat_point)}.')
    elif flips:
        who = ', '.join(state_names[s] for s in flips[:4]) + (f' and {len(flips) - 4} more' if len(flips) > 4 else '')
        parts.append(f'{who} {"flip" if len(flips) > 1 else "flips"}, but {cand[base_nat]} still wins, {headline_ev(summary, key_of)}.')
    else:
        parts.append(f'No state flips. {cand[base_nat]} wins, {headline_ev(summary, key_of)}.')
    near = closest(names, state_names, summary, base_winner)
    if near and near[1] < 10:
        parts.append(f'The closest call is {state_names[near[0]]}, which holds for {cand[near[2]]} by {near[1]:.1f} points.')
    loser = 1 - base_nat if base_nat in (0, 1) else 1
    if cand[loser] != 'no candidate':  # an unopposed year (1789, 1792, 1820) has no runner-up
        parts.append(f'{cand[loser]} wins in {won["RDO"[loser]]} of {D} draws.')
    return ' '.join(parts)


# ── The bundle contract ──
# One per election, written by publish (runs/<id>/published/<year>.json, copied
# to serve/bundles/) and read by serve/simulacra.ts, which parses the same shape
# with zod. tests/fixtures/bundle.example.json is the shared example; both sides
# test against it. Keys are exactly what publish emits: a missing or unexpected
# key is an error, so the contract can't drift silently.

class BundleError(ValueError):
    pass


def _strict(cls, d: Any, where: str, **convert):
    if not isinstance(d, dict):
        raise BundleError(f'{where}: expected an object, got {type(d).__name__}')
    names = {f.name for f in fields(cls)}
    required = {f.name for f in fields(cls) if f.default is MISSING and f.default_factory is MISSING}
    missing, extra = required - d.keys(), d.keys() - names
    if missing or extra:
        raise BundleError(f'{where}: missing {sorted(missing)}, unexpected {sorted(extra)}')
    return cls(**{k: convert[k](v) if k in convert else v for k, v in d.items()})


def _list(conv, where: str):
    def go(xs):
        if not isinstance(xs, list):
            raise BundleError(f'{where}: expected a list')
        return [conv(x, f'{where}[{i}]') for i, x in enumerate(xs)]
    return go


@dataclass(frozen=True)
class Slice:
    """One page slice (`slices` above): fractions of the slice's adults; `adults` in millions."""
    key: str
    label: str
    adults: float
    barred: float
    home: float
    A: float
    B: float
    O: float  # noqa: E741
    source: Any  # the profile's source for the slice, or None

    @classmethod
    def from_dict(cls, d, where='slice'):
        return _strict(cls, d, where)


@dataclass(frozen=True)
class WhatIf:
    key: str
    label: str
    kind: str          # franchise | population | issue | candidate
    detail: str
    slices: list
    assumption: str
    confidenceTier: str  # high | medium | low | very-low
    evidence: str        # the evidence strength level
    exploratory: bool

    @classmethod
    def from_dict(cls, d, where='whatIf'):
        return _strict(cls, d, where)


@dataclass(frozen=True)
class Election:
    slices: list[Slice]
    whatIfs: list[WhatIf]

    @classmethod
    def from_dict(cls, d, where='election'):
        return _strict(cls, d, where, slices=_list(Slice.from_dict, f'{where}.slices'),
                       whatIfs=_list(WhatIf.from_dict, f'{where}.whatIfs'))


@dataclass(frozen=True)
class StateResult:
    code: str
    won: str            # A | B | O
    # A numpy bool written with json's default=float: published bundles carry 0.0 / 1.0.
    flipped: bool | float
    margin: float
    marginRange: list
    pFlip: float

    @classmethod
    def from_dict(cls, d, where='state'):
        return _strict(cls, d, where)


@dataclass(frozen=True)
class Result:
    """serialize.result plus publish's extras: one what-if combination."""
    ev: dict
    winner: str | None
    states: list[StateResult]
    slices: list[Slice]
    summary: str
    confidence: str      # the page's high | medium | low
    applied: list
    unknown: str | None
    range: dict
    drawsWon: dict
    popular: dict
    popularRange: dict
    assumptions: list
    howIGotThis: list
    sources: list
    confidenceTier: str
    confidenceLabel: str
    confidenceFlags: list
    confidenceReasons: list
    evidence: list
    mode: str
    runId: str
    validation: Any
    cohortEffects: list

    @classmethod
    def from_dict(cls, d, where='result'):
        return _strict(cls, d, where, states=_list(StateResult.from_dict, f'{where}.states'),
                       slices=_list(Slice.from_dict, f'{where}.slices'))


@dataclass(frozen=True)
class TableRow:
    """A state × slice row of one combination's point run (fractions of `adults`)."""
    state: str
    slice: str
    adults: float
    barred: float
    home: float
    A: float
    B: float
    O: float  # noqa: E741

    @classmethod
    def from_dict(cls, d, where='table'):
        return _strict(cls, d, where)


@dataclass(frozen=True)
class Words:
    key: str
    words: list

    @classmethod
    def from_dict(cls, d, where='words'):
        return _strict(cls, d, where)


@dataclass(frozen=True)
class Bundle:
    year: int
    runId: str
    election: Election
    runs: dict[str, Result]           # combination key ('' is history; 'a+b' sorted) → result
    tables: dict[str, list[TableRow]]  # same keys as runs
    voters: dict                       # combination key → slice key → one voter
    interviews: dict                   # {} or {questions, byWhatIf}
    ev: dict[str, int]
    historyWinner: dict[str, str]
    words: list[Words]
    # Bundles published before the briefs record (1916, 1924) lack these three.
    pre: dict | None = None
    told: dict = field(default_factory=dict)
    reading: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, d) -> 'Bundle':
        def runs(m):
            return {k: Result.from_dict(v, f'runs[{k!r}]') for k, v in m.items()}

        def tables(m):
            return {k: _list(TableRow.from_dict, f'tables[{k!r}]')(v) for k, v in m.items()}
        b = _strict(cls, d, 'bundle', election=Election.from_dict, runs=runs, tables=tables,
                    words=_list(Words.from_dict, 'words'))
        if set(b.runs) != set(b.tables):
            raise BundleError('bundle: runs and tables have different combination keys')
        if '' not in b.runs:
            raise BundleError('bundle: no unchanged run (key "")')
        return b

    def to_dict(self) -> dict:
        return asdict(self)
