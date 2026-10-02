"""NHGIS extract → population/adults_<year>_by_state_nhgis.csv in the harness's
long format (the columns of adults_1920_by_state.csv), one census at a time.

    python3 scripts/harness/build_population.py 1930            # writes the table
    python3 scripts/harness/build_population.py 1920 --check    # compares with the hand-keyed 1920 table

Every row says how it was made in `note`: "tabulated" (straight from a census
table) or an [I]-tagged estimate (and from what).
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
from simharness.config import CACHE  # noqa: E402
from simharness.geo import CODE_OF  # noqa: E402

SRC = CACHE / 'population/nhgis/extract_1/nhgis0001_csv'
COLS = ['year', 'state', 'sex', 'group', 'race_as_recorded', 'label_as_recorded', 'count', 'vintage_mode', 'note',
        'source_table', 'source_url', 'page']
NHGIS_URL = 'https://www.nhgis.org'


def read(ds: str) -> pd.DataFrame:
    f = next(SRC.glob(f'nhgis0001_{ds}_*_state.csv'))
    d = pd.read_csv(f, encoding='latin-1', skiprows=[1])  # row 2 repeats the headers as descriptions
    code = {k.casefold(): v for k, v in CODE_OF.items()}  # NHGIS writes "District Of Columbia"
    d = d[d.STATE.str.casefold().isin(code)].copy()
    d['state'] = d.STATE.str.casefold().map(code)
    return d.set_index('state')


def rows(year, d, spec, table, note='tabulated'):
    """spec: [(column, sex, group, label)]"""
    out = []
    for st, r in d.iterrows():
        for col, sex, group, label in spec:
            out.append({'year': year, 'state': st, 'sex': sex, 'group': group, 'race_as_recorded': label.split(':')[0],
                        'label_as_recorded': label, 'count': float(r[col]), 'vintage_mode': 'truth', 'note': note,
                        'source_table': table, 'source_url': NHGIS_URL, 'page': ''})
    return out


def year_1920_1930(year: int) -> pd.DataFrame:
    """Both censuses tabulate 21+ by sex × race/nativity and the foreign-born
    white by sex × citizenship: complete, no estimates."""
    if year == 1920:
        d = read('ds43')
        rn = {'M': ['A7P001', 'A7P002', 'A7P003', 'A7P004', 'A7P005'], 'F': ['A7P006', 'A7P007', 'A7P008', 'A7P009', 'A7P010']}
        cz = {'M': ['A7Q001', 'A7Q002', 'A7Q003', 'A7Q004'], 'F': ['A7Q005', 'A7Q006', 'A7Q007', 'A7Q008']}
        t_rn, t_cz = 'NHGIS 1920_cPHAM NT13', 'NHGIS 1920_cPHAM NT15'
    else:
        d = read('ds54')
        # NT10's codebook labels interleave the sexes (BDQ001 NN male, BDQ002 NN female…), but
        # the values run sex-major like 1920's: males BDQ001–005, females BDQ006–010. Checked
        # below against NT7 (race by sex) and NT10 of 1930_cAge30 (white nativity by sex).
        rn = {'M': ['BDQ001', 'BDQ002', 'BDQ003', 'BDQ004', 'BDQ005'], 'F': ['BDQ006', 'BDQ007', 'BDQ008', 'BDQ009', 'BDQ010']}
        x = read('ds53')
        for sex, (nn, nf, fb, ng, ot), (wn, wf, b, o) in (('M', rn['M'], ('BDD001', 'BDD003', 'BDL003', 'BDL005')),
                                                          ('F', rn['F'], ('BDD002', 'BDD004', 'BDL004', 'BDL006'))):
            for mine, theirs in (((nn, nf), (wn,)), ((fb,), (wf,)), ((ng,), (b,)), ((ot,), (o,))):
                gap = (d[list(mine)].sum(axis=1) - x[list(theirs)].sum(axis=1)).abs().max()
                assert gap < 1, f'1930 {sex}: {mine} vs {theirs} differ by {gap}'
        cz = {'M': ['BDR001', 'BDR002', 'BDR003', 'BDR004'], 'F': ['BDR005', 'BDR006', 'BDR007', 'BDR008']}
        t_rn, t_cz = 'NHGIS 1930_cPAE NT10', 'NHGIS 1930_cPAE NT12'
    out = []
    for sex in ('M', 'F'):
        nn, nf, fb, ng, ot = rn[sex]
        out += rows(year, d, [(nn, sex, 'native_white_native_parentage', 'White: Native-born with native parentage'),
                              (nf, sex, 'native_white_foreign_or_mixed_parentage', 'White: Native-born with foreign or mixed parentage'),
                              (ng, sex, 'negro', 'Negro: Negro'),
                              (ot, sex, 'other_races', 'Other: Indian, Chinese, Japanese and all other races')], t_rn)
        nat, fp, al, unk = cz[sex]
        out += rows(year, d, [(nat, sex, 'foreign_white_naturalized', 'White: Foreign-born, naturalized'),
                              (fp, sex, 'foreign_white_first_papers', 'White: Foreign-born, first papers'),
                              (al, sex, 'foreign_white_alien', 'White: Foreign-born, alien'),
                              (unk, sex, 'foreign_white_unknown', 'White: Foreign-born, citizenship unknown')], t_cz)
        gap = (d[fb] - d[[nat, fp, al, unk]].sum(axis=1)).abs().max()
        assert gap < 1, f'{year} {sex}: foreign-born total and citizenship split differ by {gap}'
    return pd.DataFrame(out, columns=COLS)


BUILDERS = {1920: year_1920_1930, 1930: year_1920_1930}


def check_1920(nh: pd.DataFrame):
    from simharness.data import GROUP_MAP
    hand = pd.read_csv(CACHE / 'population/adults_1920_by_state.csv')
    hand = hand[hand.group != 'TOTAL']
    agg = lambda x: x.assign(g=x.group.map(lambda g: GROUP_MAP.get(g, g))).groupby(['state', 'sex', 'g'])['count'].sum()  # noqa: E731
    a, b = agg(hand), agg(nh)
    j = pd.concat([a.rename('hand'), b.rename('nhgis')], axis=1).fillna(0)
    j['diff'] = j.nhgis - j.hand
    j['rel'] = j['diff'] / j.hand.clip(lower=1)
    bad = j[(j['diff'].abs() > 50) & (j.rel.abs() > 0.005)]
    print(f'cells {len(j)}; total hand {j.hand.sum():,.0f} vs nhgis {j.nhgis.sum():,.0f}; '
          f'cells off by >50 and >0.5%: {len(bad)}')
    if len(bad):
        print(bad.sort_values('diff', key=abs, ascending=False).head(15).to_string())


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('year', type=int)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    # Other censuses live in sibling modules (each exports BUILDERS), imported
    # here so they can import read/rows/COLS from this module.
    import importlib
    for m in ('build_population_early', 'build_population_mid', 'build_population_modern', 'build_population_republic'):
        try:
            BUILDERS.update(importlib.import_module(m).BUILDERS)
        except ModuleNotFoundError as e:
            if e.name != m:
                raise
    df = BUILDERS[a.year](a.year)
    if a.check and a.year == 1920:
        check_1920(df)
    else:
        out = CACHE / f'population/adults_{a.year}_by_state_nhgis.csv'
        df.to_csv(out, index=False)
        print(f'wrote {out.name}: {len(df)} rows, {df.state.nunique()} states, {df["count"].sum():,.0f} adults '
              f'({df[df.sex == "F"]["count"].sum():,.0f} women)')
