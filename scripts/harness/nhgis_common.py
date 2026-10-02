"""NHGIS, shared by the harness scripts.

The extract client (IPUMS API v2) behind nhgis_extract*.py: submit an NHGIS
state-level extract, poll it, then download and unzip it into the cache. The key
is read from ~/.config/simulacra/nhgis.env (IPUMS_API_KEY=…) and is never
printed. Everything lands under $SIMHARNESS_CACHE/population/nhgis/: the request
JSON beside the extracts, the files plus PROVENANCE-nhgis.md in extract_<N>/.
NHGIS terms forbid redistributing an extract, so none of it enters the repo.

What the build_population* scripts share: the long output format (the columns
of adults_1920_by_state.csv), state-table loading, gap checks and the comparison
against a hand-keyed census table.

Importing it puts the repo root on sys.path, so `simharness` imports work when a
script is run directly.
"""
import argparse
import io
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from simharness.config import CACHE  # noqa: E402
from simharness.geo import CODE_OF  # noqa: E402

NHGIS_DIR = CACHE / 'population/nhgis'

# ---------------------------------------------------------------- extract client
API = 'https://api.ipums.org'
CITATION = ('Citation: Manson, S., Schroeder, J., Van Riper, D., Knowles, K., Kugler, T., Roberts, F., and Ruggles, S. '
            'IPUMS National Historical Geographic Information System, https://www.nhgis.org (see nhgis.org/citation for '
            'the current version DOI).')
TERMS = 'Terms: not for redistribution; stays in the harness cache, outside the repo.'


def key() -> str:
    for line in (Path.home() / '.config/simulacra/nhgis.env').read_text().splitlines():
        if line.startswith('IPUMS_API_KEY='):
            return line.split('=', 1)[1].strip()
    raise SystemExit('no IPUMS_API_KEY in ~/.config/simulacra/nhgis.env')


def call(path, body=None, raw=False):
    """GET (or POST `body` as JSON) an API path or a full URL; JSON back unless raw."""
    req = urllib.request.Request(path if path.startswith('http') else API + path,
                                 headers={'Authorization': key(), 'Content-Type': 'application/json'},
                                 data=json.dumps(body).encode() if body is not None else None,
                                 method='POST' if body is not None else 'GET')
    try:
        with urllib.request.urlopen(req) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f'HTTP {e.code}: {e.read().decode()[:800]}')
    return data if raw else json.loads(data)


def request(datasets: dict, description: str) -> dict:
    """datasets: {name: [table, ...] or (tables, breakdown values or None)} → an extract request, state level."""
    ds = {}
    for name, spec in datasets.items():
        tables, breakdown = spec if isinstance(spec, tuple) else (spec, None)
        ds[name] = {'dataTables': tables, 'geogLevels': ['state']}
        if breakdown:
            ds[name]['breakdownValues'] = breakdown
    return {'datasets': ds, 'dataFormat': 'csv_header', 'breakdownAndDataTypeLayout': 'single_file',
            'description': description}


def status(n: int) -> dict:
    return call(f'/extracts/{n}?collection=nhgis&version=2')


class Extract:
    """One extract definition. request_name is the request file's name under NHGIS_DIR, with {n} for the
    extract number (build_population_modern.py finds its extract by that name)."""

    def __init__(self, body: dict, request_name: str, title: str, script: str):
        self.body, self.request_name, self.title, self.script = body, request_name, title, script

    def submit(self) -> int:
        r = call('/extracts?collection=nhgis&version=2', self.body)
        n = r['number']
        NHGIS_DIR.mkdir(parents=True, exist_ok=True)
        (NHGIS_DIR / self.request_name.format(n=n)).write_text(json.dumps({'number': n, 'request': self.body}, indent=1))
        return n

    def download(self, n: int, st: dict) -> list:
        data = call(st['downloadLinks']['tableData']['url'], raw=True)
        d = NHGIS_DIR / f'extract_{n}'
        d.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = z.namelist()
            z.extractall(d)
        (d / 'PROVENANCE-nhgis.md').write_text(
            f'# NHGIS extract {n} ({self.title})\n\nRequested and downloaded {time.strftime("%Y-%m-%d %H:%M")} via the '
            f'IPUMS API v2 (scripts/harness/{self.script}). Tables: see ../{self.request_name.format(n=n)}. '
            f'Files: {len(names)}.\n\n{CITATION}\n\n{TERMS}\n')
        return names

    def cli(self):
        ap = argparse.ArgumentParser(description=f'NHGIS extract: {self.title}. submit prints the extract number; '
                                                 'wait N polls every 30 s, then downloads into the cache.')
        ap.add_argument('cmd', nargs='?', default='submit', choices=['submit', 'status', 'wait'])
        ap.add_argument('n', nargs='?', type=int, help='extract number (status, wait)')
        a = ap.parse_args()
        if a.cmd == 'submit':
            print('extract', self.submit())
            return
        if a.n is None:
            ap.error(f'{a.cmd} needs the extract number')
        if a.cmd == 'status':
            st = status(a.n)
            print(st['status'], st.get('errors'))
            return
        while True:
            st = status(a.n)
            print(time.strftime('%H:%M:%S'), st['status'], flush=True)
            if st['status'] == 'completed':
                print('files', self.download(a.n, st))
                return
            if st['status'] in ('failed', 'canceled'):
                raise SystemExit(f'extract {a.n} {st["status"]}: {st.get("errors")}')
            time.sleep(30)


# ---------------------------------------------------------------- population tables
SRC = NHGIS_DIR / 'extract_1/nhgis0001_csv'  # 1870–1970 state tables (nhgis_extract.py)
COLS = ['year', 'state', 'sex', 'group', 'race_as_recorded', 'label_as_recorded', 'count', 'vintage_mode', 'note',
        'source_table', 'source_url', 'page']
NHGIS_URL = 'https://www.nhgis.org'
STATE_CODE = {k.casefold(): v for k, v in CODE_OF.items()}  # NHGIS writes "District Of Columbia"


def load(ds: str, src: Path = SRC, pattern: str = 'nhgis0001_{ds}_*_state.csv') -> pd.DataFrame:
    """One NHGIS state table, unfiltered. Row 2 repeats the headers as descriptions and is skipped."""
    return pd.read_csv(next(src.glob(pattern.format(ds=ds))), encoding='latin-1', skiprows=[1])


def row(year, state, sex, group, race, label, count, note, table) -> dict:
    return {'year': year, 'state': state, 'sex': sex, 'group': group, 'race_as_recorded': race,
            'label_as_recorded': label, 'count': count, 'vintage_mode': 'truth', 'note': note,
            'source_table': table, 'source_url': NHGIS_URL, 'page': ''}


def frame(rows: list) -> pd.DataFrame:
    """Rows in output order: by state, sex, group."""
    return pd.DataFrame(rows, columns=COLS).sort_values(['state', 'sex', 'group'], kind='stable').reset_index(drop=True)


def rows(year, d, spec, table, note='tabulated') -> list:
    """spec: [(column, sex, group, label)] → one row per state of d and spec entry, unrounded."""
    return [row(year, st, sex, group, label.split(':')[0], label, float(r[col]), note, table)
            for st, r in d.iterrows() for col, sex, group, label in spec]


def assert_close(a, b, what, tol=1.0):
    gap = (pd.Series(a) - pd.Series(b)).abs().dropna()
    assert gap.max() < tol, f'{what}: off by {gap.max()} ({gap.idxmax()})'


def hand_vs_nhgis(hand: pd.DataFrame, nh: pd.DataFrame) -> pd.DataFrame:
    """Counts by (state, sex, harness group) side by side; NaN where only one side has the cell."""
    from simharness.data import GROUP_MAP

    def agg(x):
        return x.assign(g=x.group.map(lambda g: GROUP_MAP.get(g, g))).groupby(['state', 'sex', 'g'])['count'].sum()
    return pd.concat([agg(hand[hand.group != 'TOTAL']).rename('hand'), agg(nh).rename('nhgis')], axis=1)


def off_cells(j: pd.DataFrame) -> pd.DataFrame:
    """Adds diff and rel to a filled hand_vs_nhgis frame; returns the cells off by >50 and >0.5%."""
    j['diff'] = j.nhgis - j.hand
    j['rel'] = j['diff'] / j.hand.clip(lower=1)
    return j[(j['diff'].abs() > 50) & (j.rel.abs() > 0.005)]


def print_worst(bad: pd.DataFrame):
    if len(bad):
        print(bad.sort_values('diff', key=abs, ascending=False).head(15).to_string())
