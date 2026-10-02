"""Run configuration: everything that determines a run, hashed into its id.

A run is re-hashed by (election, what-ifs, seed, models, prompt version, draw
counts, agent counts, data manifest). Two runs with the same hash must produce
the same numbers; the run directory is named by it.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
# The repo root: configs/, extracts/, runs/ and serve/bundles/
# all sit next to the simharness package.
ROOT = HERE.parent
RUNS = ROOT / 'runs'

# Raw downloads live outside the web repo: some carry terms that forbid
# redistribution, and the UI agent's dev server shouldn't watch them.
CACHE = Path(os.environ.get(
    'SIMHARNESS_CACHE',
    str(Path.home() / 'research_notes/historical_election_sim_data/harness_cache'),
))


@dataclass
class AgentConfig:
    bulk_model: str = 'claude-sonnet-5-5'
    check_model: str = 'claude-opus-5-5'
    check_share: float = 0.2          # share of agents also asked on check_model
    per_cohort: int = 6               # agents per agent cohort
    paraphrases: int = 3              # control and counterfactual paraphrases
    effort: str = 'low'               # output_config.effort for the voice layer
    backend: str = 'anthropic'        # anthropic | anthropic-batch | transcript | mock
    max_cohorts: int = 40             # cost cap; the merge rule folds the smallest
    arms: list | None = None          # subset of control, cf, swap, probe; None sends all
    only_cohorts: list | None = None  # cohort keys to interview; None interviews all
    max_requests: int | None = None   # hard cap on requests per run
    max_dollars: float | None = None  # hard stop, checked against the dry-run estimate
    max_tokens: int = 4000            # per-request output ceiling (also the estimate's worst case)


@dataclass
class RunConfig:
    election: int = 1920
    election_day: str = '1920-11-02'
    context_cutoff: str = '1920-11-01'  # last admissible source date
    mode: str = 'truth'                 # truth | strict
    what_ifs: list = field(default_factory=lambda: ['no-19th', 'fifteenth', 'league'])
    seed: int = 1920
    draws: int = 400
    prompt_version: str = 'p1'
    holdout: list = field(default_factory=lambda: 'CA FL ID IN LA MI MO MT NC NY OH OK'.split())
    agents: AgentConfig = field(default_factory=AgentConfig)

    @classmethod
    def load(cls, path: str | Path) -> 'RunConfig':
        raw = json.loads(Path(path).read_text())
        agents = AgentConfig(**raw.pop('agents', {}))
        return cls(**raw, agents=agents)

    def to_dict(self) -> dict:
        return asdict(self)

    def run_id(self, data_manifest: dict | None = None) -> str:
        blob = json.dumps({'config': self.to_dict(), 'data': data_manifest or {}}, sort_keys=True)
        return f'{self.election}-{hashlib.sha256(blob.encode()).hexdigest()[:10]}'
