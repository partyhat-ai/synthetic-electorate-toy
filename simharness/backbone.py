"""The statistical backbone, starting with who may vote.

Every adult 21+ is in a cell (state × sex × group), and nobody is dropped:
legal_can gives each cell the fraction legally able to vote, and a reason
code for the rest.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

GROUPS = ['native_white', 'foreign_white_naturalized', 'foreign_white_alien', 'black', 'other']


@dataclass
class Inputs:
    cells: pd.DataFrame      # state, sex, group, adults20, adults16
    women16: set             # states where women could vote for president in Nov 1916
    women_pre19: set         # states where women could vote for president in Nov 1920 without the 19th
    alien_voting: set        # states where declarant aliens could vote in 1920
    other_citizen: dict = field(default_factory=dict)  # state → citizen share of 'other' adults


def legal_can(inp: Inputs, year: int) -> tuple[np.ndarray, list]:
    """Fraction of each cell legally able to vote, and the reason for the rest.

    Aliens only where inp.alien_voting; 'other' × inp.other_citizen. Women:
    1916 by women16; in 1920 the 19th Amendment covers every state."""
    c = inp.cells
    can = np.ones(len(c))
    reason = [''] * len(c)
    for i, r in enumerate(c.itertuples()):
        if r.group == 'foreign_white_alien' and r.state not in inp.alien_voting:
            can[i], reason[i] = 0.0, 'noncitizen'
        elif r.group == 'other':
            can[i] = inp.other_citizen.get(r.state, 1.0)
            reason[i] = 'native_status' if can[i] < 1 else ''
        if r.sex == 'F':
            if year == 1916 and r.state not in inp.women16:
                can[i], reason[i] = 0.0, 'sex'
    return can, reason
