"""Early-republic labels and franchise, 1789–1864.

    python3 scripts/harness/build_republic.py returns     # → labels/state_pres_1789_1864.csv
    python3 scripts/harness/build_republic.py franchise   # → franchise/state_franchise_1789_1864.csv
    python3 scripts/harness/build_republic.py all

Returns are parsed from the per-election Wikipedia "results by state" tables
(cached under labels/raw/wikipedia_1789_1864/; those tables cite Tufts' "A New
Nation Votes" for 1789–1824 and Dubin / CQ / Leip for 1824+). How each state
chose its electors is hand-keyed (CHOSEN below; Every Vote Equal Table 2.1 /
the Wikipedia pages), as is the national EV check (NATIONAL_EV).

Party slots (fixed across agents): R = Federalist (1789–1816; Washington in
1789/92 with D=0; DeWitt Clinton 1812 as the Federalist-backed candidate),
J.Q. Adams 1824, National Republican 1828/32, Whig 1836–52 (all four 1836
Whigs), Republican 1856+. D = Democratic-Republican 1796–1820, Jackson 1824,
Democratic 1828+ (Douglas in 1860). O = everyone else; R=0 in 1820. Named
thirds (own votes in `third`): 1832 Wirt, 1848 Van Buren, 1856 Fillmore,
1860 Breckinridge.

Franchise rules are hand-coded from Keyssar, The Right to Vote (2009 ed.),
Tables A.1–A.4, with eligibility shares tagged [I] (see FRANCHISE notes and
notes/G.md).
"""
import io
import re
import sys
import urllib.parse
import urllib.request
import warnings
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
from simharness.config import CACHE  # noqa: E402
from simharness.geo import CODE_OF  # noqa: E402

warnings.filterwarnings('ignore')
RAW = CACHE / 'labels/raw/wikipedia_1789_1864'
YEARS = list(range(1789, 1793, 3)) + list(range(1796, 1865, 4))  # 1789, 1792, 1796 … 1864
WP = 'https://en.wikipedia.org/wiki/{}_United_States_presidential_election'
CODE = {k.casefold(): v for k, v in CODE_OF.items()}


def page(y: int) -> str:
    f = RAW / f'{y}.html'
    if not f.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        t = urllib.parse.quote(f'{"1788–89" if y == 1789 else y}_United_States_presidential_election')
        req = urllib.request.Request(f'https://en.wikipedia.org/w/index.php?title={t}&action=render',
                                     headers={'User-Agent': 'SimulacraHarness/1.0 (historical research)'})
        f.write_bytes(urllib.request.urlopen(req).read())
    return f.read_text()


def tables(y):
    return pd.read_html(io.StringIO(page(y)))


# ---------------------------------------------------------------- method of choice
# Legislature-chosen states (everything else that appointed electors was popular).
LEG = {
    1789: 'CT GA NJ SC', 1792: 'CT DE GA NJ NY NC RI SC VT', 1796: 'CT DE NJ NY RI SC TN VT',
    1800: 'CT DE GA MA NH NJ NY PA SC TN VT', 1804: 'CT DE GA NY SC VT', 1808: 'CT DE GA MA NY SC VT',
    1812: 'CT DE GA LA NJ NY NC SC VT', 1816: 'CT DE GA IN LA MA NY SC VT',
    1820: 'AL DE GA IN LA MO NY SC VT', 1824: 'DE GA LA NY SC VT', 1828: 'DE SC',
    **{y: 'SC' for y in range(1832, 1861, 4)}, 1864: '',
}
NONE = {1789: {'NY': 'legislature deadlocked; no electors appointed'},
        1864: {**{s: 'seceded; no electors' for s in 'AL AR FL GA MS NC SC TX VA'.split()},
               'LA': 'held a Union-occupation election; Congress did not count its 7 EVs',
               'TN': 'held a Union-occupation election; Congress did not count its 10 EVs'}}
CHOSEN_NOTE = {
    (1789, 'MA'): 'hybrid: voters nominated by district, legislature chose (popular vote = nominating ballots)',
    (1792, 'MA'): 'hybrid: district popular vote, legislature filled seats lacking a majority',
    (1796, 'MA'): 'hybrid: district popular vote, legislature filled seats lacking a majority',
    (1789, 'NH'): 'popular vote, legislature chose where no majority',
    (1792, 'KY'): 'electors chosen by the state electoral college of senators [I: coded popular, no returns]',
    (1796, 'KY'): 'no surviving returns',
    (1796, 'TN'): 'electors chosen by electors appointed by the legislature',
    (1800, 'TN'): 'electors chosen by electors appointed by the legislature',
}

RET_NOTE = {
    (1860, 'NJ'): 'anti-Lincoln fusion ticket (Douglas/Bell/Breckinridge) counted in other; 3 fusion electors voted Douglas',
    (1860, 'NY'): 'anti-Lincoln fusion ticket counted in other',
    (1860, 'PA'): 'Breckinridge-headed fusion ticket counted in other; straight Douglas votes in dem',
    (1860, 'RI'): 'Douglas-led fusion ticket counted in dem',
    (1812, 'PA'): 'returns not extant as a party split (leading elector ran on both tickets)',
    (1828, 'NY'): 'votes are the at-large tally; 34 district electors chosen in districts',
    (1828, 'ME'): 'votes are the at-large tally; 7 district electors',
    (1820, 'MA'): 'Federalist elector slates (no Federalist presidential candidate) counted in other (R=0 in 1820)',
}

# National electoral vote check: (R, D, O, appointed electors)
NATIONAL_EV = {
    1789: (69, 0, 0, 73), 1792: (132, 0, 0, 135), 1796: (71, 67, 0, 138), 1800: (65, 73, 0, 138),
    1804: (14, 162, 0, 176), 1808: (47, 122, 6, 176), 1812: (89, 128, 0, 218), 1816: (34, 183, 0, 221),
    1820: (0, 231, 1, 235), 1824: (84, 99, 78, 261), 1828: (83, 178, 0, 261), 1832: (49, 219, 18, 288),
    1836: (124, 170, 0, 294), 1840: (234, 60, 0, 294), 1844: (105, 170, 0, 275), 1848: (163, 127, 0, 290),
    1852: (42, 254, 0, 296), 1856: (114, 174, 8, 296), 1860: (180, 12, 111, 303), 1864: (212, 21, 0, 234),
}
EV_NOTE = {
    1789: 'pre-12th Amendment (two votes per elector): slot EVs = electors voting for Washington; Adams 34 etc. were second votes',
    1792: 'pre-12th Amendment: slot EVs = votes for Washington (132 of 135; 3 not cast); Adams/Clinton were second votes',
    1796: 'pre-12th Amendment: R = Adams votes, D = Jefferson votes; MD elector voting Adams+Jefferson counted R',
    1800: 'pre-12th Amendment: Jefferson 73 = Burr 73 tie (D), House chose Jefferson Feb 1801; R = Adams 65',
    1824: 'no EV majority: House chose Adams (R) on 9 Feb 1825; O = Crawford 41 + Clay 37',
    1836: 'R = all Whigs (Harrison 73, White 26, Webster 14, Mangum 11)',
    1860: 'O = Breckinridge 72 + Bell 39',
    1864: 'LA and TN EVs not counted; one NV elector did not vote',
}


# ---------------------------------------------------------------- parsing
NONNUM_ZERO = ('—', '-', '–', 'no ballots', 'no candidate', '', 'nan')


def cell(x):
    """→ (value|None, partial, missing)."""
    s = re.sub(r'\[[^\]]*\]', '', str(x)).strip()
    if s.lower() in NONNUM_ZERO:
        return 0.0, False, False
    partial = s.endswith('+')
    s2 = s.rstrip('+').replace(',', '').replace('%', '')
    try:
        return float(s2), partial, False
    except ValueError:
        return None, False, True


def state_of(x):
    s = re.sub(r'\[[^\]]*\]', '', str(x))
    s = re.sub(r'\(.*?\)', '', s)
    s = re.sub(r'[^A-Za-z \-–]', '', s)
    s = re.split(r'[–-]', s)[0].strip()
    return CODE.get(s.casefold())


def is_district(x):
    s = re.sub(r'\[[^\]]*\]', '', str(x))
    return bool(re.search(r'[–-]', s))


def flat(t):
    if isinstance(t.columns, pd.MultiIndex):
        return [(str(a), str(b)) for a, b in t.columns]
    return [(str(a), str(a)) for a in t.columns]


def popular(t, slotmap):
    """slotmap: [(substring of group header, slot)]; slot in R/D/O/T (T = named third, also O).
    Returns {state: dict(rep, dem, other, third, total, partial, missing, ev_*)}."""
    cols = flat(t)
    groups = {}
    for j, (g, sub) in enumerate(cols):
        gl = g.lower()
        slot = next((s for k, s in slotmap if k.lower() in gl), None)
        if slot is None and any(k in gl for k in ('total',)):
            slot = 'TOT'
        if slot is None:
            continue
        sl = sub.lower()
        kind = 'ev' if ('elector' in sl or 'e.v' in sl) else 'v' if (sl in ('#', 'votes', 'no.', 'votes cast', 'total') or (slot == 'TOT' and 'unnamed' not in sl)) else None
        if kind:
            groups.setdefault((slot, kind), []).append(j)
    out = {}
    has_at_large = {state_of(r.iloc[0]) for _, r in t.iterrows() if state_of(r.iloc[0]) and not is_district(r.iloc[0])}
    for _, r in t.iterrows():
        st = state_of(r.iloc[0])
        if not st:
            continue
        skip_votes = st in has_at_large and is_district(r.iloc[0])   # districts re-tally the at-large ballots
        d = out.setdefault(st, {'rep': 0.0, 'dem': 0.0, 'other': 0.0, 'third': 0.0, 'total': 0.0, 'partial': False,
                                'missing': False, 'any': False, 'ev_rep': 0.0, 'ev_dem': 0.0, 'ev_other': 0.0})
        for (slot, kind), js in groups.items():
            for j in js:
                v, p, m = cell(r.iloc[j])
                if kind == 'ev':
                    if v is not None and slot != 'TOT':
                        d[{'R': 'ev_rep', 'D': 'ev_dem'}.get(slot, 'ev_other')] += v
                    continue
                if skip_votes:
                    continue
                if m:
                    d['missing'] = True
                    continue
                d['partial'] |= p and slot in ('R', 'D', 'T')   # '27+' scattering is not a partial return
                d['any'] |= (v or 0) > 0
                if slot == 'TOT':
                    d['total'] += v
                else:
                    d[{'R': 'rep', 'D': 'dem'}.get(slot, 'other')] += v
                    if slot == 'T':
                        d['third'] += v
    return out


def ev_by_candidate(t, slotmap, electors_col):
    """Per-candidate EV tables (pre-12th Amendment, and 1808/1812): slot EVs per state."""
    cols = flat(t)
    out = {}
    for _, r in t.iterrows():
        st = state_of(r.iloc[0])
        if not st:
            continue
        e = {'R': 0.0, 'D': 0.0, 'O': 0.0}
        for j, (g, sub) in enumerate(cols):
            name = sub if g != sub else g
            if g.lower().startswith('for vice'):
                continue
            slot = next((s for k, s in slotmap if k.lower() in name.lower()), None)
            if slot:
                v, _, _ = cell(r.iloc[j])
                e[slot] += v or 0
        n, _, _ = cell(r.iloc[electors_col])
        out[st] = (e, n)
    return out


# Table index of the popular-vote results-by-state table and the slot map, per year.
POP = {
    1789: (9, [('Anti-Federalist', 'O'), ('Federalist', 'R'), ('Total', 'TOT')]),
    1792: (5, [('Democratic-Republican', 'O'), ('Federalist', 'R')]),
    1796: (7, [('Adams', 'R'), ('Jefferson', 'D'), ('State total', 'TOT')]),
    1800: (8, [('Jefferson', 'D'), ('Adams', 'R'), ('Other', 'O'), ('State total', 'TOT')]),
    1804: (9, [('Jefferson', 'D'), ('Federalist', 'R'), ('Other', 'O'), ('Total', 'TOT')]),
    1808: (10, [('Madison', 'D'), ('Pinckney', 'R'), ('Monroe', 'O'), ('Other', 'O')]),
    1812: (15, [('Madison', 'D'), ('Clinton', 'R'), ('Other', 'O')]),
    1816: (12, [('Monroe', 'D'), ('Federalist', 'R'), ('Others', 'O'), ('Total', 'TOT')]),
    1820: (9, [('Monroe', 'D'), ('Federalist', 'O'), ('Others', 'O')]),
    1824: (8, [('Jackson', 'D'), ('Adams', 'R'), ('Clay', 'O'), ('Crawford', 'O'), ('Other', 'O'), ('State total', 'TOT')]),
    1828: (7, [('Jackson', 'D'), ('Adams', 'R'), ('State Total', 'TOT')]),
    1832: (14, [('Jackson', 'D'), ('Clay', 'R'), ('Wirt', 'T'), ('Floyd', 'O'), ('State Total', 'TOT')]),
    1836: (13, [('Van Buren', 'D'), ('Whig', 'R'), ('Total', 'TOT')]),
    1840: (10, [('Harrison', 'R'), ('Van Buren', 'D'), ('Birney', 'O'), ('State Total', 'TOT')]),
    1844: (9, [('Polk', 'D'), ('Clay', 'R'), ('Birney', 'O'), ('State Total', 'TOT')]),
    1848: (12, [('Taylor', 'R'), ('Cass', 'D'), ('Van Buren', 'T'), ('State Total', 'TOT')]),
    1852: (9, [('Pierce', 'D'), ('Scott', 'R'), ('Hale', 'O'), ('Others', 'O'), ('State Total', 'TOT')]),
    1856: (13, [('Buchanan', 'D'), ('Fremont', 'R'), ('Frémont', 'R'), ('Fillmore', 'T'), ('State Total', 'TOT')]),
    1860: (14, [('Lincoln', 'R'), ('Douglas', 'D'), ('Breckinridge', 'T'), ('Bell', 'O'), ('Other', 'O'), ('State Total', 'TOT')]),
    1864: (13, [('Lincoln', 'R'), ('McClellan', 'D'), ('State Total', 'TOT')]),
}
# Years whose EVs come from a per-candidate table: (table index, slot map, electors column)
EVTAB = {
    1789: (10, [('Washington', 'R')], 1),
    1792: (6, [('Washington', 'R')], 1),
    1796: (6, [('John Adams', 'R'), ('Jefferson', 'D')], 1),
    1800: (7, [('John Adams', 'R'), ('Jefferson', 'D')], 1),
    1808: (9, [('Madison', 'D'), ('Pinckney', 'R'), ('Clinton', 'O')], 1),
    1812: (14, [('Madison', 'D'), ('DeWitt Clinton', 'R')], 1),
}
# Electors appointed per state in years read from the popular table (state EV column = column 1).


def returns() -> pd.DataFrame:
    rows = []
    for y in YEARS:
        ts = tables(y)
        ti, smap = POP[y]
        pop = popular(ts[ti], smap)
        # EVs and the state roster
        if y in EVTAB:
            ei, emap, ecol = EVTAB[y]
            evs = ev_by_candidate(ts[ei], emap, ecol)
        else:
            evs = {}
            t = ts[ti]
            for _, r in t.iterrows():
                st = state_of(r.iloc[0])
                if st:
                    n, _, _ = cell(r.iloc[1])
                    e, _ = evs.get(st, ({'R': 0, 'D': 0, 'O': 0}, 0))
                    p = pop.get(st, {})
                    evs[st] = ({'R': p.get('ev_rep', 0), 'D': p.get('ev_dem', 0), 'O': p.get('ev_other', 0)},
                               evs.get(st, (None, 0))[1] + (n or 0))
        if y == 1789:
            evs.setdefault('NY', ({'R': 0, 'D': 0, 'O': 0}, 0))
        leg = set(LEG[y].split())
        for st in sorted(set(evs) | set(NONE.get(y, {}))):
            e, n = evs.get(st, ({'R': 0, 'D': 0, 'O': 0}, 0))
            notes = []
            if st in NONE.get(y, {}):
                chosen, n, e = 'none', 0, {'R': 0, 'D': 0, 'O': 0}
                notes.append(NONE[y][st])
            elif st in leg:
                chosen = 'legislature'
            else:
                chosen = 'popular'
            if (y, st) in CHOSEN_NOTE:
                notes.append(CHOSEN_NOTE[(y, st)])
            if y == 1796 and e['R'] + e['D'] > n:   # MD: one elector voted Adams + Jefferson
                e['D'] = n - e['R']
            if y in (1789, 1792):
                e['O'] = 0
            p = pop.get(st)
            rec = {'year': y, 'state': st, 'rep': None, 'dem': None, 'other': None, 'total': None, 'third': None,
                   'ev_rep': e['R'], 'ev_dem': e['D'], 'ev_other': e['O'], 'ev_total': n, 'chosen_by': chosen,
                   'source': f'Wikipedia "{y} United States presidential election", results by state '
                             f'({"Tufts A New Nation Votes" if y <= 1824 else "Dubin/CQ/Leip"} figures as cited)'}
            if chosen == 'popular':
                if p and p['any'] and not p['missing']:
                    tot = max(p['total'], p['rep'] + p['dem'] + p['other'])
                    rec.update(rep=p['rep'], dem=p['dem'], other=tot - p['rep'] - p['dem'], total=tot, third=p['third'])
                    if p['partial']:
                        notes.append('partial returns (some counties/districts missing): do not use for turnout')
                elif p and p['any'] and (p['rep'] + p['dem'] > 0 or y <= 1792):
                    tot = p['rep'] + p['dem'] + p['other']
                    rec.update(rep=p['rep'], dem=p['dem'], other=p['other'], total=tot, third=p['third'])
                    notes.append('partial returns (some districts/candidates not extant): do not use for turnout')
                else:
                    notes.append('popular vote held but returns not extant in the compilation')
            if (y, st) in RET_NOTE:
                notes.append(RET_NOTE[(y, st)])
            rec['note'] = '; '.join(notes)
            rows.append(rec)
    df = pd.DataFrame(rows)
    # Hand fixes where the tables do not carry the EV split cleanly.
    df = fix_ev(df)
    for y, (r, d, o, n) in NATIONAL_EV.items():
        s = df[df.year == y][['ev_rep', 'ev_dem', 'ev_other', 'ev_total']].sum()
        got = (s.ev_rep, s.ev_dem, s.ev_other, s.ev_total)
        flag = '' if got == (r, d, o, n) else f'   <-- expected {(r, d, o, n)}'
        print(y, 'EV R/D/O/appointed', tuple(int(x) for x in got), flag)
    for y, t in EV_NOTE.items():
        i = df.index[(df.year == y)][0]
        df.loc[i, 'note'] = '; '.join(x for x in [df.loc[i, 'note'], f'[national EV] {t}'] if x)
    return df


def fix_ev(df):
    def setev(y, st, r=None, d=None, o=None, n=None):
        i = df.index[(df.year == y) & (df.state == st)][0]
        for k, v in (('ev_rep', r), ('ev_dem', d), ('ev_other', o), ('ev_total', n)):
            if v is not None:
                df.loc[i, k] = v
    setev(1812, 'OH', n=8)          # 8 electors appointed, 7 voted
    setev(1816, 'DE', r=3)          # 4 appointed, 3 voted (King)
    setev(1816, 'MD', r=0)          # 3 Federalist district electors did not vote
    setev(1864, 'NV', n=3)          # 3 appointed, 1 elector snowbound
    return df


# ---------------------------------------------------------------- franchise
# Per state: list of (first election year, rule) in force from that election on. Rule fields:
#   q   = qualification type: 'prop' (freehold/estate), 'tax' (taxpaying, incl. militia/road-work
#         alternatives), 'univ' (adult male, residence only)
#   wc  = [I] share of adult white men meeting it (Keyssar ch. 2 & App. A; Engerman & Sokoloff 2005;
#         Williamson 1960 — rough, ±0.1)
#   blk = free Black men: 'eq' (same terms as whites), 'no' (barred), 'ny250' ($250 freehold, NY 1821)
#   lit / alien / women flags; why = the legal change, with its date
UNIV, TAXQ = 0.95, 0.88   # residence/pauper exclusions; taxpaying exclusions
F = {
    'CT': [(1789, dict(q='prop', wc=0.65, blk='eq', why='freehold 40s/yr or £40 personal estate')),
           (1816, dict(q='prop', wc=0.65, blk='no', why='1814 statute limits to white men')),
           (1820, dict(q='tax', wc=TAXQ, blk='no', why='1818 constitution: taxpaying or militia service or $7 freehold')),
           (1848, dict(q='univ', wc=UNIV, blk='no', why='1845 amendment drops tax/militia')),
           (1856, dict(q='univ', wc=0.93, blk='no', lit=1, why='1855 amendment: must read the constitution or statutes'))],
    'DE': [(1789, dict(q='prop', wc=0.60, blk='eq', why='1776: 50-acre freehold or £40 estate')),
           (1792, dict(q='tax', wc=0.85, blk='no', why='1792 constitution: white freemen who paid a state/county tax'))],
    'GA': [(1789, dict(q='tax', wc=TAXQ, blk='no', why='1789/1798 constitutions: white(1777)/citizen men who paid all taxes due'))],
    'MD': [(1789, dict(q='prop', wc=0.60, blk='eq', why='1776: 50-acre freehold or £30 property; free Black owners not barred by text')),
           (1804, dict(q='univ', wc=UNIV, blk='no', why='1801-02 amendment drops property, limits to white men'))],
    'MA': [(1789, dict(q='prop', wc=0.75, blk='eq', why='1780: freehold £3/yr income or £60 estate')),
           (1824, dict(q='tax', wc=TAXQ, blk='eq', why='1821 amendment: paid a state or county tax')),
           (1860, dict(q='tax', wc=0.85, blk='eq', lit=1, why='1857 amendment: read the constitution and write one’s name'))],
    'NH': [(1789, dict(q='tax', wc=0.90, blk='eq', why='1784: male inhabitants paying a poll tax')),
           (1792, dict(q='univ', wc=UNIV, blk='eq', why='1792 constitution drops the poll-tax requirement'))],
    'NJ': [(1789, dict(q='prop', wc=0.75, blk='eq', alien=1, why='1776: all inhabitants worth £50 (no sex, race or citizenship bar)')),
           (1792, dict(q='prop', wc=0.75, blk='eq', alien=1, women=1, why='1790 election law says "he or she": propertied single women and widows vote')),
           (1808, dict(q='tax', wc=TAXQ, blk='no', why='1807 act: white male citizens who paid a tax')),
           (1844, dict(q='univ', wc=UNIV, blk='no', why='1844 constitution drops taxpaying'))],
    'NY': [(1789, dict(q='prop', wc=0.70, blk='eq', why='1777: £20 freehold or 40s rent (Assembly)')),
           (1824, dict(q='tax', wc=0.90, blk='ny250', why='1821 constitution: whites pay tax or serve in militia/highway; Black men need $250 freehold')),
           (1828, dict(q='univ', wc=UNIV, blk='ny250', why='1826 amendment: white manhood suffrage; $250 rule kept for Black men'))],
    'NC': [(1789, dict(q='tax', wc=0.85, blk='eq', why='1776: Commons franchise = freemen who paid public taxes (Senate needed 50 acres)')),
           (1836, dict(q='tax', wc=0.85, blk='no', why='1835 amendments bar free Black men')),
           (1860, dict(q='tax', wc=TAXQ, blk='no', why='1857 amendment drops the Senate 50-acre rule'))],
    'PA': [(1789, dict(q='tax', wc=TAXQ, blk='eq', why='1776/1790: freemen who paid a state/county tax within 2 years (sons of electors 21-22 exempt)')),
           (1840, dict(q='tax', wc=TAXQ, blk='no', why='1838 constitution adds "white"'))],
    'RI': [(1789, dict(q='prop', wc=0.50, blk='eq', why='freehold $134 (£40) or eldest son of a freeman')),
           (1824, dict(q='prop', wc=0.45, blk='no', why='1822 act bars Black men; freehold rule kept')),
           (1832, dict(q='prop', wc=0.40, blk='no', why='freehold rule binds harder as towns grow (Dorr-era estimates ~40%)')),
           (1844, dict(q='tax', wc=0.80, blk='eq', poll=1, why='1842 constitution: native men pay $1 registry tax; foreign-born need $134 freehold; no colour bar'))],
    'SC': [(1789, dict(q='prop', wc=0.70, blk='no', why='1790: free white men with 50 acres/town lot or paying 3s tax (legislature chose electors)')),
           (1812, dict(q='univ', wc=UNIV, blk='no', why='1810 amendment: white manhood suffrage (legislature still chose electors)'))],
    'VA': [(1789, dict(q='prop', wc=0.55, blk='no', why='50 acres unimproved / 25 improved + house / town lot; free Black men barred since 1723')),
           (1832, dict(q='prop', wc=0.70, blk='no', why='1830 constitution adds leaseholders and taxpaying householders')),
           (1852, dict(q='univ', wc=UNIV, blk='no', why='1851 constitution: white manhood suffrage'))],
    'VT': [(1792, dict(q='univ', wc=UNIV, blk='eq', why='1777/1793: men of "quiet and peaceable behaviour", one year resident'))],
    'KY': [(1792, dict(q='univ', wc=UNIV, blk='eq', why='1792 constitution: free male citizens, no colour bar')),
           (1800, dict(q='univ', wc=UNIV, blk='no', why='1799 constitution: free white men'))],
    'TN': [(1796, dict(q='univ', wc=0.93, blk='eq', why='1796: freeholders or 6-month inhabitants; no colour bar')),
           (1836, dict(q='univ', wc=UNIV, blk='no', why='1834 constitution: free white men'))],
    'OH': [(1804, dict(q='tax', wc=0.90, blk='no', why='1803: white male taxpayers or road workers')),
           (1852, dict(q='univ', wc=UNIV, blk='no', why='1851 constitution: white manhood suffrage'))],
    'LA': [(1812, dict(q='tax', wc=0.70, blk='no', why='1812: white male citizens who bought federal land or paid a state tax')),
           (1848, dict(q='univ', wc=UNIV, blk='no', why='1845 constitution drops taxpaying (2-year residence)'))],
    'IN': [(1816, dict(q='univ', wc=UNIV, blk='no', why='1816: white male citizens')),
           (1852, dict(q='univ', wc=UNIV, blk='no', alien=1, why='1851 constitution: declarant aliens with 1 year residence vote'))],
    'MS': [(1820, dict(q='tax', wc=TAXQ, blk='no', why='1817: white male citizens who paid tax or did militia duty')),
           (1836, dict(q='univ', wc=UNIV, blk='no', why='1832 constitution: white manhood suffrage'))],
    'IL': [(1820, dict(q='univ', wc=UNIV, blk='no', alien=1, why='1818: all white male inhabitants (aliens vote)')),
           (1852, dict(q='univ', wc=UNIV, blk='no', why='1848 constitution: citizens only (aliens resident at adoption grandfathered)'))],
    'AL': [(1820, dict(q='univ', wc=UNIV, blk='no', why='1819: white male citizens'))],
    'ME': [(1820, dict(q='univ', wc=UNIV, blk='eq', why='1819: male citizens, no colour bar (paupers, untaxed Indians excluded)'))],
    'MO': [(1820, dict(q='univ', wc=UNIV, blk='no', why='1820: free white male citizens'))],
    'AR': [(1836, dict(q='univ', wc=UNIV, blk='no', why='1836: free white male citizens'))],
    'MI': [(1836, dict(q='univ', wc=UNIV, blk='no', alien=1, why='1835: white male citizens and white male inhabitants resident at adoption; 1850: declarant aliens'))],
    'FL': [(1848, dict(q='univ', wc=UNIV, blk='no', why='1838/1845: free white male citizens'))],
    'TX': [(1848, dict(q='univ', wc=UNIV, blk='no', why='1845: free male citizens (Africans and untaxed Indians excluded)'))],
    'IA': [(1848, dict(q='univ', wc=UNIV, blk='no', why='1846: white male citizens'))],
    'WI': [(1848, dict(q='univ', wc=UNIV, blk='no', alien=1, why='1848: white male citizens and declarant aliens'))],
    'CA': [(1852, dict(q='univ', wc=UNIV, blk='no', why='1849: white male citizens (incl. Mexican citizens electing US citizenship)'))],
    'MN': [(1860, dict(q='univ', wc=UNIV, blk='no', alien=1, why='1857: white male citizens, declarant aliens, mixed-blood "civilized" men'))],
    'OR': [(1860, dict(q='univ', wc=UNIV, blk='no', alien=1, why='1857: white male citizens and declarant aliens of one year'))],
    'KS': [(1864, dict(q='univ', wc=UNIV, blk='no', alien=1, why='1859 Wyandotte constitution: white male citizens and declarant aliens'))],
    'WV': [(1864, dict(q='univ', wc=UNIV, blk='no', why='1863: white male citizens'))],
    'NV': [(1864, dict(q='univ', wc=UNIV, blk='no', why='1864: white male citizens'))],
}
# Share of free Black men meeting the rule when admitted on equal terms [I]: property and tax
# rules bound much harder on free Black men (Keyssar ch. 3; Litwack, North of Slavery).
BLACK_RATE = {'univ': 0.95, 'tax': 0.6, 'prop': 0.25}
NY250 = 0.08   # [I] NY: ~1,000 of ~13,000 Black men qualified by 1855 (Field 1982; Keyssar ch. 3)
NJ_WOMEN = 0.10  # [I] share of NJ adult women who were unmarried/widowed AND worth £50
FELONY = 0.0005  # [I] "infamous crimes" exclusions; state-prison populations were tiny before 1865


def franchise() -> pd.DataFrame:
    from build_population_republic import free_share
    ret = pd.read_csv(CACHE / 'labels/state_pres_1789_1864.csv')
    out = []
    for _, r in ret.iterrows():
        y, st = int(r.year), r.state
        rules = [x for x in F.get(st, []) if x[0] <= y]
        if not rules:
            raise SystemExit(f'no franchise rule for {st} {y}')
        rule = rules[-1][1]
        fs = free_share(y).get(st)
        if fs is None:  # state not in the census at or before y (e.g. KY 1792): use the next census
            fs = free_share(y + 10).get(st, 1.0)
        allowed = {'no': 0.0, 'ny250': NY250}.get(rule['blk'], min(BLACK_RATE[rule['q']], rule['wc']))
        notes = [rule['why'], f'qualification={rule["q"]}', f'white_can [I] = {rule["wc"]}',
                 f'black_can [I] = free share of Black men {fs:.3f} × allowed {allowed:.2f} (rule {rule["blk"]}; applies to Black men)']
        if rule.get('women'):
            notes.append(f'women_vote: propertied unmarried women and widows only, ≈{NJ_WOMEN} of adult women [I]')
        if rule.get('alien'):
            notes.append('alien_voting: non-citizen residents/declarant aliens could vote')
        out.append({'year': y, 'state': st, 'poll_tax': int(rule['q'] == 'tax' or bool(rule.get('poll'))),
                    'literacy_test': rule.get('lit', 0), 'alien_voting': rule.get('alien', 0),
                    'women_vote': rule.get('women', 0), 'white_can': rule['wc'], 'black_can': round(fs * allowed, 4),
                    'felony_disenfranchised_share': FELONY, 'voting_age': 21, 'chosen_by': r.chosen_by,
                    'source': 'Keyssar, The Right to Vote (2009) Tables A.1-A.4, A.12 (rules hand-coded from memory of the tables, '
                              'not re-checked page by page); Engerman & Sokoloff (2005); free share from NHGIS adults_<census> (G)',
                    'note': '; '.join(notes) + ('; poll_tax=1 means a taxpaying qualification (any tax, or militia/road-work alternative)'
                                                if rule['q'] == 'tax' else '')})
    return pd.DataFrame(out)


COLS = ['year', 'state', 'rep', 'dem', 'other', 'total', 'third', 'ev_rep', 'ev_dem', 'ev_other', 'ev_total',
        'chosen_by', 'source', 'note']


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('returns', 'all'):
        df = returns()[COLS]
        out = CACHE / 'labels/state_pres_1789_1864.csv'
        df.to_csv(out, index=False)
        print('wrote', out, len(df))
    if what in ('franchise', 'all'):
        df = franchise()
        out = CACHE / 'franchise/state_franchise_1789_1864.csv'
        df.to_csv(out, index=False)
        print('wrote', out, len(df))
