"""The pipeline. `python -m simharness.run <stage> --config configs/prototype-1920.json`

Stages (each writes into runs/<run id>/ and can be rerun alone):
  backbone   population + backbone fit + the unchanged-run reproduction check
  plan       sample agents and write every model request (no calls)
  ask        send pending requests through the configured backend
  analyze    paired effects, leakage probes, label swap, bias, audit, quotes
  evaluate   pre-registered checks → validation.json (+ EVAL table rows)
  all        backbone → plan → ask → analyze → evaluate
"""
from __future__ import annotations

import argparse
import json
import sys

from .config import ROOT, RunConfig
from .pipeline import Run


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['backbone', 'plan', 'ask', 'analyze', 'evaluate', 'all', 'id'])
    ap.add_argument('--config', default=str(ROOT / 'configs/prototype-1920.json'))
    args = ap.parse_args(argv)
    run = Run(RunConfig.load(args.config))
    stages = ['backbone', 'plan', 'ask', 'analyze', 'evaluate'] if args.stage == 'all' else [args.stage]
    for s in stages:
        if s == 'id':
            print(run.id)
            continue
        out = getattr(run, s)()
        print(s, json.dumps(out if not hasattr(out, 'world') else {'fit': 'ok'}, default=float)[:2000])


if __name__ == '__main__':
    sys.exit(main())
