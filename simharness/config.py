"""Paths: the repo root and the data cache, which lives outside the repo.
"""
from __future__ import annotations

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# Raw downloads live outside the web repo: some carry terms that forbid
# redistribution, and the UI agent's dev server shouldn't watch them.
CACHE = Path(os.environ.get(
    'SIMHARNESS_CACHE',
    str(Path.home() / 'research_notes/historical_election_sim_data/harness_cache'),
))
