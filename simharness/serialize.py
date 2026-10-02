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

PARTY_TO_KEY = {0: 'A', 1: 'B', 2: 'O'}   # R → A (Harding), D → B (Cox)

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


def slices(fit, world, point: int, sources: dict) -> list[dict]:
    c = fit.cells
    keys = c.apply(slice_of, axis=1).to_numpy()
    out = []
    a = world.adults[point]
    can = world.can[point]
    t = world.t[point]
    sh = world.share[point]
    for key, label in SLICES:
        m = keys == key
        n = a[m].sum()
        if n <= 0:
            continue
        barred = (a[m] * (1 - can[m])).sum() / n
        voted = a[m] * can[m] * t[m]
        home = (a[m] * can[m] * (1 - t[m])).sum() / n
        by_key = {PARTY_TO_KEY[p]: (voted * sh[m, p]).sum() / n for p in range(3)}
        A, B, O = by_key['A'], by_key['B'], by_key['O']
        out.append({
            'key': key, 'label': label, 'adults': round(n / 1e6, 3),
            'barred': round(float(barred), 4), 'home': round(float(home), 4),
            'A': round(float(A), 4), 'B': round(float(B), 4), 'O': round(float(O), 4),
            'source': sources.get(key),
        })
    return out


# ── The bundle contract ──
# One per election, written by the publish stage and read by the page, which
# parses the same shape with zod (src/lib/simulacra/schemas.ts).
# tests/fixtures/bundle.example.json is the shared example; both sides test
# against it. Keys are exactly what publish emits: a missing or unexpected
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
    """One what-if combination: the page's result shape plus additive fields."""
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
    # The briefs record: optional, so a bundle without it still parses.
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
