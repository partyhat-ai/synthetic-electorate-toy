"""Loaders for the harness cache. Benchmarks are not loaded here (see
benchmarks.py): the fitting code never imports them.

Files (all under config.CACHE; provenance in each folder's PROVENANCE-*.md):
  labels/state_pres_1916_1920_1924.csv     certified returns (labels)
  population/adults_1920_by_state.csv      1920 census, 21+, sex × race/nativity/citizenship
  population/adults_1910_by_state.csv      the same for 1910 (1916 interpolation)
  population/urban_rural_1920_by_state.csv urban share (persona diversity)
  franchise/state_franchise_1920.csv       poll tax, literacy test, alien voting
  franchise/women_suffrage_pre19th.csv     women's presidential suffrage before the 19th
  sources/corpus_1920.jsonl                dated Chronicling America items
  context/platforms_1920.json              verified platform planks

1924 (carried forward from 1920, backbone.carry_forward) reads the same files,
plus franchise/grayjenkins_state_franchise_1916_1920_1924.csv and its own
platforms (context/platforms_1924.json).
"""
from __future__ import annotations

import hashlib
import json
import re

import numpy as np
import pandas as pd

from .backbone import Inputs
from .config import CACHE
from .geo import STATES_1920

GROUP_MAP = {
    'native_white': 'native_white',
    'native_white_native_parentage': 'native_white',
    'native_white_foreign_parentage': 'native_white',
    'native_white_foreign_or_mixed_parentage': 'native_white',
    'native_white_mixed_parentage': 'native_white',
    'foreign_white_naturalized': 'foreign_white_naturalized',
    'foreign_white_first_papers': 'foreign_white_alien',
    'foreign_white_alien': 'foreign_white_alien',
    'foreign_white_unknown': 'foreign_white_unknown',
    'negro': 'black',
    'black': 'black',
    'other_races': 'other',
    'other': 'other',
    # 1910 women: citizenship wasn't asked of women in 1910.
    'foreign_white_citizenship_not_tabulated': 'foreign_white_unknown',
}


def manifest(paths: list) -> dict:
    out = {}
    for p in paths:
        f = CACHE / p
        if f.exists():
            out[p] = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
    return out


def returns(year: int = 1920):
    d = pd.read_csv(CACHE / 'labels/state_pres_1916_1920_1924.csv')
    out = {}
    for y in (1916, 1920, 1924):
        x = d[d.year == y].set_index('state')
        out[f'R{y % 100}'] = x.rep
        out[f'D{y % 100}'] = x.dem
        out[f'O{y % 100}'] = x.total - x.rep - x.dem
        out[f'T{y % 100}'] = x.total
        if y == 1924:
            out['P24'] = x.wp_progressive.fillna(0)  # La Follette's own votes within `other` (Wikipedia per-party column)
    r = pd.DataFrame(out).loc[STATES_1920].astype(float)
    x = d[d.year == year].set_index('state').loc[STATES_1920]
    # 1920: NARA's count; 1924: Algara–Amlani's electoral votes by party (same 1910 apportionment).
    ev = (x.nara_ev_total if year == 1920 else x.aa_state_ev_dem + x.aa_state_ev_rep + x.aa_state_ev_other).astype(int)
    assert int(ev.sum()) == 531
    return r, ev


def _long_pop(path) -> pd.DataFrame:
    p = pd.read_csv(path)
    p = p[p.state.isin(STATES_1920) & (p.group != 'TOTAL')].copy()
    p['group'] = p.group.map(lambda g: GROUP_MAP.get(g, g))
    return p.groupby(['state', 'sex', 'group'], as_index=False)['count'].sum()


def population(year: int = 1920) -> pd.DataFrame:
    """Cells state × sex × group with adults20 and adults16 (1916 by geometric
    interpolation between the 1910 and 1920 counts, truth mode). adults20 holds
    the election year's adults (the name is 1920's): for 1924, the 1920 count
    aged along the cell's 1910→1920 trend to November 1924 [I] (DISCLOSURES C13)."""
    p20 = _long_pop(CACHE / 'population/adults_1920_by_state.csv')
    f10 = CACHE / 'population/adults_1910_by_state.csv'
    p10 = _long_pop(f10) if f10.exists() else None
    # Unknown citizenship: split between naturalized and alien in the state-sex ratio.
    def resolve(p):
        """Unknown citizenship → naturalized/alien in the state-sex ratio; where a
        sex has no split at all (1910 women), the same state's men's ratio [I]:
        before 1922 a wife's citizenship followed her husband's."""
        rows = []
        split = {}
        for (s, x), g in p.groupby(['state', 'sex']):
            d = dict(zip(g.group, g['count']))
            nat, ali = d.get('foreign_white_naturalized', 0.0), d.get('foreign_white_alien', 0.0)
            if nat + ali > 0:
                split[s] = nat / (nat + ali)
        for (s, x), g in p.groupby(['state', 'sex']):
            d = dict(zip(g.group, g['count']))
            unk = d.pop('foreign_white_unknown', 0.0)
            nat, ali = d.get('foreign_white_naturalized', 0.0), d.get('foreign_white_alien', 0.0)
            share = nat / (nat + ali) if nat + ali > 0 else split.get(s, 0.5)
            if unk:
                d['foreign_white_naturalized'] = nat + unk * share
                d['foreign_white_alien'] = ali + unk * (1 - share)
            for k, v in d.items():
                rows.append({'state': s, 'sex': x, 'group': k, 'count': v})
        return pd.DataFrame(rows)
    p20 = resolve(p20)
    cells = p20.rename(columns={'count': 'adults20'})
    if p10 is not None:
        p10 = resolve(p10).rename(columns={'count': 'adults10'})
        cells = cells.merge(p10, on=['state', 'sex', 'group'], how='left')
        # Census days: 15 Apr 1910 and 1 Jan 1920 (9.71 years apart). Election
        # days: 7 Nov 1916 (6.56 years after the 1910 count) and 2 Nov 1920
        # (0.84 years after the 1920 count).
        ratio = (cells.adults20 / cells.adults10).where(cells.adults10 > 0)
        cells['adults16'] = np.where(ratio.notna(), cells.adults10 * ratio ** (6.56 / 9.71), cells.adults20 * 0.94)
        # Election day, in years after the 1 Jan 1920 count: 0.84 for 1920, 4.84 for 1924.
        after = 0.84 + (year - 1920)
        cells['adults20'] = np.where(ratio.notna(), cells.adults20 * ratio.clip(0.5, 2.0) ** (after / 9.71), cells.adults20)
        cells['interp'] = np.where(ratio.notna(), 'geometric 1910→1920, extrapolated to Nov 1920', 'fallback')
    else:
        cells['adults16'] = cells.adults20 * 0.94
        cells['interp'] = 'fallback: 1920 × 0.94 [I]'
    return cells.sort_values(['state', 'sex', 'group']).reset_index(drop=True)


def franchise(year: int = 1920) -> dict:
    f = pd.read_csv(CACHE / 'franchise/state_franchise_1920.csv')
    f = f[f.state.isin(STATES_1920)].set_index('state')
    if year != 1920:
        # The year's poll tax and literacy test from Gray & Jenkins (presidential rows).
        gj = pd.read_csv(CACHE / 'franchise/grayjenkins_state_franchise_1916_1920_1924.csv')
        gj = gj[(gj.year == year) & gj.state.isin(STATES_1920)].set_index('state')
        f['poll_tax'] = gj.poll_tax.reindex(f.index).fillna(f.poll_tax)
        f['literacy_test'] = gj.lit_test.reindex(f.index).fillna(f.literacy_test)
    w = pd.read_csv(CACHE / 'franchise/women_suffrage_pre19th.csv').set_index('state')
    pres = w.presidential_suffrage_year.combine_first(w.full_suffrage_year) if 'full_suffrage_year' in w else w.presidential_suffrage_year
    women16 = {s for s, y in pres.items() if pd.notna(y) and float(y) <= 1916}
    women_pre19 = {s for s, y in pres.items() if pd.notna(y) and float(y) <= 1920}
    alien = set(f.index[f.get('alien_declarant_voting', pd.Series(0, index=f.index)).fillna(0).astype(int) == 1])
    # Georgia and Mississippi: registration closed before women could enrol
    # (sources in franchise/state_franchise_1920.csv, women_nov1920_note).
    closed = set(f.index[f.women_able_to_vote_nov1920.fillna(1).astype(int) == 0]) if year == 1920 else set()
    return {'table': f, 'women16': women16, 'women_pre19': women_pre19, 'alien_voting': alien,
            'closed_1920': closed, 'pres_year': pres.to_dict()}


def urban_share() -> dict:
    f = CACHE / 'population/urban_rural_1920_by_state.csv'
    if not f.exists():
        return {}
    u = pd.read_csv(f)
    u = u[(u.year == 1920) & u.state.isin(STATES_1920)].pivot_table(index='state', columns='area', values='count', aggfunc='sum')
    return (u['urban'] / u['total']).to_dict()


NAMES = re.compile(r'\b(Harding|Cox|Coolidge|Roosevelt|Debs|Christensen|Republican|Democrat|G\.\s?O\.\s?P|Wilson)', re.I)


def corpus(cutoff: str, rel: str | None = 'sources/corpus_1920.jsonl', names=NAMES) -> list[dict]:
    rows = []
    path = CACHE / rel if rel else None
    if not path or not path.exists():
        return rows
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        it = json.loads(line)
        if it['date'] > cutoff:
            continue
        text = it['excerpt'].strip()
        it['identifying'] = bool(it.get('mentions_candidates')) or bool(names.search(text))
        it['text'] = ' '.join(text.split()[:120])
        rows.append(it)
    return rows


def platforms(rel: str = 'context/platforms_1920.json') -> dict:
    path = CACHE / rel
    return json.loads(path.read_text()) if path.exists() else {}


def inputs(year: int) -> tuple[Inputs, dict]:
    ret, ev = returns(year)
    cells = population(year)
    fr = franchise(year)
    return Inputs(cells=cells, returns=ret, women16=fr['women16'], women_pre19=fr['women_pre19'],
                  closed_1920=fr['closed_1920'], alien_voting=fr['alien_voting'], ev=ev), fr


def load(cfg) -> tuple[Inputs, dict]:
    from . import profiles
    prof = profiles.get(cfg.election)
    inp, fr = inputs(cfg.election)
    files = ['labels/state_pres_1916_1920_1924.csv', 'population/adults_1920_by_state.csv',
             'population/adults_1910_by_state.csv', 'franchise/state_franchise_1920.csv',
             'franchise/women_suffrage_pre19th.csv', 'sources/corpus_1920.jsonl', 'context/platforms_1920.json']
    if cfg.election != 1920:
        files += ['franchise/grayjenkins_state_franchise_1916_1920_1924.csv', prof['platforms']] + ([prof['corpus']] if prof['corpus'] else [])
        files.remove('sources/corpus_1920.jsonl')
        files.remove('context/platforms_1920.json')
    extras = {
        'franchise': fr,
        'urban': urban_share(),
        'corpus': corpus(cfg.context_cutoff, prof['corpus'], profiles.names_re(cfg.election)),
        'platforms': platforms(prof['platforms']),
        'profile': prof,
        # A carried-forward year fits its base year first (backbone.carry_forward).
        'base_inp': inputs(prof['base'])[0] if prof['base'] else None,
        'manifest': manifest(files),
    }
    return inp, extras
