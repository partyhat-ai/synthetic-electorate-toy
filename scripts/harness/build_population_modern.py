"""NHGIS extract (nhgis_extract_modern.py) -> population/adults18_<year>_by_state_nhgis.csv
for 1980-2024: adults 18+ by state x sex x {white_nh_native, black_nh_native,
other_native, naturalized, noncitizen}, in the long format of build_population.

    python3 scripts/harness/build_population_modern.py 2000 [--extract N]   # one year
    python3 scripts/harness/build_population_modern.py all                  # every year in BUILDERS

(build_population.py imports BUILDERS from here too, but it writes adults_<year>_...;
this module's own CLI writes the adults18_ files.)

Sources by year (all NHGIS, state level):
  1980  STF2b NTB8B sex x age, iterated all / white not Spanish / Black not Spanish (100%);
        STF4Pb NTPB9 nativity x citizenship iterated all / white / Black / Spanish (sample,
        all ages); STF2a NTA13 Spanish origin by race. Not crossed with age: foreign-born
        adults = FB all ages x 1990 state adult share by citizenship [I]; race FB net of
        Spanish FB by the state's Spanish race mix [I]; FB sex split from 2000 [I].
  1990  MARS NP1 age x Hispanic x sex x race (white/Black NH 18+ by sex); STF3 NP37
        age x citizenship (sample); STF4b NPB20 nativity iterated by WNH/BNH (all ages,
        adult share [I]); FB sex split from 2000 [I].
  2000  SF4 PCT044B/C sex x 18+ x nativity / citizenship iterated all / WNH / BNH (sample),
        raked to SF1 P5 (NP005A) 18+ totals.
  2008  ACS 2006-2010 5-year; 2010, 2012, 2016, 2024 ACS 1-year; 2020 ACS 2016-2020
        5-year: B05003 (+H white alone NH, +B Black alone). Black NH native = Black alone
        native x NH share of Black alone in B03002 (all ages) [I]. 2010 and 2020 raked to
        PL 94-171 18+ state totals.
Every row's `note` says "tabulated" or what was [I]-estimated.
"""
import argparse
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from simharness.config import CACHE  # noqa: E402
from simharness.geo import CODE_OF  # noqa: E402
from build_population import COLS, NHGIS_URL  # noqa: E402

NHGIS = CACHE / 'population/nhgis'
EXTRACT = None  # set by CLI or found automatically


def src() -> Path:
    global EXTRACT
    if EXTRACT is None:
        reqs = sorted(NHGIS.glob('extract_request_*_modern.json'), key=lambda p: int(p.name.split('_')[2]))
        EXTRACT = int(reqs[-1].name.split('_')[2])
    d = NHGIS / f'extract_{EXTRACT}'
    return next(p for p in d.iterdir() if p.is_dir() and p.name.endswith('_csv'))


_CACHE = {}
FILE_OF = {}       # dataset name -> csv path
TABLE_PREFIX = {}  # (dataset, source table code) -> NHGIS column prefix


def load_prefixes():
    """Every codebook names its dataset ('Dataset: ... NHGIS code: 2024_ACS1') and, per table,
    'Source code: B05003 / NHGIS code: ATMV' (the column prefix)."""
    if FILE_OF:
        return
    for cb in src().glob('*_codebook.txt'):
        t = cb.read_text(encoding='latin-1')
        ds = re.search(r'Dataset:.*\n\s*NHGIS code:\s*(\S+)', t).group(1)
        FILE_OF[ds] = cb.with_name(cb.name.replace('_codebook.txt', '.csv'))
        for m in re.finditer(r'Source code:\s*(\S+)\s*\n\s*NHGIS code:\s*(\S+)', t):
            TABLE_PREFIX[(ds, m.group(1))] = m.group(2)


def read(ds: str) -> tuple:
    """Return (df indexed by state with code columns, {code: description})."""
    if ds in _CACHE:
        return _CACHE[ds]
    load_prefixes()
    raw = pd.read_csv(FILE_OF[ds], encoding='latin-1', header=None, low_memory=False, dtype=str)
    codes, descs = list(raw.iloc[0]), list(raw.iloc[1])
    d = raw.iloc[2:].copy()
    d.columns = codes
    code = {k.casefold(): v for k, v in CODE_OF.items()}
    d = d[d.STATE.str.casefold().isin(code)].copy()
    d['state'] = d.STATE.str.casefold().map(code)
    d = d.set_index('state')
    desc = {c: str(x) for c, x in zip(codes, descs)}
    ctx = {'GISJOIN', 'YEAR', 'STATE', 'STATEA', 'AREANAME', 'NAME_E', 'NAME_M', 'GEOID', 'STUSAB', 'REGIONA', 'DIVISIONA',
           'state'}
    for c in codes:
        if c not in ctx:
            d[c] = pd.to_numeric(d[c], errors='coerce')
    _CACHE[ds] = (d, desc)
    return _CACHE[ds]


def cols(desc: dict, *pats, table=None) -> list:
    """Codes whose description matches every regex in pats (and the table code prefix if given)."""
    out = []
    for c, s in desc.items():
        if table and not str(c).startswith(table):
            continue
        if all(re.search(p, s) for p in pats):
            out.append(c)
    return out


def is_adult(label: str) -> bool:
    for part in re.split(r'>>|:', label):
        p = part.strip()
        if p.startswith('Under'):
            return False
        m = re.match(r'(\d+)', p)
        if m and ('year' in p or re.fullmatch(r'\d+( to \d+| and \d+)?( years)?( and over)?', p)):
            return int(m.group(1)) >= 18
    raise ValueError(f'no age in {label!r}')


def adults(d, desc, table, *pats):
    cs = [c for c in cols(desc, *pats, table=table) if is_adult(desc[c])]
    assert cs, (table, pats)
    return d[cs].sum(axis=1)


def emit(year, parts: dict, tables: dict, notes: dict):
    """parts: {(sex, group): Series by state}"""
    labels = {'white_nh_native': 'White alone/White, not Hispanic, native-born',
              'black_nh_native': 'Black alone/Black, not Hispanic, native-born',
              'other_native': 'Native-born, all other (Hispanic any race, Asian, AIAN, other, multiracial)',
              'naturalized': 'Foreign-born, naturalized citizen', 'noncitizen': 'Foreign-born, not a citizen'}
    out = []
    for (sex, g), s in parts.items():
        for st, v in s.items():
            out.append({'year': year, 'state': st, 'sex': sex, 'group': g, 'race_as_recorded': labels[g].split(',')[0],
                        'label_as_recorded': labels[g], 'count': round(float(v), 1), 'vintage_mode': 'truth',
                        'note': notes.get(g, 'tabulated'), 'source_table': tables[g], 'source_url': NHGIS_URL, 'page': ''})
    df = pd.DataFrame(out, columns=COLS)
    assert df.state.nunique() == 51, df.state.nunique()
    assert (df['count'] >= 0).all(), df[df['count'] < 0]
    return df.sort_values(['state', 'sex', 'group']).reset_index(drop=True)


def check(year, df, indep: pd.Series, what: str):
    tot = df.groupby('state')['count'].sum()
    gap = (tot - indep.reindex(tot.index)) / indep.reindex(tot.index)
    print(f'{year}: groups {tot.sum():,.0f} vs {what} {indep.sum():,.0f} (national {100 * (tot.sum() / indep.sum() - 1):+.2f}%; '
          f'worst state {gap.abs().idxmax()} {100 * gap.abs().max():.2f}%)')


def split_native(native, wnn, bnn):
    """other_native = remainder; if WNH+BNH native exceed the sample-based native total, shrink them."""
    over = (wnn + bnn) / native
    k = over.clip(lower=1.0)
    return wnn / k, bnn / k, native - (wnn + bnn) / k


# ------------------------------------------------------------------- helpers per table
def pick(d, desc, prefix, *pats):
    """Sum of the columns of one table whose description matches every regex."""
    cs = cols(desc, *pats, table=prefix)
    assert cs, (prefix, pats)
    return d[cs].sum(axis=1)


def adult_sum(d, desc, prefix, *pats):
    cs = [c for c in cols(desc, *pats, table=prefix) if is_adult(desc[c])]
    assert cs, (prefix, pats)
    return d[cs].sum(axis=1)


def fb_sex_shares_2000():
    """Male share of foreign-born adults by citizenship, by state (SF4 PCT044C, all races)."""
    d, desc = read('2000_SF4')
    p = TABLE_PREFIX[('2000_SF4', 'NPCT044C')]
    out = {}
    for k, pat in (('nat', r'Naturalized citizen$'), ('nc', r'Not a citizen$')):
        m = pick(d, desc, p, r'^Total area: All races: Male >> 18 years and over', pat)
        f = pick(d, desc, p, r'^Total area: All races: Female >> 18 years and over', pat)
        out[k] = m / (m + f)
    return out


def adult_share_1990():
    """Share of the foreign born who are 18+, by citizenship (1990 STF3 NP37)."""
    d, desc = read('1990_STF3')
    p = TABLE_PREFIX[('1990_STF3', 'NP37')]
    g = lambda *pats: pick(d, desc, p, *pats)  # noqa: E731
    nat18, nc18 = g(r'^18 years and over', 'Naturalized'), g(r'^18 years and over', 'Not a citizen')
    nat, nc = nat18 + g(r'^Under 18', 'Naturalized'), nc18 + g(r'^Under 18', 'Not a citizen')
    return nat18 / nat, nc18 / nc, nat18, nc18, g(r'^18 years and over', r'Native$')


LABEL = {'white_nh_native': 'White alone/White, not Hispanic, native-born',
         'black_nh_native': 'Black alone/Black, not Hispanic, native-born',
         'other_native': 'Native-born, all other (Hispanic any race, Asian, AIAN, other, multiracial)',
         'naturalized': 'Foreign-born, naturalized citizen', 'noncitizen': 'Foreign-born, not a citizen'}


def assemble(year, by_sex, tables, notes):
    parts = {}
    for sex, (nat18, nz, nc, wnn, bnn) in by_sex.items():
        wnn, bnn, onn = split_native(nat18, wnn.clip(lower=0), bnn.clip(lower=0))
        parts.update({(sex, 'white_nh_native'): wnn, (sex, 'black_nh_native'): bnn, (sex, 'other_native'): onn,
                      (sex, 'naturalized'): nz, (sex, 'noncitizen'): nc})
    return emit(year, parts, tables, notes)


def rake(df, tot, what):
    cur = df.groupby('state')['count'].sum()
    k = tot.reindex(cur.index) / cur
    print(f'  rake to {what}: state factors {k.min():.4f}-{k.max():.4f}')
    df = df.copy()
    df['count'] = (df['count'] * df.state.map(k)).round(1)
    df['note'] = df['note'] + df.state.map(lambda s: f'; raked x{k[s]:.4f} to {what}')
    return df


# ------------------------------------------------------------------- ACS years
ACS = {2008: ('2006_2010_ACS5b', '2006_2010_ACS5a', 'ACS 2006-2010 5-year'),
       2010: ('2010_ACS1', '2010_ACS1', 'ACS 2010 1-year'),
       2012: ('2012_ACS1', '2012_ACS1', 'ACS 2012 1-year'),
       2016: ('2016_ACS1', '2016_ACS1', 'ACS 2016 1-year'),
       2020: ('2016_2020_ACS5b', '2016_2020_ACS5a', 'ACS 2016-2020 5-year'),
       2024: ('2024_ACS1', '2024_ACS1', 'ACS 2024 1-year')}


def black_ratio_2020(word):
    """2016-2020 ACS5: Black NH native 18+ of one sex / Black NH all ages, by state."""
    d, desc = read('2016_2020_ACS5b')
    da, desca = read('2016_2020_ACS5a')
    p3 = TABLE_PREFIX[('2016_2020_ACS5a', 'B03002')]
    bnh = pick(da, desca, p3, r'^Estimates: Not Hispanic or Latino: Black or African American alone$')
    bh = pick(da, desca, p3, r'^Estimates: Hispanic or Latino: Black or African American alone$')
    nat = pick(d, desc, TABLE_PREFIX[('2016_2020_ACS5b', 'B05003B')], rf'^Estimates: {word}: 18 years and over: Native$')
    return nat * bnh / (bnh + bh) / bnh


def year_acs(year):
    dsb, dsa, label = ACS[year]
    d, desc = read(dsb)
    da, desca = read(dsa)
    P = lambda ds, t: TABLE_PREFIX[(ds, t)]  # noqa: E731
    p3 = P(dsa, 'B03002')
    bnh = pick(da, desca, p3, r'^Estimates: Not Hispanic or Latino: Black or African American alone$')
    bh = pick(da, desca, p3, r'^Estimates: Hispanic or Latino: Black or African American alone$')
    r_bnh = bnh / (bnh + bh)
    # 1-year B05003B is suppressed in a few small-Black-population states (MT, WY, ...): there,
    # Black NH native 18+ = this year's Black NH (all ages, B03002) x the 2016-2020 5-year ratio [I]
    pb = P(dsb, 'B05003B')
    supp = d[[c for c in desc if str(c).startswith(pb + 'E')]].isna().any(axis=1)
    supp = list(supp[supp].index)
    by_sex = {}
    for sex, word in (('M', 'Male'), ('F', 'Female')):
        g = lambda t, pat: pick(d, desc, P(dsb, t), rf'^Estimates: {word}: 18 years and over: {pat}')  # noqa: E731
        bnn = g('B05003B', r'Native$') * r_bnh
        if supp:
            bnn[supp] = (bnh * black_ratio_2020(word))[supp]
        by_sex[sex] = (g('B05003', r'Native$'), g('B05003', r'Foreign.born: Naturalized'), g('B05003', r'Foreign.born: Not a U\.S\. citizen'),
                       g('B05003H', r'Native$'), bnn)
    b01 = adult_sum(da, desca, P(dsa, 'B01001'), r'^Estimates: (Male|Female): ')
    tables = {'white_nh_native': f'NHGIS {dsb} B05003H', 'black_nh_native': f'NHGIS {dsb} B05003B x {dsa} B03002',
              'other_native': f'NHGIS {dsb} B05003 - B05003H - B05003B', 'naturalized': f'NHGIS {dsb} B05003',
              'noncitizen': f'NHGIS {dsb} B05003'}
    notes = {'black_nh_native': f'[I] Black alone native 18+ x NH share of Black alone (B03002, all ages); {label}',
             'other_native': f'remainder: B05003 native 18+ minus white NH and Black NH native; {label}',
             'white_nh_native': f'tabulated; {label}', 'naturalized': f'tabulated; {label}', 'noncitizen': f'tabulated; {label}'}
    df = assemble(year, by_sex, tables, notes)
    m = df.state.isin(supp) & (df.group == 'black_nh_native')
    df.loc[m, 'note'] = f'[I] B05003B suppressed: Black NH all ages (B03002) x 2016-2020 ACS5 ratio of Black NH native 18+ to Black NH; {label}'
    check(year, df, b01, f'{dsa} B01001 18+')
    if year in (2010, 2020):
        ds = f'{year}_PL94171'
        dp, descp = read(ds)
        tot = pick(dp, descp, TABLE_PREFIX[(ds, 'P3' if year == 2020 else 'NP003')], r'^Total$')
        check(year, df, tot, 'PL 94-171 18+ (before rake)')
        df = rake(df, tot, f'PL 94-171 {year} 18+ state total')
    return df


# ------------------------------------------------------------------- 2000
def year_2000(year=2000):
    d, desc = read('2000_SF4')
    pn, pc = TABLE_PREFIX[('2000_SF4', 'NPCT044B')], TABLE_PREFIX[('2000_SF4', 'NPCT044C')]
    it = {'all': 'All races', 'w': 'White alone, not Hispanic or Latino', 'b': 'Black or African American alone, not Hispanic or Latino'}
    by_sex = {}
    for sex, word in (('M', 'Male'), ('F', 'Female')):
        g = lambda p, i, pat: pick(d, desc, p, rf'^Total area: {re.escape(it[i])}: {word} >> 18 years and over >> {pat}$')  # noqa: E731
        by_sex[sex] = (g(pn, 'all', 'Native'), g(pc, 'all', 'Naturalized citizen'), g(pc, 'all', 'Not a citizen'),
                       g(pn, 'w', 'Native'), g(pn, 'b', 'Native'))
    tables = {'white_nh_native': 'NHGIS 2000_SF4 PCT44B (White alone, not Hispanic)',
              'black_nh_native': 'NHGIS 2000_SF4 PCT44B (Black alone, not Hispanic)',
              'other_native': 'NHGIS 2000_SF4 PCT44B (all - WNH - BNH)', 'naturalized': 'NHGIS 2000_SF4 PCT44C',
              'noncitizen': 'NHGIS 2000_SF4 PCT44C'}
    notes = {'other_native': 'remainder: native 18+ minus white NH and Black NH native (SF4 sample)'}
    df = assemble(2000, by_sex, tables, {g: notes.get(g, 'tabulated (SF4 sample)') for g in LABEL})
    ds, dsc = read('2000_SF1a')
    tot = pick(ds, dsc, TABLE_PREFIX[('2000_SF1a', 'NP005A')], r'^Total$')
    check(2000, df, tot, 'SF1 P5 18+ (before rake)')
    return rake(df, tot, 'SF1 P5 2000 18+ state total (100% count)')


# ------------------------------------------------------------------- 1990
def year_1990(year=1990):
    r_nat, r_nc, nat18, nc18, nat_s = adult_share_1990()
    fb_a = (nat18 + nc18) / (nat18 / r_nat + nc18 / r_nc)
    msh = fb_sex_shares_2000()
    dm, descm = read('1990_MARS')
    pm = TABLE_PREFIX[('1990_MARS', 'NP1')]
    d4, desc4 = read('1990_STF4b')
    p4 = TABLE_PREFIX[('1990_STF4b', 'NPB20')]
    fb = lambda it: pick(d4, desc4, p4, rf'^Total area: {re.escape(it)}: Foreign born')  # noqa: E731
    fbw, fbb = fb('White, not of Hispanic origin') * fb_a, fb('Black, not of Hispanic origin') * fb_a
    # 1990 STF1 NP13 is Hispanic-only; the 100%-based 18+ by sex comes from MARS (all races, both origins)
    tot100 = {s: adult_sum(dm, descm, pm, rf'>> {w} >>') for s, w in (('M', 'Male'), ('F', 'Female'))}
    sample = nat_s + nat18 + nc18
    k = (tot100['M'] + tot100['F']) / sample  # sample -> 100% count
    by_sex = {}
    for sex, word in (('M', 'Male'), ('F', 'Female')):
        ms = (lambda x: x) if sex == 'M' else (lambda x: 1 - x)
        nz, nc = nat18 * k * ms(msh['nat']), nc18 * k * ms(msh['nc'])
        fbsh = (nz + nc) / (nat18 * k + nc18 * k)
        wnh = adult_sum(dm, descm, pm, rf'>> Not Hispanic >> {word} >> White$')
        bnh = adult_sum(dm, descm, pm, rf'>> Not Hispanic >> {word} >> Black$')
        by_sex[sex] = (tot100[sex] - nz - nc, nz, nc, wnh - fbw * k * fbsh, bnh - fbb * k * fbsh)
    tables = {'white_nh_native': 'NHGIS 1990_MARS NP1 - 1990_STF4b NPB20 (White, not Hispanic) FB',
              'black_nh_native': 'NHGIS 1990_MARS NP1 - 1990_STF4b NPB20 (Black, not Hispanic) FB',
              'other_native': 'NHGIS 1990_MARS NP1 18+ - FB - WNH - BNH native', 'naturalized': 'NHGIS 1990_STF3 NP37',
              'noncitizen': 'NHGIS 1990_STF3 NP37'}
    notes = {'white_nh_native': '[I] MARS white NH 18+ minus WNH foreign born (all ages x FB adult share, NP37) x FB sex share (2000)',
             'black_nh_native': '[I] MARS Black NH 18+ minus BNH foreign born (all ages x FB adult share, NP37) x FB sex share (2000)',
             'other_native': '[I] remainder of 100%-based 18+ (MARS NP1)',
             'naturalized': '[I] STF3 NP37 18+ (sample, scaled to 100% count); sex split from 2000 SF4 PCT44C',
             'noncitizen': '[I] STF3 NP37 18+ (sample, scaled to 100% count); sex split from 2000 SF4 PCT44C'}
    df = assemble(1990, by_sex, tables, notes)
    check(1990, df, sample, 'STF3 NP37 18+ (sample, independent)')
    print(f'  national 18+ {df["count"].sum():,.0f} vs published 1990 census 18+ 185,105,441 '
          f'({100 * (df["count"].sum() / 185105441 - 1):+.3f}%)')
    return df


# ------------------------------------------------------------------- 1980
def year_1980(year=1980):
    r_nat, r_nc, *_ = adult_share_1990()
    msh = fb_sex_shares_2000()
    d2, desc2 = read('1980_STF2b')
    p2 = TABLE_PREFIX[('1980_STF2b', 'NTB8B')]
    d4, desc4 = read('1980_STF4Pb')
    p4 = TABLE_PREFIX[('1980_STF4Pb', 'NTPB9')]
    da, desca = read('1980_STF2a')
    pa = TABLE_PREFIX[('1980_STF2a', 'NTA13')]
    d1, desc1 = read('1980_STF1')
    p1 = TABLE_PREFIX[('1980_STF1', 'NT10B')]
    g4 = lambda it, pat: pick(d4, desc4, p4, rf'^Total area: {re.escape(it)}: {pat}')  # noqa: E731
    nat_all, nc_all = g4('All races', 'Foreign born: Naturalized'), g4('All races', 'Foreign born: Not a citizen')
    sample_all = nat_all + nc_all + g4('All races', 'Native')
    nat18, nc18 = nat_all * r_nat, nc_all * r_nc
    fb_a = (nat18 + nc18) / (nat_all + nc_all)
    sp_fb = g4('Spanish origin subtotal (subtotal of summaries 20-23)', 'Foreign born')
    sp = da[[c for c in desca if str(c).startswith(pa) and desca[c].startswith('Spanish origin')]].sum(axis=1)
    sp_w = pick(da, desca, pa, r'^Spanish origin >> White$') / sp
    sp_b = pick(da, desca, pa, r'^Spanish origin >> Black$') / sp
    fbw = (g4('White', 'Foreign born') - sp_fb * sp_w).clip(lower=0) * fb_a
    fbb = (g4('Black', 'Foreign born') - sp_fb * sp_b).clip(lower=0) * fb_a
    it = lambda s: re.escape(s)  # noqa: E731
    by_sex, tot100 = {}, {}
    for sex, word in (('M', 'Male'), ('F', 'Female')):
        a = lambda iname: adult_sum(d2, desc2, p2, rf'^Total area: {it(iname)}: {word} >>')  # noqa: E731
        tot100[sex] = a('All races')
        ms = (lambda x: x) if sex == 'M' else (lambda x: 1 - x)
        # the sample nativity table is all ages; scale its FB counts to the 100% count
        k = d2[cols(desc2, r'^Total area: All races: ', table=p2)].sum(axis=1) / sample_all
        nz, nc = nat18 * k * ms(msh['nat']), nc18 * k * ms(msh['nc'])
        fbsh = (nz + nc) / ((nat18 + nc18) * k)
        wnh = a('White not of Spanish origin (on STF4B; not available for MCD\'s or CCD\'s under 2500')
        bnh = a('Black not of Spanish origin (on STF4B; not available for MCD\'s or CCD\'s under 2500')
        by_sex[sex] = (tot100[sex] - nz - nc, nz, nc, wnh - fbw * k * fbsh, bnh - fbb * k * fbsh)
    tables = {'white_nh_native': 'NHGIS 1980_STF2b NTB8B (White not of Spanish origin) - 1980_STF4Pb NTPB9 FB',
              'black_nh_native': 'NHGIS 1980_STF2b NTB8B (Black not of Spanish origin) - 1980_STF4Pb NTPB9 FB',
              'other_native': 'NHGIS 1980_STF2b NTB8B - FB - WNH - BNH native', 'naturalized': 'NHGIS 1980_STF4Pb NTPB9',
              'noncitizen': 'NHGIS 1980_STF4Pb NTPB9'}
    fbnote = 'FB all ages (STF4Pb, net of Spanish-origin FB by the state Spanish race mix, STF2a NTA13) x FB adult share (1990 NP37) x FB sex share (2000)'
    notes = {'white_nh_native': f'[I] 100% white not Spanish 18+ minus {fbnote}',
             'black_nh_native': f'[I] 100% Black not Spanish 18+ minus {fbnote}',
             'other_native': '[I] remainder of 100%-count 18+ (STF2b NTB8B)',
             'naturalized': '[I] STF4Pb all-ages naturalized x 1990 adult share (NP37), scaled to 100% count; sex split from 2000',
             'noncitizen': '[I] STF4Pb all-ages noncitizens x 1990 adult share (NP37), scaled to 100% count; sex split from 2000'}
    df = assemble(1980, by_sex, tables, notes)
    indep = adult_sum(d1, desc1, p1, r'^(Male|Female) >>')
    check(1980, df, indep, 'STF1 NT10B 18+ (100%)')
    return df


BUILDERS = {y: year_acs for y in ACS}
BUILDERS.update({1980: year_1980, 1990: year_1990, 2000: year_2000})

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('year')
    ap.add_argument('--extract', type=int)
    a = ap.parse_args()
    if a.extract:
        EXTRACT = a.extract
    years = sorted(BUILDERS) if a.year == 'all' else [int(a.year)]
    for y in years:
        df = BUILDERS[y](y)
        out = CACHE / f'population/adults18_{y}_by_state_nhgis.csv'
        df.to_csv(out, index=False)
        g = df.groupby('group')['count'].sum()
        print(f'wrote {out.name}: {len(df)} rows, {df["count"].sum():,.0f} adults 18+ | '
              + ', '.join(f'{k} {v / 1e6:.1f}M' for k, v in g.items()))
