"""The pipeline. `python -m simharness.run <stage> --config configs/prototype-1920.json`

Stages (each writes into runs/<run id>/ and can be rerun alone):
  backbone   population + backbone fit
  evaluate   pre-registered checks → validation.json (+ EVAL table rows)
  id         print the run id
"""
from __future__ import annotations

import argparse
import json
import sys

from .config import ROOT, RunConfig
from .pipeline import Run


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['backbone', 'evaluate', 'id'])
    ap.add_argument('--config', default=str(ROOT / 'configs/prototype-1920.json'))
    args = ap.parse_args(argv)
    run = Run(RunConfig.load(args.config))
    if args.stage == 'id':
        print(run.id)
        return
    out = getattr(run, args.stage)()
    print(args.stage, json.dumps(out if not hasattr(out, 'world') else {'fit': 'ok'}, default=float)[:2000])


if __name__ == '__main__':
    sys.exit(main())
