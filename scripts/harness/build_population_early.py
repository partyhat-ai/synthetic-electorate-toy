"""NHGIS 1870-1910 -> population/adults_<year>_by_state_nhgis.csv (long format,
the columns of adults_1920_by_state.csv). Plugged into build_population.py's
__main__ via BUILDERS:

    cd scripts/harness && python build_population.py 1880
    python build_population_early.py --check-1910   # men vs the hand-keyed 1910 table

What the censuses give (codebooks in the extract):
  1870 sPHX NT45-48: men 21+ total, by nativity, by race (separate margins), male
       citizens 21+. sRN NT4: race x nativity, no sex.
  1880 sPHX NT1 race x nativity x sex; NT7 men 21+ native white / FB white / colored.
  1890 cPHAM NT5/NT6/NT9 sex tables; NT14 men 21+ native white / FB white / colored.
       (No citizenship table was requested for 1890.)
  1900 cPHAM NT4/NT6/NT7/NT62 sex tables; NT9 men 21+; NT10 native men 21+ by race;
       NT11 FB men 21+ (all races) by citizenship.
  1910 cPHA NT8/NT10/NT11 sex & white nativity; NT12/NT13 men of voting age by
       race/nativity; NT17 FB white men of voting age by citizenship.
Women 21+ were not tabulated before 1920: every women's row is an [I] estimate.
Territories whose name (minus " Territory") is in geo.STATE_NAME are kept and say so
in `note`; Dakota/Indian/Alaska/Hawaii Territory and "Persons in the Military" drop.
"""
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_population import COLS, SRC, rows  # noqa: E402
from simharness.geo import CODE_OF  # noqa: E402

TAB = 'tabulated'
GROUPS = ['native_white', 'native_white_native_parentage', 'native_white_foreign_or_mixed_parentage',
          'foreign_white_naturalized', 'foreign_white_first_papers', 'foreign_white_alien', 'foreign_white_unknown',
          'negro', 'other_races']
CZ = ['foreign_white_naturalized', 'foreign_white_first_papers', 'foreign_white_alien', 'foreign_white_unknown']
# Alaska and Hawaii (statehood 1959) are territories in every census here: drop them
# even though geo.STATE_NAME lists them for the modern elections.
NOT_YET = {'AK', 'HI'}


def _read(ds: str) -> pd.DataFrame:
    """Like build_population.read, but keeps territories that later became a
    STATE_NAME state (e.g. 'Arizona Territory' -> AZ) and records that they were."""
    f = next(SRC.glob(f'nhgis0001_{ds}_*_state.csv'))
    d = pd.read_csv(f, encoding='latin-1', skiprows=[1])
    code = {k.casefold(): v for k, v in CODE_OF.items()}
    base = d.STATE.str.replace(r'\s+Territory$', '', regex=True).str.casefold()
    keep = base.isin(code) & ~base.map(code).isin(NOT_YET)
    d = d[keep].copy()
    d['state'] = base[keep].map(code)
    d['terr'] = d.STATE.str.endswith('Territory')
    assert d.state.is_unique, f'{ds}: duplicate state codes'
    return d.set_index('state')


def _emit(year, d, spec, table, note=TAB):
    out = rows(year, d, spec, table, note)
    for r in out:
        if d.at[r['state'], 'terr']:
            r['note'] = (r['note'] + '; ' if r['note'] else '') + f'territory in {year}, not yet a state'
    return out


def _gap(a, b, what, tol=1):
    g = (a - b).abs().max()
    assert g < tol, f'{what}: differ by {g}'


# ---------------------------------------------------------------- 1870
@lru_cache
def _men_1870():
    d, rn = _read('ds19'), _read('ds21')
    # Independent checks: nativity and race margins both add to the total.
    _gap(d.AMS001 + d.AMS002, d.AMR001, '1870 NT46 vs NT45')
    _gap(d[['AMT001', 'AMT002', 'AMT003', 'AMT004']].sum(axis=1), d.AMR001, '1870 NT47 vs NT45')
    # Race x nativity of men 21+: IPF of the total-population race x nativity cross
    # (sRN NT4) to the men-21+ race and nativity margins [I].
    races = [('W', 'AMT001', 'AN8001', 'AN8002'), ('C', 'AMT002', 'AN8003', 'AN8004'),
             ('I', 'AMT004', 'AN8005', 'AN8006'), ('Z', 'AMT003', 'AN8007', 'AN8008')]
    out = {}
    for st in d.index:
        seed = {r: [float(rn.at[st, n]) + 1e-6, float(rn.at[st, f]) + 1e-6] for r, _, n, f in races}
        rm = {r: float(d.at[st, c]) for r, c, _, _ in races}
        cm = [float(d.at[st, 'AMS001']), float(d.at[st, 'AMS002'])]
        x = {r: v[:] for r, v in seed.items()}
        for _ in range(200):
            for r in x:
                s = sum(x[r])
                x[r] = [v * rm[r] / s for v in x[r]] if s else [0.0, 0.0]
            for j in (0, 1):
                s = sum(x[r][j] for r in x)
                for r in x:
                    x[r][j] = x[r][j] * cm[j] / s if s else 0.0
        out[st] = x
    m = pd.DataFrame({st: {'nw': x['W'][0], 'fw': x['W'][1], 'negro': sum(x['C']), 'other': sum(x['I']) + sum(x['Z']),
                           'nb': float(d.at[st, 'AMS001']), 'cit': float(d.at[st, 'AMU001'])} for st, x in out.items()}).T
    # Naturalized = male citizens 21+ - native-born men 21+, clipped to [0, FB white] [I].
    m['nat_raw'] = m.cit - m.nb
    m['nat'] = m.nat_raw.clip(lower=0).clip(upper=m.fw)
    m['alien'] = m.fw - m.nat
    m['terr'] = d.terr
    return m


def _split_1870():
    m = _men_1870()
    s = pd.DataFrame({'foreign_white_naturalized': m.nat / m.fw, 'foreign_white_alien': m.alien / m.fw,
                      'foreign_white_first_papers': 0.0, 'foreign_white_unknown': 0.0}).fillna(0)
    return s[CZ]


def year_1870(year=1870):
    m = _men_1870()
    fm = _fm_1880()  # 1870 has no table by sex at all
    out = []
    lbl = {'nw': 'White: Native-born', 'negro': 'Colored: Native and foreign-born',
           'other': 'Indian and Chinese: Native and foreign-born'}
    grp = {'nw': 'native_white', 'negro': 'negro', 'other': 'other_races'}
    ipf = '[I] men 21+ race x nativity: NT47 race and NT46 nativity margins raked (IPF) on the sRN NT4 total-population cross'
    t = 'NHGIS 1870_sPHX NT45-NT47 (+1870_sRN NT4 seed)'
    for k in ('nw', 'negro', 'other'):
        out += _emit(year, m, [(k, 'M', grp[k], lbl[k])], t, ipf)
        w = m[[k, 'terr']].copy()
        w[k] = m[k] * fm[grp[k]].reindex(m.index)
        out += _emit(year, w, [(k, 'F', grp[k], lbl[k])], t + '; 1880_sPHX NT1',
                     '[I] women 21+ = men 21+ x the 1880 whole-population F/M ratio of the same state and group '
                     '(1870 has no table by sex)')
    tc = 'NHGIS 1870_sPHX NT46-NT48'
    cz_note = ('[I] FB white men 21+ (IPF) split: naturalized = NT48 male citizens 21+ - NT46 native-born men 21+, '
               'clipped to [0, FB white]; alien = the rest')
    for sex in ('M', 'F'):
        w = m[['nat', 'alien', 'terr']].copy()
        n = cz_note
        if sex == 'F':
            fr = fm['foreign_white'].reindex(m.index)
            w['nat'], w['alien'] = w.nat * fr, w.alien * fr
            n = cz_note + '; women = men x 1880 FB white F/M, men\'s citizenship split (wife followed husband before 1922)'
            tc2 = tc + '; 1880_sPHX NT1'
        else:
            tc2 = tc
        out += _emit(year, w, [('nat', sex, 'foreign_white_naturalized', 'White: Foreign-born, naturalized'),
                               ('alien', sex, 'foreign_white_alien', 'White: Foreign-born, alien')], tc2, n)
    return pd.DataFrame(out, columns=COLS)


# ---------------------------------------------------------------- 1880
A_CHINESE = 0.95  # [I] share of Chinese/Japanese males who were 21+ (an almost all-adult male labour migration)


@lru_cache
def _fm_1880():
    d = _read('ds25')
    p = lambda cols: d[cols].sum(axis=1)  # noqa: E731
    return pd.DataFrame({
        'native_white': d.AR0002 / d.AR0001,
        'foreign_white': d.AR0004 / d.AR0003,
        'negro': p(['AR0006', 'AR0008']) / p(['AR0005', 'AR0007']),
        'other_races': p(['AR0010', 'AR0012', 'AR0014', 'AR0016']) / p(['AR0009', 'AR0011', 'AR0013', 'AR0015']),
    }).fillna(1.0)


@lru_cache
def _men_1880():
    d = _read('ds25')
    neg = d.AR0005 + d.AR0007
    chi = d.AR0009 + d.AR0011
    ind = d.AR0013 + d.AR0015
    # NT7 "Colored" men 21+ includes Chinese and Indians (CA: 66,809 colored men 21+
    # vs 3,467 Negro males of all ages). Split it by males weighted by adult share:
    # Negro and Indian at the national colored-men-21+/Negro-males ratio of states
    # where they're >99% of colored males, Chinese/Japanese at A_CHINESE [I].
    pure = (chi + ind) < 0.01 * (neg + chi + ind)
    a_n = d.ASU003[pure].sum() / neg[pure].sum()
    wn, wc, wi = neg * a_n, chi * A_CHINESE, ind * a_n
    tot = (wn + wc + wi).replace(0, 1)
    m = pd.DataFrame({'nw': d.ASU001.astype(float), 'fw': d.ASU002.astype(float),
                      'negro': d.ASU003 * wn / tot, 'other': d.ASU003 * (wc + wi) / tot, 'terr': d.terr})
    # Independent check: men 21+ can't exceed males of all ages in any group.
    assert (m.nw <= d.AR0001).all() and (m.fw <= d.AR0003).all() and (d.ASU003 <= neg + chi + ind).all()
    m.attrs['a_n'] = a_n
    return m


def _interp_split(year):
    """Citizenship shares of FB white men 21+ for a census with none: linear in
    time between the 1870 derivation and the 1900 tabulation (1890's citizenship
    table wasn't in the extract), 1900 alone where the unit wasn't in 1870 [I]."""
    s70, s00 = _split_1870(), _split_1900()
    w = (year - 1870) / 30
    s = s70.reindex(s00.index) * (1 - w) + s00 * w
    return s.fillna(s00)


def _fw_rows(year, fw_m, fw_f, split, terr, table, note_m, note_f):
    out = []
    lbl = {'foreign_white_naturalized': 'White: Foreign-born, naturalized',
           'foreign_white_first_papers': 'White: Foreign-born, first papers',
           'foreign_white_alien': 'White: Foreign-born, alien',
           'foreign_white_unknown': 'White: Foreign-born, citizenship unknown'}
    for sex, tot, note in (('M', fw_m, note_m), ('F', fw_f, note_f)):
        w = pd.DataFrame({g: tot * split[g].reindex(tot.index) for g in CZ})
        w['terr'] = terr
        out += _emit(year, w, [(g, sex, g, lbl[g]) for g in CZ], table, note)
    return out


def year_1880(year=1880):
    m, fm = _men_1880(), _fm_1880()
    t = 'NHGIS 1880_sPHX NT7'
    tf = 'NHGIS 1880_sPHX NT7 x NT1'
    fnote = '[I] women 21+ = men 21+ x the whole-population F/M ratio of the same state and group (NT1)'
    out = _emit(year, m, [('nw', 'M', 'native_white', 'White: Native-born')], t)
    split = (f'[I] NT7 colored men 21+ split Negro vs Chinese/Indian by NT1 males weighted by adult share '
             f'(Negro & Indian {m.attrs["a_n"]:.3f}, Chinese/Japanese {A_CHINESE})')
    out += _emit(year, m, [('negro', 'M', 'negro', 'Colored: Negro'),
                           ('other', 'M', 'other_races', 'Colored: Chinese, Japanese and Indian')], t + '; NT1', split)
    w = pd.DataFrame({'nw': m.nw * fm.native_white, 'negro': m.negro * fm.negro, 'other': m.other * fm.other_races,
                      'terr': m.terr})
    out += _emit(year, w, [('nw', 'F', 'native_white', 'White: Native-born')], tf, fnote)
    out += _emit(year, w, [('negro', 'F', 'negro', 'Colored: Negro'),
                           ('other', 'F', 'other_races', 'Colored: Chinese, Japanese and Indian')], tf, fnote + '; ' + split)
    cz = '[I] NT7 FB white men 21+ x citizenship shares interpolated 1870 (derived) -> 1900 (tabulated) at 1880'
    out += _fw_rows(year, m.fw, m.fw * fm.foreign_white, _interp_split(year), m.terr, t + '; 1870_sPHX NT48; 1900_cPHAM NT11',
                    cz, cz + '; women = men x NT1 FB white F/M, men\'s split (wife followed husband before 1922)')
    return pd.DataFrame(out, columns=COLS)


# ---------------------------------------------------------------- 1900
@lru_cache
def _men_1900():
    d = _read('ds31')
    nat = d[[f'AYN00{i}' for i in range(1, 7)]].sum(axis=1)
    fb = d[[f'AYO00{i}' for i in range(1, 9)]].sum(axis=1)
    _gap(nat + fb, d.AZ4001, '1900 NT10+NT11 vs NT9')
    _gap(d.AZF001 + d.AZF003, d.AZ0001, '1900 NT4 vs NT62')
    # NT7's codebook says "Other Colored" for AZ3001/2, but the values are ALL colored
    # (Negro + other): nationally 4.71M vs 4.39M Negro males, and FL 120,518 vs
    # 120,199. Check: colored minus Negro must hold the native "Colored" men 21+ (NT10).
    oth_m, oth_f = d.AZ3001 - d.AZ3003, d.AZ3002 - d.AZ3004
    assert (oth_m >= 0).all() and (oth_m >= d.AYN005 + d.AYN006).all(), '1900 NT7 not colored-total'
    assert (d.AZX001 <= d.AZF003).all()
    fbnw_males = d.AZF003 - d.AZX001          # FB non-white males, all ages (NT4 - NT6)
    fbnw_f = d.AZF004 - d.AZX002
    fbnw = fbnw_males * fb / d.AZF003.replace(0, 1)   # [I] at the FB adult share
    # FB "other" can't exceed other-colored males less native other men 21+; the rest is FB Negro [I].
    fb_oth = pd.concat([fbnw, (oth_m - d.AYN005 - d.AYN006).clip(lower=0) * fb / d.AZF003.replace(0, 1)],
                       axis=1).min(axis=1)
    fb_neg = fbnw - fb_oth
    cz = pd.DataFrame({'foreign_white_naturalized': d.AYO001 + d.AYO002, 'foreign_white_first_papers': d.AYO003 + d.AYO004,
                       'foreign_white_alien': d.AYO005 + d.AYO006, 'foreign_white_unknown': d.AYO007 + d.AYO008}).astype(float)
    # FB non-whites (mostly Chinese, barred from naturalizing) come out of alien, then unknown [I].
    take = pd.concat([fbnw, cz.foreign_white_alien], axis=1).min(axis=1)
    cz['foreign_white_alien'] -= take
    cz['foreign_white_unknown'] -= (fbnw - take)
    assert (cz.foreign_white_unknown > -1).all(), '1900: FB non-white exceeds alien + unknown'
    m = pd.DataFrame({'nw': (d.AYN001 + d.AYN002).astype(float), 'negro_nb': (d.AYN003 + d.AYN004).astype(float),
                      'other_nb': (d.AYN005 + d.AYN006).astype(float), 'fb_neg': fb_neg, 'fb_oth': fb_oth,
                      'fw': cz.sum(axis=1), 'terr': d.terr})
    m['negro'] = m.negro_nb + m.fb_neg
    m['other'] = m.other_nb + m.fb_oth
    nw_m = d.AZF001 - (d.AZ3001 - fbnw_males)
    nw_f = d.AZF002 - (d.AZ3002 - fbnw_f)
    fm = pd.DataFrame({'native_white': nw_f / nw_m, 'foreign_white': d.AZX002 / d.AZX001,
                       'negro': d.AZ3004 / d.AZ3003, 'other_races': oth_f / oth_m.replace(0, 1),
                       'white': (nw_f + d.AZX002) / (nw_m + d.AZX001)}).fillna(1.0)
    return m, cz, fm


def _split_1900():
    _, cz, _ = _men_1900()
    return cz.div(cz.sum(axis=1).replace(0, 1), axis=0)


def year_1900(year=1900):
    m, cz, fm = _men_1900()
    t = 'NHGIS 1900_cPHAM NT10'
    out = _emit(year, m, [('nw', 'M', 'native_white', 'White: Native-born')], t)
    fbn = ('[I] native-born (NT10, tabulated) + FB non-white men 21+ = (NT4 FB males - NT6 FB white males) x FB '
           'adult share (NT11/NT4); FB "other" capped at NT7 other-colored males, the rest FB Negro')
    out += _emit(year, m, [('negro', 'M', 'negro', 'Negro'),
                           ('other', 'M', 'other_races', 'Colored: Indian, Chinese, Japanese')], t + '; NT4; NT6; NT7; NT11', fbn)
    fnote = '[I] women 21+ = men 21+ x the whole-population F/M ratio of the same state and group (NT4/NT6/NT7)'
    w = pd.DataFrame({'nw': m.nw * fm.native_white, 'negro': m.negro * fm.negro, 'other': m.other * fm.other_races,
                      'terr': m.terr})
    out += _emit(year, w, [('nw', 'F', 'native_white', 'White: Native-born'), ('negro', 'F', 'negro', 'Negro'),
                           ('other', 'F', 'other_races', 'Colored: Indian, Chinese, Japanese')],
                 'NHGIS 1900_cPHAM NT10 x NT4/NT6/NT7', fnote)
    czn = ('[I] NT11 FB men 21+ by citizenship (all races) less the FB non-white estimate, taken from alien '
           'then unknown')
    out += _fw_rows(year, m.fw, m.fw * fm.foreign_white, _split_1900(), m.terr, 'NHGIS 1900_cPHAM NT11; NT4; NT6', czn,
                    czn + '; women = men x NT6 FB white F/M, men\'s split (wife followed husband before 1922)')
    return pd.DataFrame(out, columns=COLS)


# ---------------------------------------------------------------- 1890
def year_1890(year=1890):
    d = _read('ds27')
    _gap(d.AVP001 + d.AVP003, d.AV3001, '1890 NT5 vs NT9 (male)')
    _gap(d[['AV0001', 'AV0003', 'AV0005', 'AV0007']].sum(axis=1), d.AV3001, '1890 NT6 vs NT9 (male)')
    _gap(d[['AV0002', 'AV0004', 'AV0006', 'AV0008']].sum(axis=1), d.AV3002, '1890 NT6 vs NT9 (female)')
    assert (d.AUP001 <= d.AV0001 + d.AV0003).all() and (d.AUP002 <= d.AV0005).all() and (d.AUP003 <= d.AV0007).all()
    m80, m00 = _men_1880(), _men_1900()[0]
    fm80, fm00 = _fm_1880(), _men_1900()[2]
    # NT14 "Colored" men 21+ (incl. Chinese/Indian, CA 72,061) split by the mean of the
    # 1880 and 1900 Negro shares of colored men 21+ in the state [I].
    sh = pd.concat([(m80.negro / (m80.negro + m80.other)), (m00.negro / (m00.negro + m00.other))], axis=1).mean(axis=1)
    sh = sh.reindex(d.index).fillna(1.0)
    m = pd.DataFrame({'nw': d.AUP001.astype(float), 'fw': d.AUP002.astype(float),
                      'negro': d.AUP003 * sh, 'other': d.AUP003 * (1 - sh), 'terr': d.terr})
    t = 'NHGIS 1890_cPHAM NT14'
    out = _emit(year, m, [('nw', 'M', 'native_white', 'White: Native-born')], t)
    spl = '[I] NT14 colored men 21+ split Negro vs other by the mean of the state\'s 1880 and 1900 Negro shares'
    out += _emit(year, m, [('negro', 'M', 'negro', 'Colored: Negro'),
                           ('other', 'M', 'other_races', 'Colored: Chinese, Japanese and Indian')], t, spl)
    # Women: NT6 F/M for native white; Negro/other F/M = mean of 1880 and 1900, scaled so the
    # implied colored F/M matches 1890's NT6 [I].
    fm_nw = (d.AV0002 + d.AV0004) / (d.AV0001 + d.AV0003)
    fm_fw = d.AV0006 / d.AV0005
    fn = pd.concat([fm80.negro, fm00.negro], axis=1).mean(axis=1).reindex(d.index).fillna(d.AV0008 / d.AV0007)
    fo = pd.concat([fm80.other_races, fm00.other_races], axis=1).mean(axis=1).reindex(d.index).fillna(1.0)
    k = (d.AV0008 / d.AV0007) / ((fn * m.negro + fo * m.other) / d.AUP003.replace(0, 1)).replace(0, 1)
    w = pd.DataFrame({'nw': m.nw * fm_nw, 'negro': m.negro * fn * k, 'other': m.other * fo * k, 'terr': m.terr})
    out += _emit(year, w, [('nw', 'F', 'native_white', 'White: Native-born')], t + ' x NT6',
                 '[I] women 21+ = men 21+ x the whole-population F/M ratio of the same state and group (NT6)')
    out += _emit(year, w, [('negro', 'F', 'negro', 'Colored: Negro'),
                           ('other', 'F', 'other_races', 'Colored: Chinese, Japanese and Indian')], t + ' x NT6',
                 '[I] women 21+ = men 21+ x mean 1880/1900 F/M of the group, scaled to NT6 colored F/M; ' + spl)
    cz = ('[I] NT14 FB white men 21+ x citizenship shares interpolated 1870 (derived) -> 1900 (tabulated) at 1890 '
          '(no 1890 citizenship table in the extract)')
    out += _fw_rows(year, m.fw, m.fw * fm_fw, _interp_split(year), m.terr, t + '; 1870_sPHX NT48; 1900_cPHAM NT11', cz,
                    cz + '; women = men x NT6 FB white F/M, men\'s split (wife followed husband before 1922)')
    return pd.DataFrame(out, columns=COLS)


# ---------------------------------------------------------------- 1910
def year_1910(year=1910):
    d = _read('ds37')
    _gap(d[[f'A3200{i}' for i in range(1, 7)]].sum(axis=1), d.A31001, '1910 NT13 vs NT12')
    _gap(d[[f'A3300{i}' for i in range(1, 5)]].sum(axis=1), d.A32004, '1910 NT17 vs NT13 FB white')
    _gap(d[['A5B001', 'A5B002', 'A5B003', 'A5B004']].sum(axis=1), d.A30001 + d.A30002, '1910 NT8 vs NT11 white')
    oth_m, oth_f = d.A3Z001 - d.A30001 - d.A30003, d.A3Z002 - d.A30002 - d.A30004
    assert (oth_m > -1).all() and (oth_f > -1).all()
    assert (d.A32005 <= d.A30003).all() and (d.A32001 + d.A32002 + d.A32003 + d.A32004 <= d.A30001).all()
    t = 'NHGIS 1910_cPHA NT13'
    m = d.copy()
    m['nwf'] = (d.A32002 + d.A32003).astype(float)
    out = []
    out += _emit(year, m, [('A32001', 'M', 'native_white_native_parentage', 'Native-Born White: Native parentage'),
                           ('nwf', 'M', 'native_white_foreign_or_mixed_parentage', 'Native-Born White: Foreign or mixed parentage'),
                           ('A32005', 'M', 'negro', 'Negro'),
                           ('A32006', 'M', 'other_races', 'Indian, Chinese, Japanese and all other races')], t)
    lbl = [('A33001', 'foreign_white_naturalized', 'Foreign-born white: Naturalized'),
           ('A33002', 'foreign_white_first_papers', 'Foreign-born white: With first papers'),
           ('A33003', 'foreign_white_alien', 'Foreign-born white: Alien'),
           ('A33004', 'foreign_white_unknown', 'Foreign-born white: Unknown citizenship status')]
    out += _emit(year, m, [(c, 'M', g, lab) for c, g, lab in lbl], 'NHGIS 1910_cPHA NT17')
    # Women: NT11 gives white/Negro by sex, other = NT10 - NT11. White nativity isn't by sex
    # in 1910: native and FB white F/M = the state's 1900 ratios x (1910 white F/M / 1900 white F/M) [I].
    fm00 = _men_1900()[2].reindex(d.index)
    r_w = d.A30002 / d.A30001
    k = r_w / fm00.white
    r_nw = (fm00.native_white * k).fillna(r_w)
    r_fw = (fm00.foreign_white * k).fillna(r_w)
    w = pd.DataFrame({'np': d.A32001 * r_nw, 'nwf': m.nwf * r_nw, 'neg': d.A32005 * d.A30004 / d.A30003,
                      'oth': d.A32006 * (oth_f / oth_m.replace(0, 1)), 'terr': d.terr})
    for c in ('A33001', 'A33002', 'A33003', 'A33004'):
        w[c] = d[c] * r_fw
    fnote = '[I] women 21+ = men 21+ x the whole-population F/M ratio of the same state and group (NT10/NT11)'
    wnote = ('[I] women 21+ = men 21+ x white F/M by nativity: the state\'s 1900 native/FB white F/M scaled by '
             '1910/1900 white F/M (NT11; 1910 white nativity not by sex)')
    out += _emit(year, w, [('np', 'F', 'native_white_native_parentage', 'Native-Born White: Native parentage'),
                           ('nwf', 'F', 'native_white_foreign_or_mixed_parentage', 'Native-Born White: Foreign or mixed parentage')],
                 t + ' x NT11; 1900_cPHAM NT4/NT6/NT7', wnote)
    out += _emit(year, w, [('neg', 'F', 'negro', 'Negro'), ('oth', 'F', 'other_races', 'Indian, Chinese, Japanese and all other races')],
                 t + ' x NT10/NT11', fnote)
    out += _emit(year, w, [(c, 'F', g, lab) for c, g, lab in lbl], 'NHGIS 1910_cPHA NT17 x NT11; 1900_cPHAM NT4/NT6/NT7',
                 wnote + '; men\'s citizenship split (wife followed husband before 1922)')
    return pd.DataFrame(out, columns=COLS)


BUILDERS = {1870: year_1870, 1880: year_1880, 1890: year_1890, 1900: year_1900, 1910: year_1910}


def check_1910(nh: pd.DataFrame):
    from simharness.config import CACHE
    from simharness.data import GROUP_MAP
    hand = pd.read_csv(CACHE / 'population/adults_1910_by_state.csv')
    hand = hand[hand.group != 'TOTAL']
    agg = lambda x: x.assign(g=x.group.map(lambda g: GROUP_MAP.get(g, g))).groupby(['state', 'sex', 'g'])['count'].sum()  # noqa: E731
    for sex in ('M', 'F'):
        a, b = agg(hand[hand.sex == sex]), agg(nh[nh.sex == sex])
        j = pd.concat([a.rename('hand'), b.rename('nhgis')], axis=1)
        miss = j[j.isna().any(axis=1)]
        j = j.fillna(0)
        j['diff'] = j.nhgis - j.hand
        j['rel'] = j['diff'] / j.hand.clip(lower=1)
        bad = j[(j['diff'].abs() > 50) & (j.rel.abs() > 0.005)]
        print(f'{sex}: cells {len(j)} ({len(miss)} on one side only); total hand {j.hand.sum():,.0f} vs nhgis '
              f'{j.nhgis.sum():,.0f}; exact {(j["diff"].abs() < 0.5).sum()}; off by >50 and >0.5%: {len(bad)}')
        if len(miss):
            print('  one side only:', sorted(set(s for s, _, _ in miss.index)))
        if len(bad):
            print(bad.sort_values('diff', key=abs, ascending=False).head(15).to_string())


if __name__ == '__main__':
    if '--check-1910' in sys.argv:
        check_1910(year_1910())
    else:
        for y, f in BUILDERS.items():
            df = f(y)
            assert set(df.group) <= set(GROUPS), set(df.group) - set(GROUPS)
            print(y, len(df), df.state.nunique(), f'{df["count"].sum():,.0f}',
                  f'women {df[df.sex == "F"]["count"].sum() / df["count"].sum():.3f}')
