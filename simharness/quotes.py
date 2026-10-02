"""Choosing whose words the page shows, and auditing the reasons behind them.

Selection is by representativeness, never by drama:
1. Within a page slice, a cohort is drawn in proportion to its adults.
2. Within that cohort, the agent chosen is the one whose change (control →
   counterfactual) is closest to the cohort's median change. Ties go to the
   earliest id; nothing is chosen for vividness.
3. Across a run's quotes, at least one person whose vote didn't change is
   shown. If none was chosen, the slice with the most such agents swaps its
   pick for its most typical unchanged agent.

Every quote keeps its cohort, the adults it stands for, both answers, the date
of its context and the dated sources it cites.
"""
from __future__ import annotations

import random
import re

import numpy as np

LABEL_DRIVEN = re.compile(
    r"\b(as an? |being an? |like (most|all|other) )(woman|women|man|men|black|negro|colored|immigrant|foreigner|"
    r"german|irish|italian|pole|swede|catholic|protestant|farmer'?s wife|southerner|northerner|westerner)\b"
    r"|\b(women|negroes|black (people|folks|men|women)|immigrants|foreigners|catholics|southerners|farmers) "
    r"(usually|always|naturally|tend to|are inclined|by nature)\b",
    re.I,
)


def label_driven(reason: str, sources_used: list) -> bool:
    """Heuristic flag for stereotype-driven logic: reasoning from a group label
    rather than from a circumstance in the brief. The audit sample is also
    read by a person; this flag is the first pass."""
    return bool(LABEL_DRIVEN.search(reason or '')) and not sources_used


def audit(rows: list[dict], share: float, rng: random.Random, minimum: int = 30) -> dict:
    n = max(minimum, int(round(len(rows) * share)))
    sample = rng.sample(rows, min(n, len(rows)))
    flagged = [r for r in sample if label_driven(r['reason'], r.get('sources_used'))]
    return {'audited': len(sample), 'flagged': len(flagged), 'rate': len(flagged) / max(1, len(sample)),
            'flagged_examples': [{'agent': r['agent'], 'reason': r['reason']} for r in flagged[:10]]}


def deblind(text: str, label_names: dict) -> str:
    for label, name in label_names.items():
        text = re.sub(rf'\b(?:Candidate|candidate|Mr\.)\s+{label}\b', name, text)
    return text


def select(slices: dict, agents: dict, answers: dict, cohort_adults: dict, seed: int) -> list[dict]:
    """slices: {slice: [cohort keys]}; agents: {id: agent}; answers: {id: {'control', 'cf'}}
    (normalized rows with text). Returns one pick per slice."""
    rng = random.Random(f'quotes:{seed}')
    picks, unchanged_by_slice = [], {}
    for sl, cohorts in slices.items():
        cohorts = [c for c in cohorts if any(a['cohort'] == c and a['id'] in answers for a in agents.values())]
        if not cohorts:
            continue
        c = rng.choices(cohorts, weights=[cohort_adults[x] for x in cohorts])[0]
        members = sorted([a for a in agents.values() if a['cohort'] == c and a['id'] in answers], key=lambda a: a['id'])

        def change(a):
            x = answers[a['id']]
            return (x['cf']['p_vote'] * np.nan_to_num(x['cf']['R'])) - (x['control']['p_vote'] * np.nan_to_num(x['control']['R']))

        med = float(np.median([change(a) for a in members]))
        pick = min(members, key=lambda a: (abs(change(a) - med), a['id']))
        picks.append({'slice': sl, 'agent': pick, 'cohort': c})
        unchanged_by_slice[sl] = [a for a in members if answers[a['id']]['cf']['choice'] == answers[a['id']]['control']['choice']]
    if picks and not any(answers[p['agent']['id']]['cf']['choice'] == answers[p['agent']['id']]['control']['choice'] for p in picks):
        sl = max(unchanged_by_slice, key=lambda s: len(unchanged_by_slice[s]), default=None)
        if sl and unchanged_by_slice[sl]:
            for p in picks:
                if p['slice'] == sl:
                    p['agent'] = unchanged_by_slice[sl][0]
                    p['swapped_for_unchanged'] = True
    return picks
