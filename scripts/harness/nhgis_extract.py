"""Submit, wait for and download the NHGIS state-level population extract
behind every census year from 1870 to 1970 (and 1920 again, as a check on the
harness's own 1920 table).

    python3 scripts/harness/nhgis_extract.py submit     # prints the extract number
    python3 scripts/harness/nhgis_extract.py wait N     # polls, then downloads into the cache
    python3 scripts/harness/nhgis_extract.py status N

The key is read from ~/.config/simulacra/nhgis.env (IPUMS_API_KEY=…) and is
never printed. Data lands in $SIMHARNESS_CACHE/population/nhgis/: NHGIS terms
forbid redistributing the extract, so it stays out of the repo (cite
doi:10.18128/D050.V19.0 / the NHGIS citation page).
"""
import io
import json
import os
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

API = 'https://api.ipums.org'
CACHE = Path(os.environ.get('SIMHARNESS_CACHE', str(Path.home() / 'research_notes/historical_election_sim_data/harness_cache')))
OUT = CACHE / 'population/nhgis'

# Per census: adults 21+ (men only before 1920: women weren't tabulated by
# voting age) by race / nativity, citizenship of the foreign born, and the
# population by sex × race / nativity to estimate women 21+ where needed.
TABLES = {
    '1870_sPHX': ['NT1', 'NT45', 'NT46', 'NT47', 'NT48'],   # males 21+ by nativity, by race; male citizens 21+
    '1870_sRN': ['NT1', 'NT4'],                             # race by nativity
    '1880_sPHX': ['NT1', 'NT7'],                            # race/nativity by sex; males 21+ by race/nativity
    '1890_cPHAM': ['NT5', 'NT6', 'NT9', 'NT14'],            # nativity by sex, race/nativity by sex; males 21+ by race/nativity
    '1900_cPHAM': ['NT4', 'NT6', 'NT7', 'NT9', 'NT10', 'NT11', 'NT62'],  # + native males 21+ by race; FB males 21+ by citizenship
    '1910_cPHA': ['NT8', 'NT10', 'NT11', 'NT12', 'NT13', 'NT17'],         # males of voting age by race/nativity; FB white by citizenship
    '1920_cPHAM': ['NT12', 'NT13', 'NT15'],                 # check against harness_cache/population/adults_1920_by_state.csv
    '1930_cPAE': ['NT9', 'NT10', 'NT12'],                   # 21+ by race/nativity by sex; FB white 21+ by sex by citizenship
    '1930_cAge30': ['NT7', 'NT10'],
    '1940_cPHAE': ['NT8', 'NT9', 'NT10', 'NT12'],
    '1940_cAge': ['NT7', 'NT10'],                           # 21+ by race by sex; white 21+ by nativity by sex
    '1950_cPHA': ['NT8', 'NT9A', 'NT9B', 'NT48'],
    '1950_cAge': ['NT6', 'NT18'],                           # race by sex by age
    '1960_cAge1': ['NT5', 'NT11'],                          # sex by age; race by sex by age
    '1960_cPop': ['NT14'],
    '1970_Cnt1': ['NT18', 'NT19'],                          # sex by age; race by sex by age (non-white)
}


def key() -> str:
    for line in (Path.home() / '.config/simulacra/nhgis.env').read_text().splitlines():
        if line.startswith('IPUMS_API_KEY='):
            return line.split('=', 1)[1].strip()
    raise SystemExit('no IPUMS_API_KEY in ~/.config/simulacra/nhgis.env')


def call(path, body=None, raw=False):
    req = urllib.request.Request(path if path.startswith('http') else API + path, headers={'Authorization': key(), 'Content-Type': 'application/json'},
                                 data=json.dumps(body).encode() if body is not None else None, method='POST' if body is not None else 'GET')
    try:
        with urllib.request.urlopen(req) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f'HTTP {e.code}: {e.read().decode()[:800]}')
    return data if raw else json.loads(data)


def submit() -> int:
    body = {'datasets': {ds: {'dataTables': t, 'geogLevels': ['state']} for ds, t in TABLES.items()},
            'dataFormat': 'csv_header', 'breakdownAndDataTypeLayout': 'single_file',
            'description': 'Simulacra harness: state adults 21+ by sex x race/nativity x citizenship, 1870-1970'}
    r = call('/extracts?collection=nhgis&version=2', body)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'extract_request.json').write_text(json.dumps({'number': r['number'], 'request': body}, indent=1))
    return r['number']


def status(n: int) -> dict:
    return call(f'/extracts/{n}?collection=nhgis&version=2')


def download(n: int, st: dict):
    url = st['downloadLinks']['tableData']['url']
    data = call(url, raw=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        z.extractall(OUT / f'extract_{n}')
    (OUT / 'PROVENANCE-nhgis.md').write_text(
        f'# NHGIS extract {n}\n\nRequested and downloaded {time.strftime("%Y-%m-%d %H:%M")} via the IPUMS API v2 '
        f'(scripts/harness/nhgis_extract.py). Tables: see extract_request.json. Files: {len(names)}.\n\n'
        'Citation: Manson, S., Schroeder, J., Van Riper, D., Knowles, K., Kugler, T., Roberts, F., and Ruggles, S. '
        'IPUMS National Historical Geographic Information System, https://www.nhgis.org (see nhgis.org/citation for the '
        'current version DOI).\n\nTerms: not for redistribution; stays in the harness cache, outside the repo.\n')
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
