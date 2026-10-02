"""NHGIS 1940–1970 → population tables (21+ and 18+), long format like
adults_1920_by_state.csv. Plugs into build_population.py via BUILDERS (21+).

    python3 scripts/harness/build_population.py 1950           # 21+ only, via the shared entry point
    python3 scripts/harness/build_population_mid.py            # 21+ and 18+ for 1940 1950 1960 1970
    python3 scripts/harness/build_population_mid.py 1960 1970  # just those years

Writes CACHE/population/adults_<y>_by_state_nhgis.csv (21+) and
adults18_<y>_by_state_nhgis.csv (18+; 1950 onward). Every value that is not a
straight tabulation carries an [I] note saying how it was estimated.

What each census gives (state level, NHGIS extract 1):
  1940  21+ by race × sex (cAge NT7); white 21+ by nativity × sex (cAge NT10);
        FB white 21+ by sex × citizenship (cPHAE NT12). Complete.
  1950  race (white / nonwhite) × sex × 5-yr age (cAge NT18); total 21+ (NT6, cPHA NT8);
        21+ by nativity, FB 21+ by citizenship, both sexes and all races (cPHA NT9A/9B);
        nonwhite 21+ by sex (cPHA NT48). Hawaii is blank in every 1950 table → omitted.
  1960  white / nonwhite × sex × 5-yr age (cAge1 NT11); nonwhite 21+ by sex (cPop NT14).
  1970  sex × single years to 21 (Cnt1 NT18); Negro / other × sex × 10-yr age (NT19).
"""
import functools
import sys

import numpy as np
import pandas as pd

from build_population import COLS, NHGIS_URL, SRC  # noqa: F401  (also puts HERE on sys.path)
from simharness.config import CACHE
from simharness.geo import CODE_OF

TERR = {'alaska': 'AK', 'alaska territory': 'AK', 'hawaii': 'HI', 'hawaii territory': 'HI'}


def read(ds: str, territories: bool) -> pd.DataFrame:
    f = next(SRC.glob(f'nhgis0001_{ds}_*_state.csv'))
    d = pd.read_csv(f, encoding='latin-1', skiprows=[1])
    code = {k.casefold(): v for k, v in CODE_OF.items()}
    code = {k: v for k, v in code.items() if v not in ('AK', 'HI')}  # geo may or may not list them yet
    if territories:
        code.update(TERR)
    d = d[d.STATE.str.casefold().isin(code)].copy()
    d['state'] = d.STATE.str.casefold().map(code)
    assert d.state.is_unique and len(d) == (len(set(code.values()))), (ds, len(d))
    return d.set_index('state')


def cols(prefix, a, b):
    return [f'{prefix}{i:03d}' for i in range(a, b + 1)]


def close(a, b, what, tol=1.0):
    gap = (pd.Series(a) - pd.Series(b)).abs().dropna()
    assert gap.max() < tol, f'{what}: off by {gap.max()} ({gap.idxmax()})'


def tab(label, table, note='tabulated'):
    return {'label': label, 'table': table, 'note': note}


def emit(year, cells):
    """cells: {(sex, group): (Series by state, meta)} → long DataFrame."""
    out = []
    for (sex, group), (s, m) in cells.items():
        for st, v in s.dropna().items():
            out.append({'year': year, 'state': st, 'sex': sex, 'group': group,
                        'race_as_recorded': m['label'].split(':')[0], 'label_as_recorded': m['label'],
                        'count': round(float(v), 1), 'vintage_mode': 'truth', 'note': m['note'],
                        'source_table': m['table'], 'source_url': NHGIS_URL, 'page': ''})
    return pd.DataFrame(out, columns=COLS).sort_values(['state', 'sex', 'group'], kind='stable').reset_index(drop=True)


# ---------------------------------------------------------------- 1940 (complete)
@functools.lru_cache(None)
def y1940():
    a, b = read('ds77', False), read('ds78', False)
    sx = {'M': 0, 'F': 1}
    for s, i in sx.items():
        wh, ng, ot = a[f'BV300{1+i}'], a[f'BV300{3+i}'], a[f'BV300{5+i}']
        nw, fw = a[f'BVV00{1+i}'], a[f'BVV00{3+i}']
        close(nw + fw, wh, f'1940 {s} white nativity vs NT7 white')
        close(wh + ng + ot, b[f'BYU00{1+i}'], f'1940 {s} NT7 races vs cPHAE NT8 total')
        fbw = b[cols('BWN', 1 + 4 * i, 4 + 4 * i)].sum(axis=1)
        close(fbw, fw, f'1940 {s} cPHAE NT12 citizenship vs cAge NT10 foreign-born white')
        fb = b[cols('BV8', 1 + 3 * i, 3 + 3 * i)].sum(axis=1)
        close(b[f'BY500{1+i}'] + fb, b[f'BYU00{1+i}'], f'1940 {s} native + foreign vs total')
    cells = {}
    for s, i in sx.items():
        t7, t10, t12 = 'NHGIS 1940_cAge NT7', 'NHGIS 1940_cAge NT10', 'NHGIS 1940_cPHAE NT12'
        nat, fp, al, unk = cols('BWN', 1 + 4 * i, 4 + 4 * i)
        cells[(s, 'native_white')] = (a[f'BVV00{1+i}'], tab('White: Native-born', t10))
        cells[(s, 'foreign_white_naturalized')] = (b[nat], tab('White: Foreign-born, naturalized', t12))
        cells[(s, 'foreign_white_first_papers')] = (b[fp], tab('White: Foreign-born, with first papers', t12))
        cells[(s, 'foreign_white_alien')] = (b[al], tab('White: Foreign-born, with no papers', t12))
        cells[(s, 'foreign_white_unknown')] = (b[unk], tab('White: Foreign-born, citizenship not reported', t12))
        cells[(s, 'negro')] = (a[f'BV300{3+i}'], tab('Negro: Negro', t7))
        cells[(s, 'other_races')] = (a[f'BV300{5+i}'], tab('Other: Other races', t7))
    return emit(1940, cells)


# ---------------------------------------------------------------- helpers 1950–1970
def neg_share_1940():
    """Negro share of nonwhite 21+, by state and sex (states only; territories blank by race)."""
    a = read('ds77', False)
    return {s: (a[f'BV300{3+i}'] / (a[f'BV300{3+i}'] + a[f'BV300{5+i}'])) for s, i in (('M', 0), ('F', 1))}


@functools.lru_cache(None)
def c1970():
    """1970 counts by sex: total, negro, other at 21+ and 18–20. NT19's 15–24 band
    is split by the total population's single-year shape within 15–24 [I]."""
    c = read('ds94', True)
    r = {}
    for s, o in (('M', 0), ('F', 22)):
        t = c[cols('CBT', 1 + o, 22 + o)].fillna(0).to_numpy()
        tot15_24 = t[:, 6:14].sum(axis=1)
        f21 = t[:, 12:14].sum(axis=1) / tot15_24  # 21, 22–24 of 15–24
        f18 = t[:, 9:12].sum(axis=1) / tot15_24   # 18, 19, 20
        r[(s, 'tot21')] = pd.Series(t[:, 12:].sum(axis=1), c.index)
        r[(s, 'tot18_20')] = pd.Series(t[:, 9:12].sum(axis=1), c.index)
        for g, base in (('negro', 1 if s == 'M' else 9), ('other_races', 17 if s == 'M' else 25)):
            u = c[cols('CBU', base, base + 7)].fillna(0).to_numpy()
            assert (u[:, 2] <= tot15_24 + 1).all()
            r[(s, g + '21')] = pd.Series(u[:, 3:].sum(axis=1) + u[:, 2] * f21, c.index)
            r[(s, g + '18_20')] = pd.Series(u[:, 2] * f18, c.index)
    return r


def neg_share(year):
    """[I] Negro share of nonwhite 21+: linear in time between 1940 (NT7) and 1970 (NT19);
    1970 alone where 1940 has no race split (AK, HI)."""
    c = c1970()
    s40 = neg_share_1940()
    w = (year - 1940) / 30
    out = {}
    for s in ('M', 'F'):
        s70 = c[(s, 'negro21')] / (c[(s, 'negro21')] + c[(s, 'other_races21')])
        out[s] = ((1 - w) * s40[s].reindex(s70.index) + w * s70).fillna(s70).fillna(1.0)
    return out


def ipf(seed, rows, colm, n=50):
    t = seed.astype(float) + 1e-9
    for _ in range(n):
        t *= (rows / t.sum(1))[:, None]
        t *= colm / t.sum(0)
    return t


# ---------------------------------------------------------------- 1950
@functools.lru_cache(None)
def y1950():
    a, b = read('ds83', True), read('ds84', True)
    a, b = a.drop('HI'), b.drop('HI')  # Hawaii Territory is blank in every 1950 table of the extract
    close(a.B14001, b.B37001, '1950 NT6 vs cPHA NT8 21+')
    close(b[['B4J001', 'B4J002']].sum(axis=1), b.B37001, '1950 nativity vs total 21+')
    close(b[cols('B4K', 1, 3)].sum(axis=1), b.B4J002, '1950 citizenship vs foreign-born 21+')
    band = {}
    for (race, s), o in ((('W', 'M'), 0), (('W', 'F'), 17), (('N', 'M'), 34), (('N', 'F'), 51)):
        x = a[cols('B1W', 1 + o, 17 + o)].fillna(0).to_numpy()
        band[(race, s, 21)] = pd.Series(x[:, 5:].sum(axis=1) + 0.8 * x[:, 4], a.index)
        band[(race, s, 18)] = pd.Series(0.4 * x[:, 3] + 0.2 * x[:, 4], a.index)
    est21 = sum(band[(r, s, 21)] for r in 'WN' for s in 'MF')
    rel = (est21 / a.B14001 - 1)
    print(f'1950 band-split 21+ vs NT6: national {est21.sum():,.0f} vs {a.B14001.sum():,.0f}; '
          f'state rel. error max {rel.abs().max():.4f} ({rel.abs().idxmax()})')
    nwx = b[['B3C001', 'B3C002']].sum(axis=1)
    nwe = band[('N', 'M', 21)] + band[('N', 'F', 21)]
    print(f'1950 nonwhite 21+: NT48 {nwx.sum():,.0f} vs band-split {nwe.sum():,.0f}')
    # Nonwhite 21+ by sex: NT48 where present, else band split. White total: NT6 − nonwhite; sex split by bands.
    nw, nw_note = {}, {}
    for s, col in (('M', 'B3C001'), ('F', 'B3C002')):
        nw[s] = b[col].fillna(band[('N', s, 21)])
        nw_note[s] = b[col].isna()
    wt = a.B14001 - nw['M'] - nw['F']
    wsh = band[('W', 'M', 21)] / (band[('W', 'M', 21)] + band[('W', 'F', 21)])
    wh = {'M': wt * wsh, 'F': wt * (1 - wsh)}
    # Foreign-born white 21+ by sex: 1950 foreign-born 21+ (all races) × 1940's FB-white-by-sex / FB-total ratio.
    e = read('ds78', True)
    fb40 = e[cols('BV8', 1, 6)].sum(axis=1)
    fbw40 = {'M': e[cols('BWN', 1, 4)].sum(axis=1), 'F': e[cols('BWN', 5, 8)].sum(axis=1)}
    fbw = {s: b.B4J002 * (fbw40[s] / fb40).reindex(b.index) for s in 'MF'}
    # Citizenship: rake 1940's FB-white sex × (naturalized, alien incl. first papers, not reported)
    # to the 1950 sex totals above and 1950's citizenship split of all FB 21+.
    cz = {(s, k): pd.Series(np.nan, b.index) for s in 'MF' for k in range(3)}
    for st in b.index:
        seed = np.array([[e.at[st, 'BWN001'], e.at[st, 'BWN002'] + e.at[st, 'BWN003'], e.at[st, 'BWN004']],
                         [e.at[st, 'BWN005'], e.at[st, 'BWN006'] + e.at[st, 'BWN007'], e.at[st, 'BWN008']]])
        r = np.array([fbw['M'][st], fbw['F'][st]])
        if np.isnan(seed).any() or np.isnan(r).any():
            continue
        k = b.loc[st, cols('B4K', 1, 3)].to_numpy(float)
        t = ipf(seed, r, k / k.sum() * r.sum())
        for i, s in enumerate('MF'):
            for j in range(3):
                cz[(s, j)][st] = t[i, j]
    ns = neg_share(1950)
    T6, T18, T48, T9 = 'NHGIS 1950_cAge NT6', 'NHGIS 1950_cAge NT18', 'NHGIS 1950_cPHA NT48', 'NHGIS 1950_cPHA NT9A/NT9B'
    fbnote = ('[I] 1950 foreign-born 21+ (NT9A, all races, both sexes) × 1940 state ratio of FB white by sex to all FB '
              '(1940_cPHAE NT12/NT10); citizenship raked (IPF) from 1940 FB-white sex × citizenship to 1950 NT9B '
              'all-FB citizenship split; 1950 "alien" includes first papers')
    c21, c18 = {}, {}
    for s in 'MF':
        nb = wh[s] - fbw[s]
        assert (nb.dropna() > 0).all(), '1950 native white < 0'
        wnote = ('[I] white 21+ = NT6 total 21+ − nonwhite 21+ (NT48); sex split by NT18 bands with 20–24 split '
                 'evenly by single year; minus estimated foreign-born white')
        c21[(s, 'native_white')] = (nb, tab('White: Native-born', f'{T6}; {T48}; {T18}; {T9}', wnote))
        for j, (g, lab) in enumerate((('foreign_white_naturalized', 'naturalized'), ('foreign_white_alien', 'alien'),
                                      ('foreign_white_unknown', 'citizenship not reported'))):
            c21[(s, g)] = (cz[(s, j)], tab(f'White: Foreign-born, {lab}', f'{T9}; NHGIS 1940_cPHAE NT10/NT12', fbnote))
        nnote = ('[I] nonwhite 21+ by sex from NT48 (Alaska: NT18 bands, 20–24 split evenly); Negro share of nonwhite '
                 'interpolated linearly 1940 (cAge NT7) → 1970 (Cnt1 NT19); Alaska 1970 share')
        c21[(s, 'negro')] = (nw[s] * ns[s].reindex(nw[s].index), tab('Negro: Negro (est. from nonwhite)', f'{T48}; {T18}', nnote))
        c21[(s, 'other_races')] = (nw[s] * (1 - ns[s].reindex(nw[s].index)),
                                   tab('Other: Other races (est. from nonwhite)', f'{T48}; {T18}', nnote))
        # 18–20 add-on
        w18, n18 = band[('W', s, 18)], band[('N', s, 18)]
        fsh = (fbw[s] / wh[s])
        c18[(s, 'native_white')] = w18 * (1 - fsh)
        for j, g in enumerate(('foreign_white_naturalized', 'foreign_white_alien', 'foreign_white_unknown')):
            c18[(s, g)] = w18 * fsh * (cz[(s, j)] / fbw[s])
        c18[(s, 'negro')] = n18 * ns[s].reindex(n18.index)
        c18[(s, 'other_races')] = n18 * (1 - ns[s].reindex(n18.index))
    note18 = ('; 18–20 [I]: NT18 bands, 2/5 of 15–19 + 1/5 of 20–24 (even single-year split), '
              'nativity/citizenship/Negro shares as 21+')
    return emit(1950, c21), add18(1950, c21, c18, note18)


def add18(year, c21, c18, note18):
    cells = {}
    for k, (s, m) in c21.items():
        n = m['note'] + note18 if m['note'].startswith('[I]') else '[I] 21+ ' + m['note'] + note18
        cells[k] = (s + c18[k].reindex(s.index), dict(m, note=n))
    return emit(year, cells)


# ---------------------------------------------------------------- 1950 shares carried to 1960, 1970
def fb_shares_1950():
    """FB white share of white 21+, and citizenship split of FB white, by state × sex from the 1950 build.
    Hawaii (no 1950 data): national 1950 shares."""
    d = y1950()[0]
    p = d.pivot_table(index=['state', 'sex'], columns='group', values='count', aggfunc='sum')
    fbg = ['foreign_white_naturalized', 'foreign_white_alien', 'foreign_white_unknown']
    p.loc[('HI', 'M'), :] = p.xs('M', level='sex').sum()
    p.loc[('HI', 'F'), :] = p.xs('F', level='sex').sum()
    fb = p[fbg].sum(axis=1)
    share = fb / (fb + p['native_white'])
    split = p[fbg].div(fb, axis=0)
    return share, split


def white_split(year, wh, w18, src, wnote, has18=True):
    share, split = fb_shares_1950()
    fbnote = (f'[I] white 21+ ({wnote}) × 1950 FB-white share of white 21+ and 1950 citizenship split, carried '
              f'forward by state × sex (Hawaii: national 1950 shares); 1950 "alien" includes first papers')
    c21, c18 = {}, {}
    for s in 'MF':
        sh = share.xs(s, level='sex').reindex(wh[s].index)
        sp = split.xs(s, level='sex').reindex(wh[s].index)
        c21[(s, 'native_white')] = (wh[s] * (1 - sh), tab('White: Native-born (est.)', src, fbnote))
        c18[(s, 'native_white')] = w18[s] * (1 - sh)
        for g, lab in (('foreign_white_naturalized', 'naturalized'), ('foreign_white_alien', 'alien'),
                       ('foreign_white_unknown', 'citizenship not reported')):
            c21[(s, g)] = (wh[s] * sh * sp[g], tab(f'White: Foreign-born, {lab} (est.)', src, fbnote))
            c18[(s, g)] = w18[s] * sh * sp[g]
    return c21, c18


# ---------------------------------------------------------------- 1960
@functools.lru_cache(None)
def y1960():
    a, b = read('ds89', True), read('ds91', True)
    band = {}
    for (race, s), o in ((('W', 'M'), 0), (('W', 'F'), 18), (('N', 'M'), 36), (('N', 'F'), 54)):
        x = a[cols('B49', 1 + o, 18 + o)].fillna(0).to_numpy()
        band[(race, s)] = x
    for s, o in (('M', 0), ('F', 18)):
        t = a[cols('B5F', 1 + o, 18 + o)].fillna(0).to_numpy()
        gap = np.abs(band[('W', s)] + band[('N', s)] - t).max()
        assert gap < 1, f'1960 {s}: NT11 white+nonwhite vs NT5 sex×age differ by {gap}'
    est = {k: pd.Series(x[:, 5:].sum(axis=1) + 0.8 * x[:, 4], a.index) for k, x in band.items()}
    e18 = {k: pd.Series(0.4 * x[:, 3] + 0.2 * x[:, 4], a.index) for k, x in band.items()}
    for s, col in (('M', 'B5T001'), ('F', 'B5T002')):
        r = est[('N', s)] / b[col] - 1
        print(f'1960 nonwhite 21+ {s}: NT14 {b[col].sum():,.0f} vs band-split {est[("N", s)].sum():,.0f} '
              f'(state rel. max {r.abs().max():.4f} {r.abs().idxmax()})')
    T11, T14 = 'NHGIS 1960_cAge1 NT11', 'NHGIS 1960_cPop NT14'
    wh = {s: est[('W', s)] for s in 'MF'}
    w18 = {s: e18[('W', s)] for s in 'MF'}
    c21, c18 = white_split(1960, wh, w18, f'{T11}; NHGIS 1950_cPHA NT9A/NT9B',
                           'NT11 bands, 25+ plus 4/5 of 20–24, even single-year split')
    ns = neg_share(1960)
    nnote = '[I] nonwhite 21+ by sex tabulated (NT14); Negro share interpolated linearly 1940 (cAge NT7) → 1970 (Cnt1 NT19); AK, HI 1970 share'
    for s, col in (('M', 'B5T001'), ('F', 'B5T002')):
        c21[(s, 'negro')] = (b[col] * ns[s], tab('Negro: Negro (est. from nonwhite)', T14, nnote))
        c21[(s, 'other_races')] = (b[col] * (1 - ns[s]), tab('Other: Other races (est. from nonwhite)', T14, nnote))
        c18[(s, 'negro')] = e18[('N', s)] * ns[s]
        c18[(s, 'other_races')] = e18[('N', s)] * (1 - ns[s])
    note18 = ('; 18–20 [I]: NT11 bands, 2/5 of 15–19 + 1/5 of 20–24 (even single-year split), '
              'nativity/citizenship/Negro shares as 21+')
    return emit(1960, c21), add18(1960, c21, c18, note18)


# ---------------------------------------------------------------- 1970
@functools.lru_cache(None)
def y1970():
    c = c1970()
    T18, T19 = 'NHGIS 1970_Cnt1 NT18', 'NHGIS 1970_Cnt1 NT19'
    wh = {s: c[(s, 'tot21')] - c[(s, 'negro21')] - c[(s, 'other_races21')] for s in 'MF'}
    w18 = {s: c[(s, 'tot18_20')] - c[(s, 'negro18_20')] - c[(s, 'other_races18_20')] for s in 'MF'}
    for s in 'MF':
        assert (wh[s] > 0).all() and (w18[s] > 0).all()
    c21, c18 = white_split(1970, wh, w18, f'{T18}; {T19}; NHGIS 1950_cPHA NT9A/NT9B',
                           'NT18 total 21+ minus NT19 Negro and other')
    rnote = ('[I] NT19 25+ tabulated; 21–24 = NT19 15–24 band × (NT18 total 21–24 / total 15–24), '
             'i.e. the band split by the total population\'s single-year shape')
    for s in 'MF':
        c21[(s, 'negro')] = (c[(s, 'negro21')], tab('Negro: Negro', T19 + '; ' + T18, rnote))
        c21[(s, 'other_races')] = (c[(s, 'other_races21')], tab('Other: Other races', T19 + '; ' + T18, rnote))
        c18[(s, 'negro')] = c[(s, 'negro18_20')]
        c18[(s, 'other_races')] = c[(s, 'other_races18_20')]
    note18 = ('; 18–20 [I]: total tabulated (NT18 single years), Negro/other = NT19 15–24 band × total 18–20 / 15–24, '
              'white nativity/citizenship shares as 21+')
    return emit(1970, c21), add18(1970, c21, c18, note18)


BUILDERS = {1940: lambda y: y1940(), 1950: lambda y: y1950()[0], 1960: lambda y: y1960()[0], 1970: lambda y: y1970()[0]}
BUILDERS18 = {1950: lambda y: y1950()[1], 1960: lambda y: y1960()[1], 1970: lambda y: y1970()[1]}


if __name__ == '__main__':
    years = [int(y) for y in sys.argv[1:]] or [1940, 1950, 1960, 1970]
    for y in years:
        for name, B in ((f'adults_{y}_by_state_nhgis.csv', BUILDERS), (f'adults18_{y}_by_state_nhgis.csv', BUILDERS18)):
            if y not in B:
                continue
            df = B[y](y)
            assert (df['count'] >= 0).all(), f'{name}: negative counts'
            df.to_csv(CACHE / 'population' / name, index=False)
            est = df[df.note.str.startswith('[I]')]['count'].sum()
            print(f'wrote {name}: {len(df)} rows, {df.state.nunique()} states, {df["count"].sum():,.0f} '
                  f'({df[df.sex == "F"]["count"].sum():,.0f} women; {est / df["count"].sum():.0%} of count in [I] rows)')
