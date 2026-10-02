"""1790–1860 censuses → population/adults_<year>_by_state_nhgis.csv (same long
format as build_population.py). Loaded by build_population.py through BUILDERS:

    python3 scripts/harness/build_population.py 1830

Source: NHGIS extract made by scripts/harness/nhgis_extract_republic.py (state tables;
see TABLES there). Groups: white, free_colored, enslaved (1790–1840);
native_white, foreign_white_unknown, free_colored, enslaved, other_races
(1850–1860; foreign-born citizenship is not tabulated, hence "_unknown").

None of these censuses tabulates age 21 exactly, so every adult count is an
[I] estimate from the age bands (note column says which). Band splits use a
stationary-growth age profile: each single-year cohort is W=0.97 the size of
the one a year younger (≈3% annual growth, early-republic rate), so the share
of a band [a, b] aged ≥21 is sum_{21..b} W^x / sum_{a..b} W^x.
"""
import sys
from pathlib import Path

import warnings as _w
import pandas as pd
_w.filterwarnings("ignore")

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
from simharness.config import CACHE  # noqa: E402
from simharness.geo import CODE_OF  # noqa: E402

COLS = ['year', 'state', 'sex', 'group', 'race_as_recorded', 'label_as_recorded', 'count', 'vintage_mode', 'note',
        'source_table', 'source_url', 'page']
NHGIS_URL = 'https://www.nhgis.org'
W = 0.97
# Territories / predecessor areas → the state they became (state code). Dakota is ambiguous → dropped.
AREA = {'southwest territory': 'TN', 'northwest territory': 'OH', 'orleans territory': 'LA',
        'louisiana territory': 'MO', 'district of columbia': 'DC'}
DS = {1790: 'ds1', 1800: 'ds2', 1810: 'ds3', 1820: 'ds4', 1830: 'ds5', 1840: 'ds7', 1850: 'ds10', 1860: 'ds14'}
FOREIGN_ADULT = {'M': 0.72, 'F': 0.70}  # [I] share of foreign-born whites aged 21+ (immigrants are adult-heavy)


def adult_share(a: int, b: int) -> float:
    """Share of the band [a, b] aged 21+, under the W age profile."""
    ages = range(a, b + 1)
    return sum(W ** x for x in ages if x >= 21) / sum(W ** x for x in ages)


def src_dir() -> Path:
    hits = sorted((CACHE / 'population/nhgis').glob('extract_*/nhgis*_csv/nhgis*_ds1_1790_state.csv'))
    if not hits:
        raise SystemExit('no 1790–1860 NHGIS extract: run scripts/harness/nhgis_extract_republic.py submit / wait N')
    return hits[-1].parent


def code_of(name: str):
    n = name.casefold().strip()
    if n in AREA:
        return AREA[n]
    n = n.replace(' territory', '')
    return {k.casefold(): v for k, v in CODE_OF.items()}.get(n)


def read(ds: str) -> pd.DataFrame:
    f = next(src_dir().glob(f'nhgis*_{ds}_*_state.csv'))
    d = pd.read_csv(f, encoding='latin-1', skiprows=[1])
    d['state'] = d.STATE.map(code_of)
    d = d[d.state.notna()]
    return d.set_index('state')


def table_of(year, ds_label):
    return f'NHGIS {year}_{ds_label}'


def out_rows(year, cells, table):
    """cells: {(state, sex, group): (count, note, label)}"""
    race = {'white': 'White', 'native_white': 'White', 'foreign_white_unknown': 'White', 'free_colored': 'Free colored',
            'enslaved': 'Slave', 'other_races': 'Other'}
    out = []
    for (st, sex, g), (c, note, label) in sorted(cells.items()):
        out.append({'year': year, 'state': st, 'sex': sex, 'group': g, 'race_as_recorded': race[g],
                    'label_as_recorded': label, 'count': round(float(c), 1), 'vintage_mode': 'truth', 'note': note,
                    'source_table': table, 'source_url': NHGIS_URL, 'page': ''})
    return pd.DataFrame(out, columns=COLS)


# ---------------------------------------------------------------- per-census adult counts
def white_1800_1820(year):
    """Free white males/females 16–25, 26–44, 45+ (1820 men also 16–18)."""
    d = read(DS[year])
    p = {1800: 'AAX', 1810: 'AA6', 1820: 'ABG'}[year]
    res = {}
    for st, r in d.iterrows():
        for sex, off in (('M', 0), ('F', 5)):
            b1625, b2644, b45 = (r[f'{p}{off + i:03d}'] for i in (3, 4, 5))
            if year == 1820 and sex == 'M':
                b1925 = b1625 - r['ABH001']
                n = adult_share(19, 25) * b1925 + b2644 + b45
                note = f'[I] 21+ = {adult_share(19, 25):.3f}×(16–25 less 16–18) + 26–44 + 45+'
            else:
                n = adult_share(16, 25) * b1625 + b2644 + b45
                note = f'[I] 21+ = {adult_share(16, 25):.3f}×(16–25) + 26–44 + 45+'
            res[(st, sex, 'white')] = (n, note, f'Free white {"males" if sex == "M" else "females"} 16–25/26–44/45+')
    return d, res


def colored_1820():
    """Slave / free colored by sex: <14, 14–25, 26–44, 45+ (ABK001–016)."""
    d = read('ds4')
    res = {}
    f = adult_share(14, 25)
    for st, r in d.iterrows():
        for g, base in (('enslaved', 0), ('free_colored', 8)):
            for sex, off in (('M', 0), ('F', 4)):
                c = lambda i: r[f'ABK{base + off + i:03d}']  # noqa: E731
                res[(st, sex, g)] = (f * c(2) + c(3) + c(4), f'[I] 21+ = {f:.3f}×(14–25) + 26–44 + 45+',
                                     f'{"Slave" if g == "enslaved" else "Free colored"} {sex} 14–25/26–44/45+')
    return d, res


def colored_ratios():
    """Per state: adults-by-sex / group total in 1820, the template for 1790–1810."""
    d, res = colored_1820()
    tot = {'enslaved': d[[f'ABK{i:03d}' for i in range(1, 9)]].sum(axis=1),
           'free_colored': d[[f'ABK{i:03d}' for i in range(9, 17)]].sum(axis=1)}
    nat = {(sex, g): sum(res[(s, sex, g)][0] for s in d.index) / tot[g].sum() for sex in 'MF' for g in tot}
    rat = {}
    for st in d.index:
        for g in tot:
            for sex in 'MF':
                rat[(st, sex, g)] = res[(st, sex, g)][0] / tot[g][st] if tot[g][st] > 200 else nat[(sex, g)]
    return rat, nat


def colored_from_totals(year, d, free_col, slave_col, rat, nat):
    res = {}
    for st, r in d.iterrows():
        for g, col in (('free_colored', free_col), ('enslaved', slave_col)):
            for sex in 'MF':
                k = rat.get((st, sex, g))
                src = '1820 same-state' if k is not None else '1820 national'
                k = k if k is not None else nat[(sex, g)]
                res[(st, sex, g)] = (r[col] * k, f'[I] {g} total ({col}) × {src} share {sex} 21+ ({k:.3f}); no sex/age in {year}',
                                     f'{"Free nonwhite" if g == "free_colored" else "Slave"} (total, sex/age not tabulated)')
    return res


def y1790(year=1790):
    d = read('ds1')
    d00, w00 = white_1800_1820(1800)
    rat, nat = colored_ratios()
    res = {}
    for st, r in d.iterrows():
        for sex, col in (('M', 'AAO002'), ('F', 'AAO004')):
            off = 0 if sex == 'M' else 5
            if st in d00.index:
                b = d00.loc[st]
                k = w00[(st, sex, 'white')][0] / sum(b[f'AAX{off + i:03d}'] for i in (3, 4, 5))
                src = '1800 same-state'
            else:
                k = adult_share(16, 25) * 0.30 + 0.70
                src = 'default'
            res[(st, sex, 'white')] = (r[col] * k, f'[I] white {sex} 16+ ({col}{", NHGIS-estimated" if sex == "F" else ""}) × {src} 21+/16+ ratio ({k:.3f})',
                                       f'White {"males" if sex == "M" else "females (estimated)"} 16 and over')
    res.update(colored_from_totals(1790, d, 'AAQ001', 'AAQ002', rat, nat))
    return out_rows(1790, res, 'NHGIS 1790_cPop NT4, NT6')


def y1800_1810(year):
    d, res = white_1800_1820(year)
    rat, nat = colored_ratios()
    free_col, slave_col = {1800: ('AAY001', 'AAY002'), 1810: ('AA7001', 'AA7002')}[year]
    res.update(colored_from_totals(year, d, free_col, slave_col, rat, nat))
    return out_rows(year, res, f'NHGIS {year}_cPop NT5, NT6')


def y1820(year=1820):
    _, res = white_1800_1820(1820)
    _, col = colored_1820()
    res.update(col)
    return out_rows(1820, res, 'NHGIS 1820_cPop NT4A, NT4B, NT7')


def y1830_1840(year):
    d = read(DS[year])
    wp, cp = {1830: ('ABW', 'ABX'), 1840: ('ACY', 'ACZ')}[year]
    fw, fc = adult_share(20, 29), adult_share(10, 23)
    # colored block order: 1830 slave then free; 1840 free then slave
    blocks = {1830: (('enslaved', 0), ('free_colored', 12)), 1840: (('free_colored', 0), ('enslaved', 12))}[year]
    res = {}
    for st, r in d.iterrows():
        for sex, off in (('M', 0), ('F', 13)):
            w = lambda i: r[f'{wp}{off + i:03d}']  # noqa: E731
            res[(st, sex, 'white')] = (fw * w(5) + sum(w(i) for i in range(6, 14)),
                                       f'[I] 21+ = {fw:.3f}×(20–29) + 30+', f'Free white {sex} 20–29 and 30+ bands')
        for g, base in blocks:
            for sex, off in (('M', 0), ('F', 6)):
                c = lambda i: r[f'{cp}{base + off + i:03d}']  # noqa: E731
                res[(st, sex, g)] = (fc * c(2) + sum(c(i) for i in range(3, 7)),
                                     f'[I] 21+ = {fc:.3f}×(10–23) + 24+', f'{g} {sex} 10–23 and 24+ bands')
    t = {1830: 'NHGIS 1830_cPop NT4, NT5', 1840: 'NHGIS 1840_cPopX NT4, NT5'}[year]
    return out_rows(year, res, t)


def adults_1850_1860(year):
    """→ {(st, sex, group): (count, note, label)} for white / free_colored / enslaved / other_races."""
    d = read(DS[year])
    f = adult_share(20, 29)
    res = {}
    if year == 1850:
        # AEL: 3 race blocks × 2 sexes × 15 cells (<1,1–4,5–9,10–14,15–19,20–29,…,100+,unknown)
        layout = [('white', 0), ('free_colored', 30), ('enslaved', 60)]
        for st, r in d.iterrows():
            for g, base in layout:
                for sex, off in (('M', 0), ('F', 15)):
                    c = [r[f'AEL{base + off + i:03d}'] for i in range(1, 16)]
                    known = sum(c[:14])
                    ad = f * c[5] + sum(c[6:14])
                    ad += c[14] * (ad / known if known else 0)
                    res[(st, sex, g)] = (ad, f'[I] 21+ = {f:.3f}×(20–29) + 30+, age-unknown allocated pro rata',
                                         f'{g} {sex} by age (NT4)')
    else:
        # AH0: 6 races × 15 age cells × 2 sexes, sex innermost
        races = [('white', 0), ('free_colored', 30), ('enslaved', 60), ('other_races', 90), ('other_races', 120), ('other_races', 150)]
        for st, r in d.iterrows():
            for g, base in races:
                for sex, s in (('M', 1), ('F', 2)):
                    c = [r[f'AH0{base + 2 * i + s:03d}'] for i in range(15)]
                    known = sum(c[:14])
                    ad = f * c[5] + sum(c[6:14])
                    ad += c[14] * (ad / known if known else 0)
                    k = (st, sex, g)
                    prev = res.get(k, (0, '', ''))[0]
                    res[k] = (prev + ad, f'[I] 21+ = {f:.3f}×(20–29) + 30+, age-unknown allocated pro rata'
                              + ('; Indian + half breed + Asiatic' if g == 'other_races' else ''), f'{g} {sex} by age (NT4)')
    return res


def y1850_1860(year):
    res = adults_1850_1860(year)
    if year == 1850:
        n = read('ds12')
        fb = {'M': n['AGF001'], 'F': n['AGF002']}
        t = 'NHGIS 1850_cPAX NT4; 1850_sPAX NT1, NT5, NT7'
    else:
        n = read('ds14')
        fb = {'M': n['AH4007'], 'F': n['AH4008']}
        t = 'NHGIS 1860_cPAX NT4, NT7'
    out = {}
    for (st, sex, g), v in res.items():
        if g != 'white':
            out[(st, sex, g)] = v
            continue
        wa = v[0]
        fa = min(fb[sex].get(st, 0) * FOREIGN_ADULT[sex], 0.95 * wa)
        out[(st, sex, 'foreign_white_unknown')] = (fa, f'[I] foreign-born white {sex} (all ages) × {FOREIGN_ADULT[sex]} adult share; '
                                                   'citizenship not tabulated', f'Foreign-born white {sex}')
        out[(st, sex, 'native_white')] = (wa - fa, f'[I] white 21+ ({v[1][4:]}) less foreign-born adults; birthplace-unknown counted native',
                                          f'Native white {sex} (residual)')
    return out_rows(year, out, t)


def build(year: int) -> pd.DataFrame:
    if year == 1790:
        return y1790()
    if year in (1800, 1810):
        return y1800_1810(year)
    if year == 1820:
        return y1820()
    if year in (1830, 1840):
        return y1830_1840(year)
    return y1850_1860(year)


BUILDERS = {y: build for y in range(1790, 1861, 10)}


def free_share(year: int) -> dict:
    """Per state: free colored / (free colored + enslaved) among adult men, from the nearest census at or before `year`."""
    c = max(y for y in BUILDERS if y <= max(year, 1790))
    f = CACHE / f'population/adults_{c}_by_state_nhgis.csv'
    df = pd.read_csv(f) if f.exists() else build(c)
    m = df[(df.sex == 'M') & df.group.isin(['free_colored', 'enslaved'])].pivot_table(index='state', columns='group', values='count', aggfunc='sum')
    return (m.free_colored / (m.free_colored + m.enslaved)).fillna(1.0).to_dict()


if __name__ == '__main__':
    for y in (map(int, sys.argv[1:]) if len(sys.argv) > 1 else BUILDERS):
        df = build(y)
        out = CACHE / f'population/adults_{y}_by_state_nhgis.csv'
        df.to_csv(out, index=False)
        print(f'wrote {out.name}: {len(df)} rows, {df.state.nunique()} states, {df["count"].sum():,.0f} adults '
              f'({df[df.sex == "F"]["count"].sum():,.0f} women)')
