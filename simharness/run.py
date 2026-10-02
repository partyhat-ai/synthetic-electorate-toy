"""The pipeline. `python -m simharness.run <stage> --config configs/prototype-1920.json`

Stages (each writes into runs/<run id>/ and can be rerun alone):
  backbone   population + backbone fit + the unchanged-run reproduction check
  plan       sample agents and write every model request (no calls)
  ask        send pending requests through the configured backend
  analyze    paired effects, leakage probes, label swap, bias, audit, quotes
  publish    every what-if combination → the page's result shape + bundle
  evaluate   pre-registered checks → validation.json (+ EVAL table rows); 1920 only
  verify     the unchanged rerun reproduces every state's R/D/O (R1), plus
             Corder–Wolbrecht where it exists (1924)
  all        backbone → plan → ask → analyze → publish → evaluate
"""
from __future__ import annotations

import argparse
import json
import sys

from .config import ROOT, RunConfig
from .pipeline import Run


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['backbone', 'plan', 'ask', 'analyze', 'publish', 'evaluate', 'verify', 'all', 'id',
                                      'research', 'whatif'])
    ap.add_argument('--config', default=str(ROOT / 'configs/prototype-1920.json'))
    ap.add_argument('--text', help='whatif: the words a reader typed')
    ap.add_argument('--queue', action='store_true', help='whatif: model what the router queued as unknown')
    ap.add_argument('--limit', type=int, default=3, help='whatif --queue: at most this many texts')
    ap.add_argument('--refresh', action='store_true', help='research again even if evidence is saved')
    ap.add_argument('--key', help='research: only this what-if')
    ap.add_argument('--reextract', action='store_true', help='research: extract findings again from the saved notes (no search)')
    args = ap.parse_args(argv)
    if args.stage in ('research', 'whatif'):
        from . import intake
        if args.stage == 'research':
            out = intake.research_config(args.config, args.refresh, args.key, args.reextract)
        elif args.queue:
            out = intake.process_queue(args.config, args.limit)
        elif args.text:
            out = intake.whatif(args.text, args.config, args.refresh)
        else:
            ap.error('whatif needs --text or --queue')
        print(json.dumps(out, indent=1, default=float))
        return
    run = Run(RunConfig.load(args.config))
    stages = ['backbone', 'plan', 'ask', 'analyze', 'evaluate', 'publish'] if args.stage == 'all' else [args.stage]
    for s in stages:
        if s == 'id':
            print(run.id)
            continue
        out = getattr(run, s)()
        print(s, json.dumps(out if not hasattr(out, 'world') else {'fit': 'ok'}, default=float)[:2000])


if __name__ == '__main__':
    sys.exit(main())
