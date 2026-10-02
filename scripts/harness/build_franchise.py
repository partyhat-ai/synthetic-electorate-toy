"""Build franchise/state_franchise_all.csv: the legal franchise by state, presidential years 1868–1968.

Columns: year,state,poll_tax,literacy_test,alien_voting,women_vote,white_can,black_can,
         felony_disenfranchised_share,voting_age,chosen_by,source,note

Sources:
  poll_tax, literacy_test: Gray & Jenkins (2024) State-Level Data File, doi:10.7910/DVN/QIY9EM,
    rows elec_type==1 (presidential), 1872–1968. 1868 uses the state's 1870 row [I]
    (the file starts in 1870). DC (1964, 1968): no poll tax, no literacy test.
  women_vote: Teele (2018) presidential-suffrage year (franchise/women_suffrage_pre19th.csv)
    <= election year; every state from 1920 (19th Amendment).
  alien_voting: declarant-alien voting, Keyssar (2000) The Right to Vote, Table A.12, and
    Hayduk (2006) Democracy for All, ch. 2 — year ranges transcribed from those tables
    without the book to hand, so tagged [I] (Gray & Jenkins has no alien-voting field).
  voting_age: 21; GA 18 from 1944 (1943 amendment); KY 18 from 1956 (1955 amendment);
    AK 19 and HI 20 from 1960 (statehood constitutions).
  black_can / white_can: 1 from 1870 (15th Amendment). 1868: Black men barred by law
    outside New England (except CT), WI, NE, and the reconstructed South; NY's $250
    property test for Black men [I]; ex-Confederate test oaths in MO, TN, WV, AR [I].
  felony_disenfranchised_share: blank (no state-level estimate before 1970; Gray &
    Jenkins' exfelon law flag is kept in the note).
  chosen_by: from labels/state_pres_all.csv.

Run: ~/.venvs/simharness/bin/python scripts/harness/build_franchise.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))  # the repo root
from simharness.config import CACHE  # noqa: E402

FR = CACHE / 'franchise'
OUT = FR / 'state_franchise_all.csv'
YEARS = list(range(1868, 1969, 4))

# Declarant-alien voting for president: state → (first, last) election year it applied.
# Keyssar (2000) Table A.12; Hayduk (2006) [I].
ALIEN = {
    'WI': (1848, 1908), 'MI': (1850, 1894), 'IN': (1851, 1921), 'MN': (1857, 1896), 'OR': (1859, 1914),
    'KS': (1861, 1918), 'NE': (1867, 1918), 'MO': (1865, 1921), 'TX': (1869, 1921), 'AR': (1868, 1926),
    'AL': (1867, 1901), 'FL': (1868, 1894), 'GA': (1868, 1877), 'SC': (1868, 1895), 'LA': (1879, 1898),
    'CO': (1876, 1902), 'ND': (1889, 1909), 'SD': (1889, 1918),
}
# 1868: Black men legally able to vote (share of adult Black men) [I].
BLACK_1868 = {s: 0.0 for s in ['CA', 'CT', 'DE', 'IL', 'IN', 'KS', 'KY', 'MD', 'MI', 'MO', 'NJ', 'NV', 'OH', 'OR',
                               'PA', 'WV', 'IA', 'MN']}
BLACK_1868['NY'] = 0.1  # $250 freehold test for Black men only [I]
# 1868: whites barred by ex-Confederate test oaths [I].
WHITE_1868 = {'MO': 0.80, 'TN': 0.70, 'WV': 0.85, 'AR': 0.85}


def voting_age(state: str, year: int) -> int:
    if year >= 1972:
        return 18
    if state == 'GA' and year >= 1944:
        return 18
    if state == 'KY' and year >= 1956:
        return 18
    if state == 'AK' and year >= 1960:
        return 19
    if state == 'HI' and year >= 1960:
        return 20
    return 21


def main():
    gj = pd.read_csv(FR / 'raw/GrayJenkins_State-Level_Data_File.tab', sep='\t')
    icp = pd.read_csv(FR / 'grayjenkins_state_franchise_1916_1920_1924.csv').drop_duplicates('state')
    code = dict(zip(icp.icpsr_state.astype(int), icp.state))
    gj['st'] = gj.state.astype(int).map(code)
    pres = gj[gj.elec_type == 1].set_index(['year', 'st'])
    first70 = gj[gj.year == 1870].sort_values('elec_type').drop_duplicates('st').set_index('st')
    w = pd.read_csv(FR / 'women_suffrage_pre19th.csv').set_index('state')
    wy = w.presidential_suffrage_year.combine_first(w.full_suffrage_year).to_dict()
    ret = pd.read_csv(CACHE / 'labels/state_pres_all.csv')
    rows = []
    for _, r in ret[ret.year.isin(YEARS)].iterrows():
        y, s = int(r.year), r.state
        notes, src = [], []
        if s == 'DC':
            pt, lt, ex = 0, 0, np.nan
            src.append('DC: no poll tax or literacy test')
        elif y == 1868:
            g = first70.loc[s] if s in first70.index else None
            pt, lt, ex = (np.nan, np.nan, np.nan) if g is None else (g.poll_tax, g.lit_test, g.exfelon)
            src.append('Gray&Jenkins doi:10.7910/DVN/QIY9EM 1870 row [I]')
        else:
            g = pres.loc[(y, s)]
            pt, lt, ex = g.poll_tax, g.lit_test, g.exfelon
            src.append('Gray&Jenkins doi:10.7910/DVN/QIY9EM elec_type 1')
        py = wy.get(s)
        wv = int(y >= 1920 or (py is not None and pd.notna(py) and float(py) <= y))
        if y == 1920 and s in ('GA', 'MS'):
            notes.append('women could not register in time for Nov 1920 (closed_1920)')
        src.append('women: Teele doi:10.7910/DVN/EVYI2H')
        a = ALIEN.get(s)
        av = int(a is not None and a[0] <= y <= a[1])
        if a is not None:
            src.append('alien: Keyssar 2000 Table A.12 / Hayduk 2006 [I]')
        bc = BLACK_1868.get(s, 1.0) if y == 1868 else 1.0
        wc = WHITE_1868.get(s, 1.0) if y == 1868 else 1.0
        if y == 1868 and (s in BLACK_1868 or s in WHITE_1868):
            notes.append('pre-15th Amendment exclusions [I]')
        if pd.notna(ex):
            notes.append(f'exfelon law (GJ)={int(ex)}')
        rows.append({'year': y, 'state': s, 'poll_tax': pt, 'literacy_test': lt, 'alien_voting': av, 'women_vote': wv,
                     'white_can': wc, 'black_can': bc, 'felony_disenfranchised_share': np.nan,
                     'voting_age': voting_age(s, y), 'chosen_by': r.chosen_by, 'source': '; '.join(src),
                     'note': '; '.join(notes)})
    out = pd.DataFrame(rows)
    for c in ('poll_tax', 'literacy_test'):
        out[c] = out[c].astype('Int64')
    out.to_csv(OUT, index=False)
    print(f'wrote {OUT} ({len(out)} rows)')
    print(out.groupby('year')[['poll_tax', 'literacy_test', 'alien_voting', 'women_vote']].sum().T.to_string())
    print('missing poll_tax:', out[out.poll_tax.isna()][['year', 'state']].values.tolist())


if __name__ == '__main__':
    main()
