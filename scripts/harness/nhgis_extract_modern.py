"""Submit, wait for and download the NHGIS state-level extract behind the
1980-2024 adult (18+) population tables: nativity x citizenship x sex x race
(white non-Hispanic, Black) from the decennial sample files and the ACS
B05003 family, plus 100%-count / PL 94-171 18+ totals as independent checks.

    python3 scripts/harness/nhgis_extract_modern.py submit     # prints the extract number
    python3 scripts/harness/nhgis_extract_modern.py wait N     # polls, then downloads into the cache
    python3 scripts/harness/nhgis_extract_modern.py status N

Key handling and terms as in nhgis_extract.py (key never printed; data stays in
$SIMHARNESS_CACHE/population/nhgis/extract_<N>/, not redistributable).
"""
import io
import json
import sys
import time
import zipfile

from nhgis_extract import OUT, call

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


def body():
    ds = {}
    for name, (tables, bd) in DATASETS.items():
        ds[name] = {'dataTables': tables, 'geogLevels': ['state']}
        if bd:
            ds[name]['breakdownValues'] = bd
    return {'datasets': ds, 'dataFormat': 'csv_header', 'breakdownAndDataTypeLayout': 'single_file',
            'description': 'Simulacra harness: state 18+ by sex x race x nativity x citizenship, 1980-2024'}


def submit() -> int:
    b = body()
    r = call('/extracts?collection=nhgis&version=2', b)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'extract_request_{r["number"]}_modern.json').write_text(json.dumps({'number': r['number'], 'request': b}, indent=1))
    return r['number']


def status(n: int) -> dict:
    return call(f'/extracts/{n}?collection=nhgis&version=2')


def download(n: int, st: dict):
    data = call(st['downloadLinks']['tableData']['url'], raw=True)
    d = OUT / f'extract_{n}'
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        z.extractall(d)
    (d / 'PROVENANCE.md').write_text(
        f'# NHGIS extract {n} (modern, 1980-2024)\n\nRequested and downloaded {time.strftime("%Y-%m-%d %H:%M")} via the IPUMS API v2 '
        f'(scripts/harness/nhgis_extract_modern.py). Tables: see ../extract_request_{n}_modern.json. Files: {len(names)}.\n\n'
        'Citation: Manson, S., Schroeder, J., Van Riper, D., Knowles, K., Kugler, T., Roberts, F., and Ruggles, S. '
        'IPUMS National Historical Geographic Information System, https://www.nhgis.org.\n\n'
        'Terms: not for redistribution; stays in the harness cache, outside the repo.\n')
    return names


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'submit'
    if cmd == 'submit':
        print('extract', submit())
    elif cmd == 'status':
        st = status(int(sys.argv[2]))
        print(st['status'], st.get('errors'))
    elif cmd == 'wait':
        n = int(sys.argv[2])
        while True:
            st = status(n)
            print(time.strftime('%H:%M:%S'), st['status'], flush=True)
            if st['status'] == 'completed':
                print('files', download(n, st))
                break
            if st['status'] in ('failed', 'canceled'):
                raise SystemExit(f'extract {n} {st["status"]}: {st.get("errors")}')
            time.sleep(30)
