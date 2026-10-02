"""Run configuration: everything that determines a run, hashed into its id.

A run is re-hashed by (election, seed, draw counts, holdout states, data
manifest). Two runs with the same hash must produce the same numbers; the run
directory is named by it.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
# The repo root: configs/, extracts/ and runs/ all sit next to the simharness
# package.
ROOT = HERE.parent
RUNS = ROOT / 'runs'

# Raw downloads live outside the web repo: some carry terms that forbid
# redistribution, and the UI agent's dev server shouldn't watch them.
CACHE = Path(os.environ.get(
    'SIMHARNESS_CACHE',
    str(Path.home() / 'research_notes/historical_election_sim_data/harness_cache'),
))


@dataclass
class RunConfig:
    election: int = 1920
    election_day: str = '1920-11-02'
    context_cutoff: str = '1920-11-01'  # last admissible source date
    mode: str = 'truth'                 # truth | strict
    seed: int = 1920
    draws: int = 400
    holdout: list = field(default_factory=lambda: 'CA FL ID IN LA MI MO MT NC NY OH OK'.split())

    @classmethod
    def load(cls, path: str | Path) -> 'RunConfig':
        return cls(**json.loads(Path(path).read_text()))

    def to_dict(self) -> dict:
        return asdict(self)

    def run_id(self, data_manifest: dict | None = None) -> str:
        blob = json.dumps({'config': self.to_dict(), 'data': data_manifest or {}}, sort_keys=True)
        return f'{self.election}-{hashlib.sha256(blob.encode()).hexdigest()[:10]}'
