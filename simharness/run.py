"""The pipeline. `python -m simharness.run <stage> --config configs/prototype-1920.json`

Stages (each writes into runs/<run id>/ and can be rerun alone):
  backbone   population + backbone fit + the unchanged-run reproduction check
  plan       sample agents and write every model request (no calls)
  ask        send pending requests through the configured backend
  analyze    paired effects, leakage probes, label swap, bias, audit, quotes
  publish    every what-if combination → the page's result shape + bundle
  evaluate   pre-registered checks → validation.json (+ EVAL table rows); 1920 only
  verify     any year: the unchanged rerun reproduces every state's R/D/O (R1), plus
             Corder–Wolbrecht where it exists
  dryrun     free: backbone (if needed) → verify → plan, with brief samples and counts
             (`python -m simharness.run dryrun --year 1880`)
  all        backbone → plan → ask → analyze → publish → evaluate
"""
from __future__ import annotations

import argparse
import json
import sys

from .config import ROOT, RunConfig
from .pipeline import LEGISLATURE_EV, Run
from .publish import CONF, KIND_ORDER, SOURCES, briefs_record, census_phrase, pre_interviews, sources_for

# The stages live in pipeline.py and publish.py; these names stay importable from here.
__all__ = ['CONF', 'KIND_ORDER', 'LEGISLATURE_EV', 'SOURCES', 'Run', 'briefs_record', 'census_phrase', 'main',
           'pre_interviews', 'sources_for']


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['backbone', 'plan', 'ask', 'analyze', 'publish', 'evaluate', 'verify', 'dryrun', 'all', 'id',
                                      'research', 'whatif', 'stage'])
    ap.add_argument('--config', default=str(ROOT / 'configs/prototype-1920.json'))
    ap.add_argument('--year', type=int, help='use configs/live-<year>.json (instead of --config)')
    ap.add_argument('--samples', type=int, default=1, help='dryrun: briefs to print per slice and per what-if')
    ap.add_argument('--all-cohorts', action='store_true',
                    help='dryrun: ignore the config\'s only_cohorts and arms (every group and arm; a separate run folder)')
    ap.add_argument('--text', help='whatif: the words a reader typed')
    ap.add_argument('--queue', action='store_true', help='whatif: model what the router queued as unknown')
    ap.add_argument('--limit', type=int, default=3, help='whatif --queue: at most this many texts')
    ap.add_argument('--refresh', action='store_true', help='research again even if evidence is saved')
    ap.add_argument('--key', help='research: only this what-if')
    ap.add_argument('--reextract', action='store_true', help='research: extract findings again from the saved notes (no search)')
    args = ap.parse_args(argv)
    if args.year:
        args.config = str(ROOT / f'configs/live-{args.year}.json')
    if args.stage in ('research', 'whatif', 'stage'):
        from . import intake
        if args.stage == 'research':
            out = intake.research_config(args.config, args.refresh, args.key, args.reextract)
        elif args.stage == 'stage':
            out = intake.stage_config(args.config, args.key, args.refresh)
        elif args.queue:
            out = intake.process_queue(args.config, args.limit)
        elif args.text:
            out = intake.whatif(args.text, args.config, args.refresh)
        else:
            ap.error('whatif needs --text or --queue')
        print(json.dumps(out, indent=1, default=float))
        return
    cfg = RunConfig.load(args.config)
    if args.all_cohorts:
        cfg.agents.only_cohorts, cfg.agents.arms, cfg.agents.max_requests = None, None, None
    run = Run(cfg)
    stages = ['backbone', 'plan', 'ask', 'analyze', 'evaluate', 'publish'] if args.stage == 'all' else [args.stage]
    for s in stages:
        if s == 'id':
            print(run.id)
            continue
        if s == 'dryrun':
            out = run.dryrun(args.samples)
            for b in out['briefs']:
                print(f"\n── {b['arm']} · {b['slice']} · {b['agent']} ──\n{b['user']}")
            print('\ndryrun', json.dumps({k: v for k, v in out.items() if k != 'briefs'}, indent=1, default=float))
            continue
        out = getattr(run, s)()
        print(s, json.dumps(out if not hasattr(out, 'world') else {'fit': 'ok'}, default=float)[:2000])


if __name__ == '__main__':
    sys.exit(main())
