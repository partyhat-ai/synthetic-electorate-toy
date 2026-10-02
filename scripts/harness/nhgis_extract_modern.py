"""Submit, wait for and download the NHGIS state-level extract behind the
1980-2024 adult (18+) population tables: nativity x citizenship x sex x race
(white non-Hispanic, Black) from the decennial sample files and the ACS
B05003 family, plus 100%-count / PL 94-171 18+ totals as independent checks.

    python3 scripts/harness/nhgis_extract_modern.py submit     # prints the extract number
    python3 scripts/harness/nhgis_extract_modern.py wait N     # polls, then downloads into the cache
    python3 scripts/harness/nhgis_extract_modern.py status N

Key handling, cache layout and terms: nhgis_common.py.
"""
from nhgis_common import Extract, request

ACS_TABLES = ['B01001', 'B03002', 'B05003', 'B05003B', 'B05003H']

# dataset -> (tables, breakdown values or None)
DATASETS = {
    # 1980: 100% sex by age (total; white / Black not of Spanish origin); sample nativity x
    # citizenship by race (all ages); Spanish origin by race; sample sex by age (check).
    '1980_STF1': (['NT10B'], None),
    '1980_STF2a': (['NTA13'], None),
    '1980_STF2b': (['NTB8B'], ['bs03.ge0000', 'bs04.ch00', 'bs04.ch24', 'bs04.ch25']),
    '1980_STF3': (['NT15B'], None),
    '1980_STF4Pb': (['NTPB9'], ['bs03.ge0000', 'bs04.ch00', 'bs04.ch01', 'bs04.ch02', 'bs04.ch19']),
    # 1990: 100% sex by age; MARS age x Hispanic x sex x race; sample age x citizenship;
    # sample nativity/citizenship by race (all ages).
    '1990_STF1': (['NP13'], None),
    '1990_MARS': (['NP1'], None),
    '1990_STF3': (['NP37'], None),
    '1990_STF4b': (['NPB20'], ['bs09.ge00', 'bs10.ch000', 'bs10.ch120', 'bs10.ch121']),
    # 2000: SF4 sex x age(18) x nativity and x citizenship, iterated total / WNH / BNH;
    # SF1 18+ total and 18+ NH by race (independent).
    '2000_SF1a': (['NP005A', 'NP006C'], None),
    '2000_SF4': (['NPCT044B', 'NPCT044C'], ['bs21.ge00', 'bs22.ch001', 'bs22.ch451', 'bs22.ch453']),
    # ACS (2008 = 2006-2010 5-year; 2020 = 2016-2020 5-year; 1-year otherwise) + PL 18+ checks.
    '2006_2010_ACS5a': (['B01001', 'B03002'], None),
    '2006_2010_ACS5b': (['B05003', 'B05003B', 'B05003H'], None),
    '2010_ACS1': (ACS_TABLES, None),
    '2010_PL94171': (['NP003', 'NP004'], None),
    '2012_ACS1': (ACS_TABLES, None),
    '2016_ACS1': (ACS_TABLES, None),
    '2016_2020_ACS5a': (['B01001', 'B03002'], None),
    '2016_2020_ACS5b': (['B05003', 'B05003B', 'B05003H'], None),
    '2020_PL94171': (['P3', 'P4'], None),
    '2024_ACS1': (ACS_TABLES, None),
}

EXTRACT = Extract(request(DATASETS, 'Simulacra harness: state 18+ by sex x race x nativity x citizenship, 1980-2024'),
                  'extract_request_{n}_modern.json', 'modern, 1980-2024', 'nhgis_extract_modern.py')

if __name__ == '__main__':
    EXTRACT.cli()
