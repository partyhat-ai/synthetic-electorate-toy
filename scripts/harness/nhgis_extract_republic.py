"""Submit, wait for and download the NHGIS state-level extract behind the
1790–1860 censuses (early-republic population: sex × race × free/enslaved ×
age bands, plus nativity for 1850 and 1860).

    python3 scripts/harness/nhgis_extract_republic.py submit     # prints the extract number
    python3 scripts/harness/nhgis_extract_republic.py wait N     # polls, then downloads into the cache
    python3 scripts/harness/nhgis_extract_republic.py status N

Reuses the API client of nhgis_extract.py (key from ~/.config/simulacra/nhgis.env,
never printed). Data lands in $SIMHARNESS_CACHE/population/nhgis/extract_<N>/ and
stays out of the repo (NHGIS terms).
"""
import io
import json
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nhgis_extract import OUT, call  # noqa: E402

TABLES = {
    '1790_cPop': ['NT1', 'NT4', 'NT5', 'NT6'],          # white males 16+/<16, white females; race/slave status
    '1800_cPop': ['NT1', 'NT5', 'NT6', 'NT9'],          # free white by sex × age; nonwhite by slave status
    '1810_cPop': ['NT1', 'NT5', 'NT6', 'NT9'],
    '1820_cPop': ['NT1', 'NT4A', 'NT4B', 'NT5', 'NT7', 'NT8', 'NT10'],  # + colored by slave status × sex × age; aliens
    '1830_cPop': ['NT1', 'NT4', 'NT5', 'NT9', 'NT12'],  # + foreigners not naturalized
    '1840_cPopX': ['NT1', 'NT4', 'NT5', 'NT25'],
    '1850_cPAX': ['NT1', 'NT4', 'NT5', 'NT40'],         # race/slave × sex × age; nativity
    '1850_sPAX': ['NT1', 'NT5', 'NT7'],                 # native / foreign / unknown birthplace × race × sex
    '1860_cPAX': ['NT1', 'NT4', 'NT5', 'NT7'],          # race/slave × age × sex; nativity × race × sex
}


def submit() -> int:
    body = {'datasets': {ds: {'dataTables': t, 'geogLevels': ['state']} for ds, t in TABLES.items()},
            'dataFormat': 'csv_header', 'breakdownAndDataTypeLayout': 'single_file',
            'description': 'Simulacra harness (agent G): state population by sex x race x free/slave x age, 1790-1860'}
    r = call('/extracts?collection=nhgis&version=2', body)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'extract_request_republic_{r["number"]}.json').write_text(json.dumps({'number': r['number'], 'request': body}, indent=1))
    return r['number']


def status(n: int) -> dict:
    return call(f'/extracts/{n}?collection=nhgis&version=2')


def download(n: int, st: dict):
    data = call(st['downloadLinks']['tableData']['url'], raw=True)
    d = OUT / f'extract_{n}'
    d.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        z.extractall(d)
    (d / 'PROVENANCE.md').write_text(
        f'# NHGIS extract {n} (1790–1860 state tables)\n\nDownloaded {time.strftime("%Y-%m-%d %H:%M")} via the IPUMS API v2 '
        f'(scripts/harness/nhgis_extract_republic.py). Tables: {json.dumps(TABLES)}. Files: {len(names)}.\n\n'
        'Citation: IPUMS NHGIS, https://www.nhgis.org (see nhgis.org/citation). Not for redistribution.\n')
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
