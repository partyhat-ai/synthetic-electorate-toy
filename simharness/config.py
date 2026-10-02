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
# The repo root: configs/, profiles/, whatifs/, extracts/, runs/, sessions/ and serve/bundles/
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
    backend: str = 'anthropic'        # anthropic | anthropic-batch | transcript
    max_cohorts: int = 40             # cost cap; the merge rule folds the smallest
    arms: list | None = None          # subset of control, cf, swap, probe; None sends all
    only_cohorts: list | None = None  # cohort keys to interview; None interviews all
    max_tokens: int = 4000            # per-request output ceiling (also the estimate's worst case)
    # Compiled what-ifs only; the defaults leave hand-written what-ifs' runs as they were (D33):
    replace_barred: bool = False      # someone who can't vote in either world takes no interview slot
    focus_cohorts: int = 0            # extra cohorts the staging pass names as the change's decisive groups
    escalate_model: str | None = None  # re-ask, on this model, anyone whose answer didn't take the change as true
    escalate_max: int = 24            # cap on escalated requests per run
    fast: bool = False                # fast mode for this layer's Opus requests (escalations); 2x price


@dataclass
class ResearchConfig:
    """The once-per-what-if calls behind a typed what-if: compile → research → extract → stage
    (scenario.py, evidence.py, world.py), and the audit of the interviews' reasoning. They run
    once per change, not once per voter, so they can afford the strongest model and effort (D33)."""
    compile_model: str = 'claude-sonnet-5-5'
    research_model: str = 'claude-sonnet-5-5'
    extract_model: str = 'claude-sonnet-5-5'  # Haiku judged every analogue unreliable and extracted none (D15)
    world_model: str | None = None     # the staging pass (world.py); None skips it
    audit_model: str | None = None     # the reasoning audit (world.py); None skips it
    compile_effort: str = 'low'
    research_effort: str = 'low'
    extract_effort: str = 'low'
    world_effort: str = 'high'
    audit_effort: str = 'medium'
    pass_max_tokens: int = 3000        # compile/stage/audit output ceiling; Opus thinking counts toward it
    fast: bool = False                 # fast mode for the Opus passes (compile, extract, stage, audit); 2x price
    max_searches: int = 4              # web_search max_uses per research call
    research_max_tokens: int = 4000


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
    research: ResearchConfig = field(default_factory=ResearchConfig)
    max_combo: int = 3                  # largest what-if combination published (2^n grows fast)

    @classmethod
    def load(cls, path: str | Path) -> 'RunConfig':
        raw = json.loads(Path(path).read_text())
        # Spending caps were removed; older configs that still carry them load as before.
        agents = AgentConfig(**{k: v for k, v in raw.pop('agents', {}).items() if k not in ('max_requests', 'max_dollars')})
        research = ResearchConfig(**{k: v for k, v in raw.pop('research', {}).items() if k != 'whatif_dollars'})
        return cls(**raw, agents=agents, research=research)

    def to_dict(self) -> dict:
        return asdict(self)

    def run_id(self, data_manifest: dict | None = None) -> str:
        # G1: the code is part of the instrument, so a changed prompt or module gets a new run folder.
        code = hashlib.sha256(b''.join(p.read_bytes() for p in sorted(HERE.glob('*.py')))).hexdigest()
        blob = json.dumps({'config': self.to_dict(), 'data': data_manifest or {}, 'code': code}, sort_keys=True)
        return f'{self.election}-{hashlib.sha256(blob.encode()).hexdigest()[:10]}'
