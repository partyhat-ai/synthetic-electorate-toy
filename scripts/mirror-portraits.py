#!/usr/bin/env python3
"""Mirror the candidates' Wikimedia Commons portraits for the assets bucket.

For every person in src/lib/simulacra/history.ts (PEOPLE), resolve the Commons
file through the Commons API (prop=imageinfo, iiprop=url|extmetadata), download
its 330px thumbnail to <out>/portraits/<id>.jpg, and write
<out>/portraits/credits.json with the file page, author, licence name and
licence URL exactly as the API gives them (never guessed).

The output stays out of git; scripts/publish-assets.sh uploads it.
Re-runnable: existing images are kept unless --force.

  python3 scripts/mirror-portraits.py --out ../simulacra-assets
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / 'src/lib/simulacra/history.ts'
API = 'https://commons.wikimedia.org/w/api.php'
# Wikimedia's User-Agent policy: identify the tool and a contact.
UA = 'SimulacraAmericana-portrait-mirror/1.0 (https://simulacraamericana.com; cam@partyhat.ai)'
WIDTH = 330

# `  id: ["Full Name", "Surname", "x/xy/File.jpg/330px-File.jpg"],` inside PEOPLE.
ROW = re.compile(r'^\s*(\w+):\s*\["([^"]+)",\s*"[^"]*",\s*"([^"]+)"\]', re.M)


def people() -> list[tuple[str, str, str]]:
    src = HISTORY.read_text()
    block = src[src.index('const PEOPLE = {'):]
    block = block[:block.index('\n}')]
    rows = []
    for pid, name, path in ROW.findall(block):
        # "b/b6/<File>/330px-<File>": the Commons file name is the third segment.
        rows.append((pid, name, urllib.parse.unquote(path.split('/')[2])))
    if not rows:
        sys.exit(f'no PEOPLE rows parsed from {HISTORY}')
    return rows


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 3:
                time.sleep(2 ** attempt * 2)
                continue
            raise
    raise RuntimeError('unreachable')


def plain(value: str | None) -> str | None:
    """extmetadata values are HTML fragments; keep their text."""
    if not value:
        return None
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', value))).strip() or None


def imageinfo(titles: list[str]) -> dict[str, dict]:
    q = urllib.parse.urlencode({
        'action': 'query', 'format': 'json', 'formatversion': '2', 'prop': 'imageinfo',
        'iiprop': 'url|extmetadata', 'iiurlwidth': WIDTH, 'titles': '|'.join(f'File:{t}' for t in titles),
    })
    data = json.loads(get(f'{API}?{q}'))
    # The API normalises titles (underscores -> spaces); map back.
    norm = {n['to']: n['from'] for n in data['query'].get('normalized', [])}
    out = {}
    for page in data['query']['pages']:
        asked = norm.get(page['title'], page['title'])
        out[asked.removeprefix('File:')] = page
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True, help='assets staging folder (outside the repo)')
    ap.add_argument('--force', action='store_true', help='re-download images that already exist')
    args = ap.parse_args()
    dest = args.out / 'portraits'
    dest.mkdir(parents=True, exist_ok=True)

    rows = people()
    pages: dict[str, dict] = {}
    files = sorted({f for _, _, f in rows})
    for i in range(0, len(files), 40):  # the API takes 50 titles per query
        pages.update(imageinfo(files[i:i + 40]))

    credits, problems = {}, []
    for pid, name, file in rows:
        page = pages.get(file)
        info = (page or {}).get('imageinfo', [None])[0]
        if not info:
            problems.append(f'{pid}: {file} not found on Commons')
            continue
        meta = info.get('extmetadata', {})
        val = lambda k: plain(meta.get(k, {}).get('value'))  # noqa: E731
        target = dest / f'{pid}.jpg'
        if args.force or not target.exists():
            target.write_bytes(get(info['thumburl']))
            time.sleep(0.2)
        credits[pid] = {
            'name': name,
            'file': f'File:{file}',
            'filePage': info['descriptionurl'],
            'author': val('Artist'),
            'credit': val('Credit'),
            'license': val('LicenseShortName'),
            'licenseUrl': val('LicenseUrl'),
            'attributionRequired': val('AttributionRequired') == 'true',
            'usageTerms': val('UsageTerms'),
        }
        lic = credits[pid]['license'] or ''
        if credits[pid]['attributionRequired'] and not credits[pid]['author']:
            problems.append(f'{pid}: {lic} requires attribution but the API gives no author')

    (dest / 'credits.json').write_text(json.dumps(credits, indent=2, ensure_ascii=False) + '\n')
    needs = sorted(p for p, c in credits.items() if c['attributionRequired'])
    print(f'{len(credits)}/{len(rows)} portraits mirrored to {dest}')
    print(f'{len(needs)} need attribution: {", ".join(needs) or "none"}')
    for p in problems:
        print('PROBLEM', p, file=sys.stderr)
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
