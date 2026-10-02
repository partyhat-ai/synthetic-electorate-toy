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

General years (every election 1789–2024 except 1916/1920/1924, which keep the
files above and load exactly as before):
  labels/state_pres_all.csv                1868–2024 returns (scripts/build_returns.py)
  labels/state_pres_1789_1864.csv          1789–1864 returns (same columns)
  population/adults_<census>_by_state_nhgis.csv    21+ by census
  population/adults18_<census>_by_state_nhgis.csv  18+ (1950 on)
  franchise/state_franchise_all.csv        1868–1968 (scripts/build_franchise.py)
  franchise/state_franchise_1789_1864.csv, franchise/state_franchise_1972_2024.csv
"""
from __future__ import annotations

import hashlib
import json
import re

import numpy as np
import pandas as pd

from .backbone import Inputs
from .config import CACHE
from .geo import ALL_STATES, CODE_OF, STATES_1920

LEGACY = (1916, 1920, 1924)

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
    # Modern (ACS / decennial 1980 on).
    'white_nh_native': 'native_white',
    'naturalized': 'foreign_white_naturalized',
    'noncitizen': 'foreign_white_alien',
    'black_nh_native': 'black',
    'other_native': 'other',
    # Early republic (1790–1860).
    'white': 'native_white',
    'free_colored': 'black',
    'enslaved': 'black',
}


def manifest(paths: list) -> dict:
    out = {}
    for p in paths:
        f = CACHE / p
        if f.exists():
            out[p] = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
    return out


def _returns_legacy(year: int = 1920) -> pd.DataFrame:
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


def _population_legacy(year: int = 1920) -> pd.DataFrame:
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


def _franchise_legacy(year: int = 1920) -> dict:
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


# ---------------------------------------------------------------- general years

RETURNS_FILES = ['labels/state_pres_1789_1864.csv', 'labels/state_pres_all.csv']
FRANCHISE_FILES = ['franchise/state_franchise_1789_1864.csv', 'franchise/state_franchise_all.csv',
                   'franchise/state_franchise_1972_2024.csv']
# Electoral votes counted by Congress, 1868–2024 (scripts/build_returns.py KNOWN_EV).
KNOWN_EV = {1868: 294, 1872: 352, 1876: 369, 1880: 369, 1884: 401, 1888: 401, 1892: 444, 1896: 447, 1900: 447,
            1904: 476, 1908: 483, 1960: 537, **{y: 531 for y in range(1912, 1960, 4)},
            **{y: 538 for y in range(1964, 2025, 4)}}


def _year_rows(files: list, year: int, what: str) -> pd.DataFrame:
    frames = [pd.read_csv(CACHE / f) for f in files if (CACHE / f).exists()]
    d = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=['year', 'state'])
    x = d[d.year == year]
    if x.empty:
        missing = [f for f in files if not (CACHE / f).exists()]
        raise FileNotFoundError(f'no {what} rows for {year}; missing file(s): {missing}' if missing else
                                f'no {what} rows for {year} in {files}')
    return x.drop_duplicates('state', keep='last').set_index('state').sort_index()


def _returns_rows(year: int) -> pd.DataFrame:
    x = _year_rows(RETURNS_FILES, year, 'returns')
    ev = x.ev_total.fillna(0)
    return x[(x.chosen_by != 'none') | (ev > 0)]


def states(year: int) -> list:
    """States with a popular vote or electors that year."""
    if year in LEGACY:
        return list(STATES_1920)
    return list(_returns_rows(year).index)


def returns(year: int = 1920):
    """(R/D/O/T/P{yy} by state, electoral votes by state). Legislature states carry 0 votes."""
    if year in LEGACY:
        return _returns_legacy(year)
    x = _returns_rows(year)
    yy = year % 100
    v = x[['rep', 'dem', 'total', 'third']].astype(float).fillna(0.0)
    r = pd.DataFrame({f'R{yy}': v.rep, f'D{yy}': v.dem, f'O{yy}': (v.total - v.rep - v.dem).clip(lower=0),
                      f'T{yy}': v.total, f'P{yy}': v.third}).astype(float)
    r.index.name = None
    ev = x.ev_total.fillna(0).astype(int)
    if year < 1868:
        # Before 1868 count the electors who voted (1864 NV cast 2 of 3; 1820 MS 2 of 3).
        ev = x[['ev_rep', 'ev_dem', 'ev_other']].fillna(0).sum(axis=1).astype(int)
    ev.name = None
    ev.index.name = None
    if year in KNOWN_EV:
        # 1789–1864 (agent G's file) can have electors who didn't vote, so the
        # slot identity and the national total are checked from 1868 on.
        slots = x[['ev_rep', 'ev_dem', 'ev_other']].fillna(0).sum(axis=1).astype(int)
        assert (slots == ev).all(), f'{year}: ev_total != ev_rep + ev_dem + ev_other in {list(ev.index[slots != ev])}'
        assert int(ev.sum()) == KNOWN_EV[year], f'{year}: {int(ev.sum())} electoral votes, expected {KNOWN_EV[year]}'
    return r, ev


def _voting_age_rule(state: str, year: int) -> int:
    if year >= 1972:
        return 18
    if (state == 'GA' and year >= 1944) or (state == 'KY' and year >= 1956):
        return 18
    if year >= 1960 and state in ('AK', 'HI'):
        return {'AK': 19, 'HI': 20}[state]
    return 21


def _election_day(year: int) -> pd.Timestamp:
    """First Tuesday after the first Monday in November (1848 on); 1 Nov before [I]."""
    if year < 1848:
        return pd.Timestamp(year, 11, 1)
    d = pd.Timestamp(year, 11, 2)
    return d + pd.Timedelta(days=(1 - d.weekday()) % 7)


def _census_day(c: int) -> pd.Timestamp:
    if c % 10:
        return pd.Timestamp(c, 7, 1)  # ACS year: mid-year estimate [I]
    if c <= 1820:
        return pd.Timestamp(c, 8, 2)  # first Monday in August (1790–1820)
    if c <= 1900:
        return pd.Timestamp(c, 6, 1)
    return {1910: pd.Timestamp(1910, 4, 15), 1920: pd.Timestamp(1920, 1, 1)}.get(c, pd.Timestamp(c, 4, 1))


def _pop_path(c: int, age: int):
    """The census file for year c and age floor (21 or 18), or None."""
    names = [f'population/adults18_{c}_by_state_nhgis.csv'] if age == 18 else \
        ([f'population/adults_{c}_by_state.csv'] if c in (1910, 1920) else []) + [f'population/adults_{c}_by_state_nhgis.csv']
    for n in names:
        if (CACHE / n).exists():
            return n
    return None


def _census_years(age: int) -> list:
    """Decennial censuses 1790–2020 plus any ACS years with a file."""
    import glob
    pat = 'adults18_*_by_state_nhgis.csv' if age == 18 else 'adults_*_by_state_nhgis.csv'
    found = {int(m.group(1)) for f in glob.glob(str(CACHE / 'population' / pat))
             if (m := re.search(r'_(\d{4})_by_state', f))}
    return sorted(set(range(1790, 2021, 10)) | found)


def _resolve(p: pd.DataFrame) -> pd.DataFrame:
    """Unknown citizenship → naturalized/alien in the state-sex ratio; else the same
    state's other sex; else 0.5 [I] (1850–1860, before citizenship was asked)."""
    rows, split = [], {}
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


_POP_CACHE: dict = {}


def _census(c: int, age: int) -> pd.Series:
    """Resolved counts by (state, sex, group) for census c, age floor 21 or 18."""
    key = (c, age)
    if key not in _POP_CACHE:
        rel = _pop_path(c, age)
        if rel is None:
            raise FileNotFoundError(f'population file missing: population/adults{"18" if age == 18 else ""}_{c}_by_state_nhgis.csv')
        p = pd.read_csv(CACHE / rel)
        p = p[p.state.isin(ALL_STATES) & (p.group != 'TOTAL')].copy()
        p['group'] = p.group.map(lambda g: GROUP_MAP.get(g, g))
        p = p.groupby(['state', 'sex', 'group'], as_index=False)['count'].sum()
        _POP_CACHE[key] = (_resolve(p).groupby(['state', 'sex', 'group'])['count'].sum(), rel)
    return _POP_CACHE[key][0]


def _brackets(year: int, age: int) -> tuple[int, int]:
    """The two censuses to interpolate (or extrapolate) from for election day."""
    t = _election_day(year)
    cs = [c for c in _census_years(age) if c % 10 == 0 or _pop_path(c, age)]
    before = [c for c in cs if _census_day(c) <= t]
    after = [c for c in cs if _census_day(c) > t]
    if before and after:
        return before[-1], after[0]
    if before:  # after the last census: the last two (an ACS year counts)
        have = [c for c in before if _pop_path(c, age)]
        if before[-1] not in have:
            raise FileNotFoundError(f'population file missing: {_missing(before[-1], age)}')
        return have[-2], have[-1]
    return after[0], after[1]  # before 1790


def _missing(c, age):
    return f'population/adults{"18" if age == 18 else ""}_{c}_by_state_nhgis.csv'


def _interp(year: int, age: int) -> tuple[pd.Series, pd.Series, list]:
    """Counts at election day by (state, sex, group): geometric between the two
    bracketing censuses; beyond them, the decade's trend with the ratio capped to
    [0.5, 2] [I]. A cell missing from one census carries the other's count [I]."""
    c0, c1 = _brackets(year, age)
    a, b = _census(c0, age), _census(c1, age)
    t, t0, t1 = _election_day(year), _census_day(c0), _census_day(c1)
    f = (t - t0).days / (t1 - t0).days
    idx = a.index.union(b.index)
    a, b = a.reindex(idx), b.reindex(idx)
    ratio = (b / a).where((a > 0) & (b > 0))
    inside = 0 <= f <= 1
    rr = ratio if inside else ratio.clip(0.5, 2.0)
    geo = a * rr ** f
    lin = a.fillna(0) + (b.fillna(0) - a.fillna(0)) * f
    first, second = (b, a) if f >= 0.5 else (a, b)
    near = first.fillna(second)
    out = geo.where(ratio.notna(), lin.where(a.notna() & b.notna(), near)).clip(lower=0)
    how = pd.Series(np.where(ratio.notna(), f'geometric {c0}→{c1}' + ('' if inside else ', extrapolated'),
                             np.where(a.notna() & b.notna(), f'linear {c0}→{c1} [I]', f'fallback: one census of {c0}/{c1} [I]')),
                    index=idx)
    return out, how, [_POP_CACHE[(c0, age)][1], _POP_CACHE[(c1, age)][1]]


def _ages(year: int, sts: list) -> dict:
    try:
        fr = _year_rows(FRANCHISE_FILES, year, 'franchise')
        va = fr.voting_age.reindex(sts)
    except (FileNotFoundError, AttributeError):
        va = pd.Series(np.nan, index=sts)
    return {s: int(va[s]) if pd.notna(va.get(s)) else _voting_age_rule(s, year) for s in sts}


def _pop_general(year: int) -> tuple[pd.DataFrame, list]:
    sts = states(year)
    ages = _ages(year, sts)
    need21 = any(a > 18 for a in ages.values())
    need18 = any(a < 21 for a in ages.values())
    files = []
    p21 = p18 = None
    if need21:
        p21, h21, f = _interp(year, 21)
        files += f
    if need18:
        try:
            p18, h18, f = _interp(year, 18)
            files += f
        except FileNotFoundError:
            if year >= 1952 or p21 is None:
                raise
            # No 18+ census before 1950: 21+ × the 1950 18+/21+ ratio of the cell [I].
            r50 = (_census(1950, 18) / _census(1950, 21)).replace([np.inf], np.nan)
            p18 = p21 * r50.reindex(p21.index).fillna(1.065)
            h18 = h21 + ' × 1950 18+/21+ ratio [I]'
            files += [_POP_CACHE[(1950, 18)][1], _POP_CACHE[(1950, 21)][1]]
    rows = []
    for s in sts:
        a = ages[s]
        if a >= 21:
            n, h = p21, h21
        elif a == 18:
            n, h = p18, h18
        else:  # 19, 20: linear between the 18+ and 21+ counts [I]
            n = p21 + (p18.reindex(p21.index) - p21) * (21 - a) / 3
            h = h21 + f' / {a}+ linear between 18+ and 21+ [I]'
        if s not in n.index.get_level_values(0):
            raise FileNotFoundError(f'{year}: no census cells for {s} in {sorted(set(files))}')
        x = n.loc[s]
        hh = h.loc[s]
        for (sex, g), v in x.items():
            rows.append({'state': s, 'sex': sex, 'group': g, 'adults20': float(v), 'interp': hh.loc[(sex, g)]})
    cells = pd.DataFrame(rows)
    cells['adults16'] = cells.adults20
    cells = cells[['state', 'sex', 'group', 'adults20', 'adults16', 'interp']]
    return cells.sort_values(['state', 'sex', 'group']).reset_index(drop=True), sorted(set(files))


def population(year: int = 1920) -> pd.DataFrame:
    """Cells state × sex × group. adults20 = adults at the election (the name is
    1920's); adults16 = adults20 for general years."""
    if year in LEGACY:
        return _population_legacy(year)
    return _pop_general(year)[0]


def _other_citizen(year: int, sts: list) -> dict:
    """Citizen (legally voting) share of 'other' adults, mostly American Indians [I]:
    before the 1887 Dawes Act few were citizens; by 1924 about two-thirds were;
    the 1924 Indian Citizenship Act made all citizens, but AZ and NM barred
    reservation Indians until 1948. 1916/1920/1924 keep the legacy (none)."""
    if year < 1888:
        v = 0.2
    elif year < 1924:
        v = 0.6
    else:
        v = 1.0
    out = {s: v for s in sts} if v < 1 else {}
    if 1924 <= year < 1948:
        out.update({s: 0.2 for s in ('AZ', 'NM') if s in sts})
    return out


def franchise(year: int = 1920) -> dict:
    if year in LEGACY:
        return _franchise_legacy(year)
    sts = states(year)
    try:
        f = _year_rows(FRANCHISE_FILES, year, 'franchise')
        fallback = False
    except FileNotFoundError:
        if year < 1972:
            raise
        # Modern rules are uniform enough to default [I]: all adults 18+, no tests.
        f = pd.DataFrame({'poll_tax': 0, 'literacy_test': 0, 'alien_voting': 0, 'women_vote': 1, 'white_can': 1.0,
                          'black_can': 1.0, 'felony_disenfranchised_share': np.nan, 'voting_age': 18,
                          'chosen_by': 'popular', 'source': 'default [I]', 'note': ''}, index=pd.Index(sts, name='state'))
        fallback = True
    f = f.reindex(sts)
    w = pd.read_csv(CACHE / 'franchise/women_suffrage_pre19th.csv').set_index('state')
    pres = w.presidential_suffrage_year.combine_first(w.full_suffrage_year) if 'full_suffrage_year' in w else w.presidential_suffrage_year
    women16 = {s for s, y in pres.items() if pd.notna(y) and float(y) <= 1916}
    women_pre19 = {s for s, y in pres.items() if pd.notna(y) and float(y) <= 1920}

    def flag(col):
        return set(f.index[f[col].fillna(0).astype(float) == 1]) if col in f else set()
    rows = _returns_rows(year)
    slots = rows[['ev_rep', 'ev_dem', 'ev_other']].fillna(0).astype(int)
    leg = rows.chosen_by == 'legislature'
    # Electors by party where the legislature chose them, and where a popular-vote
    # state divided them (district plans, split slates, faithless electors).
    # A popular-vote state with no surviving count (KY 1792, PA 1812…) keeps its history's electors too.
    novote = rows.total.fillna(0) <= 0
    ev_fixed = {s: tuple(int(v) for v in slots.loc[s]) for s in rows.index[leg | novote] if slots.loc[s].sum() > 0}
    # A divided state, or one whose electors went against the recorded plurality (before
    # 1824 voters often chose slates, not candidates: MA 1820's "other" slate voted Monroe),
    # keeps the historical division while the recorded plurality winner holds.
    v = rows[['rep', 'dem']].fillna(0).astype(float)
    oth, thr = rows.other.fillna(0).astype(float), rows.third.fillna(0).astype(float).clip(upper=rows.other.fillna(0))
    vote_win = pd.concat([v.rep, v.dem, pd.concat([thr, oth - thr], axis=1).max(axis=1)], axis=1).to_numpy().argmax(axis=1)
    ev_split = {s: tuple(int(x) for x in slots.loc[s]) for i, s in enumerate(rows.index)
                if not leg.iloc[i] and not novote.iloc[i] and slots.loc[s].sum() > 0
                and ((slots.loc[s] > 0).sum() > 1 or int(slots.loc[s].to_numpy().argmax()) != int(vote_win[i]))}
    felony = {}
    if 'felony_disenfranchised_share' in f:
        felony = {s: float(v) for s, v in f.felony_disenfranchised_share.items() if pd.notna(v)}
    return {'table': f, 'women16': women16, 'women_pre19': women_pre19, 'alien_voting': flag('alien_voting'),
            'closed_1920': set(), 'pres_year': pres.to_dict(), 'women_vote': flag('women_vote'),
            'fallback': fallback, 'ev_fixed': ev_fixed, 'ev_split': ev_split, 'felony_share': felony,
            'enslaved_share': _enslaved_share(year)}


def _enslaved_share(year: int) -> dict:
    """state → enslaved share of Black adults, from the last census before the
    election (1790–1860); empty from 1868 on."""
    if year >= 1866:
        return {}
    c = max([1790] + [c for c in range(1790, 1861, 10) if c <= year])
    f = CACHE / f'population/adults_{c}_by_state_nhgis.csv'
    if not f.exists():
        return {}
    p = pd.read_csv(f)
    b = p[p.group.isin(['enslaved', 'free_colored'])].pivot_table(index='state', columns='group', values='count', aggfunc='sum').fillna(0)
    if 'enslaved' not in b:
        return {}
    tot = b.sum(axis=1)
    return {s: float(b.enslaved[s] / tot[s]) for s in b.index if tot[s] > 0}


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
    if year in LEGACY:
        return Inputs(cells=cells, returns=ret, women16=fr['women16'], women_pre19=fr['women_pre19'],
                      closed_1920=fr['closed_1920'], alien_voting=fr['alien_voting'], ev=ev, year=year), fr
    t = fr['table']
    sts = list(ret.index)

    def can(col):
        v = t[col].astype(float) if col in t else pd.Series(1.0, index=t.index)
        return {s: float(x) for s, x in v.items() if pd.notna(x) and float(x) < 1}
    no_pop = set(t.index[t.chosen_by == 'legislature']) if 'chosen_by' in t else set()
    rows = _returns_rows(year)
    no_pop |= set(rows.index[rows.chosen_by == 'legislature'])
    return Inputs(cells=cells, returns=ret, women16=fr['women16'], women_pre19=fr['women_pre19'],
                  closed_1920=set(), alien_voting=fr['alien_voting'], ev=ev,
                  other_citizen=_other_citizen(year, sts), year=year, women_vote=fr['women_vote'],
                  voting_age=18 if year >= 1972 else 21, black_can=can('black_can'), white_can=can('white_can'),
                  no_popular=no_pop), fr


def _files(year: int) -> list:
    """Cache files a general year reads (for the manifest)."""
    out = [RETURNS_FILES[0] if year < 1868 else RETURNS_FILES[1],
           FRANCHISE_FILES[0] if year < 1868 else FRANCHISE_FILES[1] if year < 1972 else FRANCHISE_FILES[2]]
    out = [f for f in out if (CACHE / f).exists()]
    try:
        out += _pop_general(year)[1]
    except FileNotFoundError:
        pass
    return out + ['franchise/women_suffrage_pre19th.csv']


def load(cfg) -> tuple[Inputs, dict]:
    from . import profiles
    prof = profiles.get(cfg.election)
    inp, fr = inputs(cfg.election)
    files = ['labels/state_pres_1916_1920_1924.csv', 'population/adults_1920_by_state.csv',
             'population/adults_1910_by_state.csv', 'franchise/state_franchise_1920.csv',
             'franchise/women_suffrage_pre19th.csv', 'sources/corpus_1920.jsonl', 'context/platforms_1920.json']
    if cfg.election not in LEGACY:
        files = _files(cfg.election) + [prof['platforms']] + ([prof['corpus']] if prof['corpus'] else [])
    elif cfg.election != 1920:
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
