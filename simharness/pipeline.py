"""The pipeline's stages: backbone and evaluate. Each writes into runs/<run id>/
and can be rerun alone; run.py is the command line.
"""
from __future__ import annotations

import json
import pickle

import numpy as np

from . import aggregate, backbone, data, evaluate
from .config import RUNS, RunConfig


class Run:
    def __init__(self, cfg: RunConfig):
        self.cfg = cfg
        self.inp, self.extras = data.load(cfg)
        self.manifest = self.extras['manifest']
        self.id = cfg.run_id(self.manifest)
        self.year = cfg.election
        self.dir = RUNS / self.id
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / 'config.json').write_text(json.dumps({'run_id': self.id, 'config': cfg.to_dict(),
                                                          'data': self.manifest}, indent=2))

    # ── backbone ──
    def backbone(self):
        fit = backbone.fit(self.inp, self.cfg.draws, self.cfg.seed)
        with open(self.dir / 'fit.pkl', 'wb') as f:
            pickle.dump(fit, f)
        return fit

    def fit(self):
        p = self.dir / 'fit.pkl'
        if not p.exists():
            return self.backbone()
        with open(p, 'rb') as f:
            return pickle.load(f)

    def state_index(self, fit):
        states = fit.diagnostics['states']
        return states, np.array([states.index(s) for s in fit.cells.state])

    # ── evaluate ──
    def evaluate(self):
        from . import benchmarks
        fit = self.fit()
        states, sidx = self.state_index(fit)
        base_votes = aggregate.by_state(fit.world, sidx, len(states))
        checks = [evaluate.r1_reproduction(fit, self.inp, base_votes)]
        ho = evaluate.holdout(fit, self.inp, self.cfg.holdout, self.cfg.draws, self.cfg.seed)
        checks += ho['checks']
        checks += benchmarks.natural_experiment(fit, self.inp, self.extras)
        summary = {'passed': sum(1 for c in checks if c['pass'] is True),
                   'failed': [c['id'] for c in checks if c['pass'] is False],
                   'not_run': [c['id'] for c in checks if c['pass'] is None]}
        out = {'summary': summary, 'checks': checks, 'holdout_rows': ho['rows']}
        (self.dir / 'validation.json').write_text(json.dumps(out, indent=1, default=float))
        return out
