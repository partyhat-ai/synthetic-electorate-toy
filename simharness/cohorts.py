"""Agent cohorts: strata of the cell table, merged to a cost cap.

Stratification for 1920 (justified in METHOD.md §A.2): region × sex ×
race/nativity/citizenship. These are the dimensions the franchise turned on in
1920 (sex, citizenship, race in practice) plus region, which carried the
parties' coalitions. Age and urban/rural vary within a cohort's agents (persona
diversity) but don't define cohorts: no 1920 source identifies their effect.

Merge rule: while there are more cohorts than the cap, or any cohort holds
under `min_share` of eligible-or-barred adults, fold the smallest into the same
sex and group in the nearest region (geo.NEAREST_REGION); a cohort with no
same-(sex, group) neighbour left folds into the national cohort for that sex
and group. The rule is deterministic, so a cohort's key names every region it
holds.
"""
from __future__ import annotations

import pandas as pd

from .geo import NEAREST_REGION

GROUP_LABEL = {
    'native_white': 'native-born white', 'foreign_white_naturalized': 'naturalized immigrant',
    'foreign_white_alien': 'immigrant non-citizen', 'black': 'Black', 'other': 'American Indian and Asian',
}
SEX_LABEL = {'M': 'men', 'F': 'women'}


def build(cells: pd.DataFrame, cap: int = 40, min_share: float = 0.004) -> tuple[dict, dict]:
    """Returns ({cohort key: cohort}, {cell index: cohort key})."""
    total = cells.adults20.sum()
    groups = {}
    for i, r in cells.iterrows():
        k = (r.region, r.sex, r.group)
        groups.setdefault(k, []).append(i)
    members = {k: set([k[0]]) for k in groups}

    def size(k):
        return cells.loc[groups[k], 'adults20'].sum()

    while True:
        # A national cohort can't merge further, so it's never picked.
        keys = [k for k in sorted(groups, key=size) if k[0] != 'national']
        small = [k for k in keys if size(k) < min_share * total]
        if (len(groups) <= cap and not small) or not keys:
            break
        k = small[0] if small else keys[0]
        region, sex, group = k
        target = next(((r, sex, group) for r in NEAREST_REGION.get(region, []) if (r, sex, group) in groups and (r, sex, group) != k), None)
        if target is None:
            target = ('national', sex, group)
            groups.setdefault(target, [])
            members.setdefault(target, set())
        groups[target] += groups.pop(k)
        members[target] |= members.pop(k)

    cohorts, cell_to = {}, {}
    for k, idx in groups.items():
        regions = '+'.join(sorted(members[k]))
        key = f'{regions}:{k[1]}:{k[2]}'
        sub = cells.loc[idx]
        by_state = sub.groupby('state').adults20.sum().to_dict()
        cohorts[key] = {
            'key': key, 'region': k[0] if len(members[k]) == 1 else 'mixed', 'regions': sorted(members[k]),
            'sex': k[1], 'group': k[2], 'adults': float(sub.adults20.sum()),
            'adults_by_state': by_state,
            'label': f'{GROUP_LABEL[k[2]].capitalize()} {SEX_LABEL[k[1]]}, {regions.replace("+", ", ")}',
        }
        for i in idx:
            cell_to[i] = key
    return cohorts, cell_to
