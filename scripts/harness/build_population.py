"""NHGIS extract → population/adults_<year>_by_state_nhgis.csv in the harness's
long format (the columns of adults_1920_by_state.csv), one census at a time,
1790–1970. The 1920 and 1930 builder is here; the other censuses come from
build_population_republic (1790–1860), _early (1870–1910) and _mid (1940–1970).
The 1980+ tables are 18+ and only build_population_modern.py writes them.

    python3 scripts/harness/build_population.py 1930            # writes the table
    python3 scripts/harness/build_population.py 1920 --check    # compares with the hand-keyed 1920 table

Every row says how it was made in `note`: "tabulated" (straight from a census
table) or an [I]-tagged estimate (and from what).
"""
import argparse

import pandas as pd

import build_population_early
import build_population_mid
import build_population_republic
from nhgis_common import CACHE, COLS, STATE_CODE, assert_close, hand_vs_nhgis, load, off_cells, print_worst, rows


def read(ds: str) -> pd.DataFrame:
    d = load(ds)
    d = d[d.STATE.str.casefold().isin(STATE_CODE)].copy()
    d['state'] = d.STATE.str.casefold().map(STATE_CODE)
    return d.set_index('state')


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
                assert_close(d[list(mine)].sum(axis=1), x[list(theirs)].sum(axis=1), f'1930 {sex}: {mine} vs {theirs}')
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
        assert_close(d[fb], d[[nat, fp, al, unk]].sum(axis=1), f'{year} {sex}: foreign-born total vs citizenship split')
    return pd.DataFrame(out, columns=COLS)


BUILDERS = {**build_population_republic.BUILDERS, **build_population_early.BUILDERS,
            1920: year_1920_1930, 1930: year_1920_1930, **build_population_mid.BUILDERS}


def check_1920(nh: pd.DataFrame):
    j = hand_vs_nhgis(pd.read_csv(CACHE / 'population/adults_1920_by_state.csv'), nh).fillna(0)
    bad = off_cells(j)
    print(f'cells {len(j)}; total hand {j.hand.sum():,.0f} vs nhgis {j.nhgis.sum():,.0f}; '
          f'cells off by >50 and >0.5%: {len(bad)}')
    print_worst(bad)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('year', type=int)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.year not in BUILDERS:
        ap.error(f'no 21+ builder for {a.year}' + (' (1980 on: build_population_modern.py writes the 18+ tables)'
                                                   if a.year >= 1980 else ''))
    df = BUILDERS[a.year](a.year)
    if a.check and a.year == 1920:
        check_1920(df)
    else:
        out = CACHE / f'population/adults_{a.year}_by_state_nhgis.csv'
        df.to_csv(out, index=False)
        print(f'wrote {out.name}: {len(df)} rows, {df.state.nunique()} states, {df["count"].sum():,.0f} adults '
              f'({df[df.sex == "F"]["count"].sum():,.0f} women)')
