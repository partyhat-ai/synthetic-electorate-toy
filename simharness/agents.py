"""Agents: invented people drawn from a cohort's documented makeup.

A cohort is a stratum (region × sex × race/nativity/citizenship). Each agent
gets:
- a state, drawn in proportion to the cohort's adults there;
- urban or rural, from that state's published urban share;
- an age, from the cohort's published age distribution when there is one;
- a household economy, imputed [I] and used only for persona diversity (it is
  never a cohort dimension, and nothing is counted by it);
- two to four dated items from the period corpus, preferring its own state.

The person is invented; the circumstances come from the census row and the
dated items. Names come from small, plain lists and carry no information.
"""
from __future__ import annotations

import random

from .geo import REGION_OF, STATE_NAME

GROUP_WORDS = {
    'native_white': 'a white {noun} born in the United States',
    'foreign_white_naturalized': 'a white {noun} born abroad and naturalized as a United States citizen',
    'foreign_white_alien': 'a white {noun} born abroad who is not a United States citizen',
    'black': 'a Black {noun}',
    'other': 'an American Indian or Asian American {noun}',
}

FIRST = {
    'M': ['John', 'William', 'James', 'George', 'Charles', 'Frank', 'Joseph', 'Henry', 'Robert', 'Thomas',
          'Edward', 'Harry', 'Walter', 'Arthur', 'Fred', 'Albert', 'Samuel', 'Clarence', 'Louis', 'Ernest'],
    'F': ['Mary', 'Anna', 'Margaret', 'Helen', 'Elizabeth', 'Ruth', 'Florence', 'Ethel', 'Emma', 'Clara',
          'Bertha', 'Minnie', 'Alice', 'Grace', 'Edna', 'Ida', 'Mabel', 'Lillian', 'Rose', 'Sarah'],
}
# Surnames: common American surnames for native-born and Black agents; for
# foreign-born agents, surnames of the largest 1920 immigrant origins. p1 drew
# every agent from one mixed list, which gave a Black North Carolina farmer a
# Swedish surname; p2 separates them. Names still carry no modelled meaning.
LAST_COMMON = ['Adams', 'Baker', 'Carter', 'Dawson', 'Ellis', 'Foster', 'Graham', 'Hayes', 'Irwin', 'Jordan',
               'Lawson', 'Mercer', 'Owens', 'Porter', 'Reed', 'Sutton', 'Tate', 'Walker', 'Young', 'Johnson',
               'Williams', 'Brown', 'Jones', 'Davis', 'Harris', 'Jackson', 'Thomas', 'Robinson', 'Green', 'Hill']
LAST_IMMIGRANT = ['Brandt', 'Weber', 'Schmidt', 'Rossi', 'Esposito', 'Russo', 'Kowalski', 'Nowak', 'Novak',
                  'Lindqvist', 'Johansson', 'Olsen', 'Murphy', 'Kelly', 'Sullivan', 'Cohen', 'Levy', 'Kaplan',
                  'Horvath', 'Kovac', 'Dubois', 'Papadopoulos', 'Garcia', 'Lopez', 'Svoboda', 'Petrov']
LAST = LAST_COMMON + LAST_IMMIGRANT  # p1's list, kept for reproducing p1 runs

ECONOMY = {
    'farm': 'The household lives by farming.',
    'wage': 'The household lives on wages from a mill, shop, mine or railroad.',
    'trade': 'The household lives by a trade, a store or office work.',
    'proprietor': 'The household lives by a business or a profession.',
}


def economy_weights(urban: bool) -> dict:
    # [I] imputed for persona diversity only. Replace with OCC1950 × FARM from
    # the IPUMS 1920 full count (extracts/ipums-1920-fullcount.json).
    return {'farm': 0.05, 'wage': 0.5, 'trade': 0.3, 'proprietor': 0.15} if urban else \
           {'farm': 0.7, 'wage': 0.15, 'trade': 0.1, 'proprietor': 0.05}


def pick(rng: random.Random, weights: dict):
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys])[0]


def sample_agents(cohort: dict, n: int, corpus: list[dict], seed: int, urban_share: dict,
                  age_bands: dict | None = None) -> list[dict]:
    """cohort: {key, region, sex, group, adults_by_state: {state: n}, adults}."""
    rng = random.Random(f'{seed}:{cohort["key"]}')
    out = []
    for i in range(n):
        state = pick(rng, cohort['adults_by_state'])
        urban = rng.random() < urban_share.get(state, 0.5)
        if age_bands:
            band = pick(rng, age_bands)
            lo, hi = band
            age = rng.randint(lo, hi)
        else:
            age = rng.choice(range(21, 76))  # [I] uniform when no age table
        econ = pick(rng, economy_weights(urban))
        sex = cohort['sex']
        surnames = LAST_IMMIGRANT if cohort['group'].startswith('foreign') else LAST_COMMON
        name = f'{rng.choice(FIRST[sex])} {rng.choice(surnames)}'
        items = choose_items(rng, corpus, state, cohort)
        out.append({
            'id': f'{cohort["key"]}-{i}',
            'cohort': cohort['key'],
            'state': state,
            'region': REGION_OF.get(state, 'west'),
            'sex': sex,
            'group': cohort['group'],
            'age': age,
            'urban': urban,
            'economy': econ,
            'name': name,
            'items': items,
            'weight': cohort['adults'] / n,
        })
    return out


TOPIC_PRIORITY = {
    # Which dated topics a cohort's people are likeliest to have met, by group.
    'F': ['T1', 'T7', 'T8', 'T3', 'T2', 'T4'],
    'black': ['T5', 'T3', 'T2'],
    'foreign_white_naturalized': ['T6', 'T3', 'T2'],
    'foreign_white_alien': ['T6', 'T3'],
    'default': ['T3', 'T2', 'T4', 'T6'],
}


def choose_items(rng: random.Random, corpus: list[dict], state: str, cohort: dict, k: int = 3) -> list[dict]:
    order = TOPIC_PRIORITY.get(cohort['group']) or (TOPIC_PRIORITY['F'] if cohort['sex'] == 'F' else TOPIC_PRIORITY['default'])
    if cohort['sex'] == 'F' and cohort['group'] == 'black':
        order = ['T5', 'T1', 'T3']
    region = REGION_OF.get(state, 'west')
    chosen, used = [], set()
    for topic in order:
        if len(chosen) >= k:
            break
        pool = [c for c in corpus if c['topic'] == topic and c['id'] not in used]
        if topic == 'T8':  # women already voting in the West: only relevant where it is local
            pool = [c for c in pool if REGION_OF.get(c.get('state')) == region]
        own = [c for c in pool if c.get('state') == state]
        near = [c for c in pool if REGION_OF.get(c.get('state')) == region]
        src = own or near or pool
        if src:
            it = rng.choice(src)
            chosen.append(it)
            used.add(it['id'])
    return chosen


def persona_lines(agent: dict, eligibility_line: str) -> list[str]:
    noun = 'man' if agent['sex'] == 'M' else 'woman'
    who = GROUP_WORDS[agent['group']].format(noun=noun)
    place = f'{"a city or town" if agent["urban"] else "the countryside"} in {STATE_NAME.get(agent["state"], agent["state"])}'
    return [
        f'{agent["name"]}, {agent["age"]}, {who}, living in {place}.',
        ECONOMY[agent['economy']],
        eligibility_line,
    ]
