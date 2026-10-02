"""Build labels/state_pres_all.csv: certified presidential returns by state, 1868–2024.

Columns: year,state,rep,dem,other,total,third,ev_rep,ev_dem,ev_other,ev_total,chosen_by,source,note

Slots (orchestrator interface): R = Republican nominee, D = Democratic nominee
(1872: Greeley), O = everyone else; `third` = the named third candidate's own votes
(inside O): 1892 Weaver, 1912 T. Roosevelt, 1924 La Follette, 1948 Thurmond,
1968 Wallace, 1980 Anderson, 1992/1996 Perot.

Sources, in order of preference per state-year:
  1. 1916/1920/1924: the curated labels/state_pres_1916_1920_1924.csv (unchanged).
  2. 2024: FEC, "Official 2024 Presidential General Election Results" (Jan 16 2025),
     labels/raw/fec/2024presgeresults.xlsx (https://www.fec.gov/documents/5645/2024presgeresults.xlsx).
  3. Algara & Amlani county returns summed to the state (doi:10.7910/DVN/DGUMFI),
     when both its D and R shares are within 0.5 points of the Algara–Amlani state
     file (1868_2020_presvote.tab).
  4. Otherwise the Wikipedia "results by state" table for the year
     (labels/raw/wiki/wikipedia_<year>.html; those tables cite Leip / the Clerk / FEC).
  5. Otherwise the state file's percentages applied to the county-sum total [I].
EV: from the Algara–Amlani state file (dev/rev/oev), FEC for 2024.

Run: ~/.venvs/simharness/bin/python scripts/harness/build_returns.py
"""
from __future__ import annotations

import re
import sys
import warnings
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))  # the repo root
from simharness.config import CACHE  # noqa: E402
from simharness.geo import CODE_OF  # noqa: E402

RAW = CACHE / 'labels/raw'
OUT = CACHE / 'labels/state_pres_all.csv'
AA_SRC = 'Algara-Amlani county sum (doi:10.7910/DVN/DGUMFI)'
TAB_SRC = 'Algara-Amlani state file 1868_2020_presvote.tab'

# The named third candidate per year: a regex on the Wikipedia column header.
THIRD = {1892: r'Weaver', 1912: r'Roosevelt', 1924: r'La Follette', 1948: r'Thurmond',
         1968: r'Wallace', 1980: r'Anderson', 1992: r'Perot', 1996: r'Perot', 2000: r'Nader'}
# Republican and Democratic nominees' surnames (to find their Wikipedia columns).
NOMINEES = {
    1868: ('Grant', 'Seymour'), 1872: ('Grant', 'Greeley'), 1876: ('Hayes', 'Tilden'), 1880: ('Garfield', 'Hancock'),
    1884: ('Blaine', 'Cleveland'), 1888: ('Harrison', 'Cleveland'), 1892: ('Harrison', 'Cleveland'),
    1896: ('McKinley', 'Bryan'), 1900: ('McKinley', 'Bryan'), 1904: ('Roosevelt', 'Parker'), 1908: ('Taft', 'Bryan'),
    1912: ('Taft', 'Wilson'), 1916: ('Hughes', 'Wilson'), 1920: ('Harding', 'Cox'), 1924: ('Coolidge', 'Davis'),
    1928: ('Hoover', 'Smith'), 1932: ('Hoover', 'Roosevelt'), 1936: ('Landon', 'Roosevelt'), 1940: ('Willkie', 'Roosevelt'),
    1944: ('Dewey', 'Roosevelt'), 1948: ('Dewey', 'Truman'), 1952: ('Eisenhower', 'Stevenson'),
    1956: ('Eisenhower', 'Stevenson'), 1960: ('Nixon', 'Kennedy'), 1964: ('Goldwater', 'Johnson'),
    1968: ('Nixon', 'Humphrey'), 1972: ('Nixon', 'McGovern'), 1976: ('Ford', 'Carter'), 1980: ('Reagan', 'Carter'),
    1984: ('Reagan', 'Mondale'), 1988: ('Bush', 'Dukakis'), 1992: ('Bush', 'Clinton'), 1996: ('Dole', 'Clinton'),
    2000: ('Bush', 'Gore'), 2004: ('Bush', 'Kerry'), 2008: ('McCain', 'Obama'), 2012: ('Romney', 'Obama'),
    2016: ('Trump', 'Clinton'), 2020: ('Trump', 'Biden'), 2024: ('Trump', 'Harris'),
}
# Electoral votes counted by Congress (appointed electors; abstentions noted).
KNOWN_EV = {1868: 294, 1872: 352, 1876: 369, 1880: 369, 1884: 401, 1888: 401, 1892: 444, 1896: 447, 1900: 447,
            1904: 476, 1908: 483, 1960: 537}
for _y in range(1912, 1960, 4):
    KNOWN_EV[_y] = 531
for _y in range(1964, 2025, 4):
    KNOWN_EV[_y] = 538
# Electoral votes as cast where the state file differs (faithless electors,
# unpledged electors, splits): (ev_rep, ev_dem, ev_other). Sources: NARA
# Electoral College results; Congressional Quarterly's Guide to U.S. Elections.
EV_FIX = {
    (1948, 'TN'): (0, 11, 1), (1956, 'AL'): (0, 10, 1),
    (1960, 'AL'): (0, 5, 6), (1960, 'MS'): (0, 0, 8), (1960, 'OK'): (7, 0, 1),
    (1968, 'NC'): (12, 0, 1), (1972, 'VA'): (11, 0, 1), (1976, 'WA'): (8, 0, 1),
    (1988, 'WV'): (0, 5, 1), (2000, 'DC'): (0, 2, 1), (2004, 'MN'): (0, 9, 1),
    (2016, 'TX'): (36, 0, 2), (2016, 'WA'): (0, 8, 4), (2016, 'HI'): (0, 3, 1),
    (2020, 'NE'): (4, 1, 0),
}
# Legislature-chosen electors (no popular vote) and states with no electors.
LEGISLATURE = {(1868, 'FL'), (1876, 'CO')}
NOTES = {
    (1868, 'FL'): 'electors chosen by the legislature',
    (1876, 'CO'): 'electors chosen by the legislature (admitted Aug 1876)',
    (1872, 'AR'): 'electoral votes rejected by Congress',
    (1872, 'LA'): 'electoral votes rejected by Congress',
    (1872, 'GA'): "D = Greeley's electors; 3 votes cast for the dead Greeley rejected by Congress, kept in ev_dem",
    (1960, 'AL'): '6 of 11 electors unpledged (voted Byrd): ev_other; Kennedy vote = highest loyal elector (Wikipedia)',
    (1960, 'MS'): 'unpledged Democratic electors won (voted Byrd): ev_other',
    (1960, 'OK'): 'faithless elector (Byrd)',
    (1948, 'TN'): 'faithless elector (Thurmond)',
    (1956, 'AL'): 'faithless elector (W. B. Jones)',
    (1968, 'NC'): 'faithless elector (Wallace)',
    (1972, 'VA'): 'faithless elector (Hospers)',
    (1976, 'WA'): 'faithless elector (Reagan)',
    (1988, 'WV'): 'faithless elector (Bentsen)',
    (2000, 'DC'): 'one elector abstained (counted in ev_other)',
    (2020, 'NE'): 'district method: 4 R, 1 D',
    (2016, 'ME'): 'district method: 3 D, 1 R',
    (2008, 'NE'): 'district method: 4 R, 1 D',
    (2004, 'MN'): 'faithless elector (Edwards)',
    (2016, 'TX'): '2 faithless electors',
    (2016, 'WA'): '4 faithless electors',
    (2016, 'HI'): '1 faithless elector',
    (1948, 'AL'): 'Truman not on the ballot; Thurmond held the Democratic line (in O / third)',
    (1964, 'AL'): 'Johnson not on the ballot; unpledged Democratic electors in O',
    (1912, 'CA'): 'split: 11 T. Roosevelt, 2 Wilson',
    (1892, 'MI'): 'district method',
}


def _num(x):
    x = re.sub(r'\[.*?\]', '', str(x)).replace(',', '').replace('−', '-').replace('–', '-').strip()
    if x in ('-', '', 'nan', 'None') or not re.match(r'^-?\d+(\.\d+)?$', x):
        return np.nan
    return float(x)


def _state_code(name: str):
    n = re.sub(r'\[.*?\]|[†‡*§#^]|\(.*?\)', '', str(name)).strip()
    n = n.replace('D.C.', 'District of Columbia').replace('Washington, D.C.', 'District of Columbia')
    if n in CODE_OF:
        return CODE_OF[n]
    if n in ('Washington DC', 'Washington, District of Columbia', 'District of Columbia'):
        return 'DC'
    return None


def wiki(year: int) -> pd.DataFrame:
    """Per-state R, D, total and the named third's votes from the Wikipedia table."""
    f = RAW / f'wiki/wikipedia_{year}.html'
    if not f.exists():
        return pd.DataFrame()
    h = re.sub(r'(rowspan|colspan)="[^"0-9]*"', '', f.read_text())
    best = None
    for t in pd.read_html(StringIO(h)):
        if not isinstance(t.columns, pd.MultiIndex) or not 30 <= len(t) <= 75:
            continue
        sub = [str(c[-1]).strip() for c in t.columns]
        if not any(s in ('#', 'Votes', 'Vote') for s in sub):
            continue
        heads = ' '.join(str(c[-2]) for c in t.columns)
        r, d = NOMINEES[year]
        if r in heads and d in heads and ('Total' in heads or 'total' in heads or 'Margin' in heads):
            best = t
            break
    if best is None:
        return pd.DataFrame()
    t = best
    cols = list(t.columns)
    r, d = NOMINEES[year]

    def votes_col(pat, exclude=()):
        for c in cols:
            head, sub = str(c[-2]), str(c[-1]).strip()
            if sub in ('#', 'Votes', 'Vote') and re.search(pat, head) and not any(e in head for e in exclude):
                return c
        return None
    rc = votes_col(r, exclude=('Unpledged',))
    dc = votes_col(d, exclude=('Unpledged',))
    if year == 1912:
        rc = votes_col('Taft')
        dc = votes_col('Wilson')
    tc = votes_col(r'[Tt]otal')
    if tc is None:
        tcs = [c for c in cols if re.search(r'[Tt]otal', str(c[-2])) and str(c[-1]).strip() not in ('%',)]
        tc = tcs[0] if tcs else None
    thc = votes_col(THIRD[year]) if year in THIRD else None
    if year == 1904:  # Roosevelt is R in 1904, not a third
        thc = None
    rows = []
    for _, row in t.iterrows():
        vals = list(row.values)
        code = None
        for v in vals[:3]:
            code = _state_code(v)
            if code:
                break
        if code is None:
            continue
        rows.append({'state': code, 'wp_rep': _num(row[rc]) if rc is not None else np.nan,
                     'wp_dem': _num(row[dc]) if dc is not None else np.nan,
                     'wp_total': _num(row[tc]) if tc is not None else np.nan,
                     'wp_third': _num(row[thc]) if thc is not None else np.nan})
    w = pd.DataFrame(rows)
    if w.empty:
        return w
    # The first row per state is the statewide row (district rows don't map to a name).
    w = w.drop_duplicates('state', keep='first')
    w['year'] = year
    return w


def county_sums() -> pd.DataFrame:
    import pyreadr
    d = pyreadr.read_r(str(RAW / 'dataverse_shareable_presidential_county_returns_1868_2020.Rdata'))['pres_elections_release']
    d['year'] = d.election_year.astype(int)
    g = d.groupby(['year', 'state']).agg(aa_dem=('democratic_raw_votes', 'sum'), aa_rep=('republican_raw_votes', 'sum'),
                                         aa_total=('raw_county_vote_totals', 'sum'),
                                         aa_nmiss=('raw_county_vote_totals', lambda s: int(s.isna().sum()))).reset_index()
    return g


def fec2024() -> pd.DataFrame:
    x = pd.read_excel(RAW / 'fec/2024presgeresults.xlsx', header=0)
    x = x[x.STATE.astype(str).str.fullmatch(r'[A-Z]{2}')]
    rows = []
    for _, r in x.iterrows():
        rep, dem, tot = float(r['TRUMP']), float(r['HARRIS']), float(r['TOTAL VOTES'])
        evr = 0 if pd.isna(r['ELECTORAL VOTE: TRUMP (R)']) else int(r['ELECTORAL VOTE: TRUMP (R)'])
        evd = 0 if pd.isna(r['ELECTORAL VOTE: HARRIS (D)']) else int(r['ELECTORAL VOTE: HARRIS (D)'])
        rows.append({'year': 2024, 'state': r.STATE, 'rep': rep, 'dem': dem, 'total': tot, 'third': np.nan,
                     'ev_rep': evr, 'ev_dem': evd, 'ev_other': int(r['ELECTORAL VOTES']) - evr - evd,
                     'ev_total': int(r['ELECTORAL VOTES']), 'chosen_by': 'popular',
                     'source': 'FEC Official 2024 Presidential General Election Results (2025-01-16), 2024presgeresults.xlsx',
                     'note': {'NE': 'district method: 4 R, 1 D', 'ME': 'district method: 3 D, 1 R'}.get(r.STATE, '')})
    return pd.DataFrame(rows)


def legacy_1916_1924() -> pd.DataFrame:
    d = pd.read_csv(CACHE / 'labels/state_pres_1916_1920_1924.csv')
    rows = []
    for _, x in d.iterrows():
        evd, evr, evo = int(x.aa_state_ev_dem), int(x.aa_state_ev_rep), int(x.aa_state_ev_other)
        rows.append({'year': int(x.year), 'state': x.state, 'rep': x.rep, 'dem': x.dem, 'total': x.total,
                     'third': (x.wp_progressive if x.year == 1924 else np.nan),
                     'ev_rep': evr, 'ev_dem': evd, 'ev_other': evo,
                     'ev_total': int(x.nara_ev_total) if x.year == 1920 and pd.notna(x.nara_ev_total) else evr + evd + evo,
                     'chosen_by': 'popular', 'source': f'labels/state_pres_1916_1920_1924.csv ({x.value_source})',
                     'note': '' if pd.isna(x.note) else str(x.note)})
    return pd.DataFrame(rows)


def main():
    tab = pd.read_csv(RAW / '1868_2020_presvote.tab', sep='\t')
    tab = tab[tab.state != 'US']
    aa = county_sums()
    w = pd.concat([wiki(y) for y in range(1868, 2025, 4)], ignore_index=True)
    m = tab.merge(aa, on=['year', 'state'], how='left').merge(w, on=['year', 'state'], how='left')
    rows, report = [], []
    for _, x in m.iterrows():
        y, s = int(x.year), x.state
        if y in (1916, 1920, 1924):
            continue
        has_ev = pd.notna(x.totev) and x.totev > 0
        has_vote = pd.notna(x.dvote) or pd.notna(x.rvote)
        if not has_ev and not has_vote:
            if (y, s) in {(1868, 'TX'), (1868, 'MS'), (1868, 'VA')}:
                rows.append({'year': y, 'state': s, 'rep': 0, 'dem': 0, 'total': 0, 'third': np.nan, 'ev_rep': 0,
                             'ev_dem': 0, 'ev_other': 0, 'ev_total': 0, 'chosen_by': 'none', 'source': TAB_SRC,
                             'note': 'not yet readmitted: no electors'})
            continue
        ev = dict(ev_rep=int(x.rev or 0) if pd.notna(x.rev) else 0, ev_dem=int(x.dev) if pd.notna(x.dev) else 0,
                  ev_other=int(x.oev) if pd.notna(x.oev) else 0)
        if (y, s) in EV_FIX:
            ev = dict(zip(('ev_rep', 'ev_dem', 'ev_other'), EV_FIX[(y, s)]))
        ev['ev_total'] = ev['ev_rep'] + ev['ev_dem'] + ev['ev_other']
        note = NOTES.get((y, s), '')
        if (y, s) in LEGISLATURE or not has_vote:
            rows.append({'year': y, 'state': s, 'rep': 0, 'dem': 0, 'total': 0, 'third': np.nan, **ev,
                         'chosen_by': 'legislature', 'source': TAB_SRC, 'note': note})
            continue
        dp, rp = (x.dvote if pd.notna(x.dvote) else 0.0), (x.rvote if pd.notna(x.rvote) else 0.0)
        ok_aa = pd.notna(x.aa_total) and x.aa_total > 0 and x.aa_nmiss == 0 and \
            abs(100 * x.aa_dem / x.aa_total - dp) <= 0.5 and abs(100 * x.aa_rep / x.aa_total - rp) <= 0.5
        ok_w = pd.notna(x.wp_total) and x.wp_total > 0 and pd.notna(x.wp_rep) and \
            abs(100 * x.wp_rep / x.wp_total - rp) <= 1.5 and abs(100 * np.nan_to_num(x.wp_dem) / x.wp_total - dp) <= 1.5
        if pd.notna(x.aa_total) and x.aa_total > 0:
            off = max(abs(100 * x.aa_dem / x.aa_total - dp), abs(100 * x.aa_rep / x.aa_total - rp))
        else:
            off = np.nan
        if ok_aa:
            rep, dem, tot, src = x.aa_rep, x.aa_dem, x.aa_total, AA_SRC
        elif ok_w:
            rep, dem, tot, src = x.wp_rep, np.nan_to_num(x.wp_dem), x.wp_total, f'Wikipedia {y} results by state (labels/raw/wiki)'
        elif pd.notna(x.wp_total) and x.wp_total > 0:
            rep, dem, tot = x.wp_rep, np.nan_to_num(x.wp_dem), x.wp_total
            src = f'Wikipedia {y} results by state (labels/raw/wiki); differs from {TAB_SRC} by >1.5pt'
        elif pd.notna(x.aa_total) and x.aa_total > 0:
            tot = x.aa_total
            rep, dem = round(tot * rp / 100), round(tot * dp / 100)
            src = f'[I] {TAB_SRC} percentages x county-sum total'
        else:
            raise SystemExit(f'no counts for {y} {s}')
        if not ok_aa:
            report.append({'year': y, 'state': s, 'aa_off_pp': None if pd.isna(off) else round(off, 2), 'used': src[:40]})
        # A blank cell in the named third's column: not on that state's ballot.
        third = (0.0 if pd.isna(x.wp_third) else x.wp_third) if y in THIRD else np.nan
        tot = max(tot, rep + dem)  # 1868 MO: county total 9 short of R + D
        rows.append({'year': y, 'state': s, 'rep': rep, 'dem': dem, 'total': tot, 'third': third, **ev,
                     'chosen_by': 'popular', 'source': src, 'note': note})
    out = pd.concat([pd.DataFrame(rows), legacy_1916_1924(), fec2024()], ignore_index=True)
    for c in ('rep', 'dem', 'total'):
        out[c] = out[c].astype(float).round().astype('Int64')
    out['third'] = out.third.astype(float).round().astype('Int64')
    out['other'] = (out.total - out.rep - out.dem).astype('Int64')
    out = out[['year', 'state', 'rep', 'dem', 'other', 'total', 'third', 'ev_rep', 'ev_dem', 'ev_other', 'ev_total',
               'chosen_by', 'source', 'note']].sort_values(['year', 'state']).reset_index(drop=True)
    out.to_csv(OUT, index=False)
    print(f'wrote {OUT} ({len(out)} rows)')

    # Checks.
    ev = out.groupby('year').ev_total.sum()
    bad = {y: (int(ev[y]), KNOWN_EV[y]) for y in KNOWN_EV if int(ev.get(y, 0)) != KNOWN_EV[y]}
    print('EV totals off the known count:', bad or 'none')
    print('national EV by slot:')
    print(out.groupby('year')[['ev_rep', 'ev_dem', 'ev_other', 'ev_total']].sum().T.to_string())
    neg = out[out.other < 0]
    print('negative other:', neg[['year', 'state', 'rep', 'dem', 'total']].to_string() if len(neg) else 'none')
    r = pd.DataFrame(report)
    print(f'state-years where the county sum is >0.5pt off the state file: {len(r)}')
    if len(r):
        print(r.to_string())
    miss3 = out[out.year.isin(THIRD) & out.third.isna() & (out.chosen_by == 'popular')]
    print('named-third missing (state-years):', miss3[['year', 'state']].values.tolist())
    nat = out.groupby('year')[['rep', 'dem', 'other', 'total', 'third']].sum()
    print(nat.to_string())


if __name__ == '__main__':
    main()
