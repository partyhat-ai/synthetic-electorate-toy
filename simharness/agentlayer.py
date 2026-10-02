"""Builds every model request for a run (control, counterfactuals, label swap,
recall probe, second-model check) and reads the answers back.

Request id: <arm>|<agent id>|<model short>   arm ∈ control, cf:<what-if>, swap, probe
"""
from __future__ import annotations

import random

from . import prompts
from .agents import persona_lines, sample_agents
from .geo import SOUTH, STATE_NAME

SHORT = {'claude-sonnet-5-5': 'sonnet', 'claude-opus-5-5': 'opus', 'claude-haiku-4-5': 'haiku'}

R_DESCRIPTOR = 'nominee of the party that has held a majority in Congress since the 1918 elections'
D_DESCRIPTOR = 'nominee of the party of the administration in office since 1913'


ORDER_1920 = ['League of Nations', 'cost of living', 'labor', 'agriculture', 'women', 'immigration', 'Prohibition']


def party_planks(platforms: dict, party: str, drop_topics: set = frozenset(), k: int = 3, order: list = ORDER_1920) -> list[str]:
    """The control's k planks, minus any dropped topic (never replaced, so a
    counterfactual ballot differs from the control only by the change)."""
    planks = [p for p in platforms.get('planks', []) if p['party'] == party
              and 'silent' not in p['neutral_paraphrase'].lower()]
    planks.sort(key=lambda p: next((i for i, t in enumerate(order) if t.lower() in p['topic'].lower()), 99))
    planks = [p for p in planks[:k] if not any(d.lower() in p['topic'].lower() for d in drop_topics)]
    return [p['neutral_paraphrase'].rstrip('.') + '.' for p in planks]


def eligibility_line(agent: dict, fr: dict) -> str:
    s, name = agent['state'], STATE_NAME.get(agent['state'], agent['state'])
    table = fr['table']
    poll = bool(table.loc[s].get('poll_tax', 0)) if s in table.index else False
    lit = bool(table.loc[s].get('literacy_test', 0)) if s in table.index else False
    if agent['group'] == 'foreign_white_alien' and s not in fr.get('alien_voting', set()):
        return 'This person is not a United States citizen and cannot vote.'
    if agent['sex'] == 'F' and s in fr.get('closed_1920', ()):
        return f'Registration in {name} closed before women could enrol, so this person cannot vote for president this year.'
    parts = []
    devices = ' and '.join(x for x, on in (('a poll tax', poll), ('a literacy or "understanding" test', lit)) if on)
    if agent['group'] == 'black' and s in SOUTH:
        line = 'This person is a citizen.'
        if devices:
            line += f' {name} requires {devices} to register,'
        else:
            line += f' In {name}'
        return line + ' and in this county few Black citizens have been allowed to register or vote.'
    if agent['sex'] == 'F':
        y = fr['pres_year'].get(s)
        if s in fr['women_pre19'] and y and y == y and int(y) <= 1916:
            parts.append(f'Women have voted for president in {name} since {int(y)}.')
        elif s in fr['women_pre19'] and y and y == y:
            # No presidential election fell between 1917 and 1919.
            parts.append(f'{name} law gave women the vote for president in {int(y)}, so this is the first presidential '
                         'election this person can vote in.')
        else:
            parts.append('With the suffrage amendment ratified in August, this person can vote for president for the first time.')
    else:
        parts.append('This person can vote.')
    if devices:
        parts.append(f'{name} requires {devices} to vote.')
    return ' '.join(parts)


def items_for(agent: dict, drop_topics=frozenset(), drop_after: str | None = None) -> list[dict]:
    out = []
    for it in agent['items']:
        if it['identifying']:
            continue
        if it['topic'] in drop_topics and (drop_after is None or it['date'] >= drop_after):
            continue
        out.append(it)
    return out


def build_requests(cfg, cohorts: dict, extras: dict, inp, registry: dict) -> tuple[list, list]:
    ag = cfg.agents
    fr, corpus, platforms = extras['franchise'], [c for c in extras['corpus'] if not c['identifying']], extras['platforms']
    keys = ['R', 'D']
    agents, reqs = [], []
    asof = cfg.context_cutoff  # p1 used '1920-10-30' with items to 1 Nov
    for key in sorted(cohorts):
        co = cohorts[key]
        if co['group'] == 'other':
            continue  # too few adults per region for a cohort; counted by the backbone only
        agents += sample_agents(co, ag.per_cohort, corpus, cfg.seed, extras['urban'])
    for n, a in enumerate(agents):
        rng = random.Random(f'{cfg.seed}:{a["id"]}')
        label_of, order = prompts.assign_labels(rng, keys)
        labels = [label_of[p] for p in order]
        a['label_of'] = label_of
        a['paraphrase'] = n % ag.paraphrases
        elig = eligibility_line(a, fr)
        a['eligibility'] = elig
        q = prompts.QUESTIONS[a['paraphrase']]

        def parties(drop=frozenset(), swap=False):
            desc = {'R': R_DESCRIPTOR, 'D': D_DESCRIPTOR}
            plank = {p: party_planks(platforms, p, drop) for p in keys}
            if swap:
                plank = {**plank, 'R': plank['D'], 'D': plank['R']}
                desc = {**desc, 'R': desc['D'], 'D': desc['R']}
            return [{'key': p, 'descriptor': desc[p], 'planks': plank[p]} for p in order]

        def request(arm, model, persona_elig, world, items, ballot_parties, disp_labels, system=prompts.SYSTEM,
                    question=q, schema=None, meta=None):
            text = prompts.brief({'lines': persona_lines(a, persona_elig)}, world, items,
                                 prompts.ballot_block(STATE_NAME.get(a['state'], a['state']), ballot_parties, disp_labels), asof)
            return {
                'id': f'{arm}|{a["id"]}|{SHORT.get(model, model)}',
                'model': model, 'system': system, 'user': f'{text}\n\n{question}',
                'schema': schema or prompts.answer_schema(disp_labels),
                'meta': {'kind': arm.split(':')[0], 'arm': arm, 'agent': a['id'], 'cohort': a['cohort'],
                         'labels': disp_labels, 'label_of': label_of, 'paraphrase': a['paraphrase'],
                         'prompt_version': prompts.PROMPT_VERSION, 'context_date': asof,
                         'sources': [i['id'] for i in items], **(meta or {})},
            }

        models = [ag.bulk_model] + ([ag.check_model] if rng.random() < ag.check_share else [])
        ctl_items = items_for(a)
        for model in models:
            reqs.append(request('control', model, elig, {}, ctl_items, parties(), labels))
        # Counterfactuals: the same persona, labels, order, paraphrase and model.
        for wk in cfg.what_ifs:
            spec = registry[wk]
            if spec['facts'] is None:
                continue
            if spec['mode'] == 'backbone' and not agent_reached(a, wk):
                continue
            if a['group'] == 'foreign_white_alien' and spec['mode'] == 'agents':
                continue  # can't vote in either world; no effect to measure
            f = spec['facts'](a, inp)
            if not f['facts'] and f.get('eligibility') is None:
                continue
            items = items_for(a, f.get('drop_topics', set()), f.get('drop_after'))
            drop_planks = {'League of Nations'} if 'platform_override' in f else frozenset()
            change = {'what_if': wk, 'facts': f['facts'], 'eligibility': f.get('eligibility'),
                      'dropped_sources': [i['id'] for i in ctl_items if i not in items], 'dropped_planks': sorted(drop_planks)}
            for model in (models if spec['mode'] == 'agents' else [ag.bulk_model]):
                reqs.append(request(f'cf:{wk}', model, f.get('eligibility') or elig, {'facts': f['facts']}, items,
                                    parties(drop_planks), labels, meta={'change': change}))
        # L2: the platform descriptions trade labels, and the display order flips.
        if n % 2 == 0 and 'R' in label_of and 'D' in label_of:
            swapped_labels = list(reversed(labels))
            swap_parties = parties(swap=True)
            reqs.append(request('swap', ag.bulk_model, elig, {}, ctl_items, list(reversed(swap_parties)), swapped_labels,
                                meta={'swap': True, 'displayed': [{'label': l, 'platform_of': {'R': 'D', 'D': 'R'}.get(p['key'], p['key'])}
                                                                  for l, p in zip(swapped_labels, reversed(swap_parties))]}))
        # L1: a separate instance, the same blinded brief, asked to identify.
        if n % 2 == 1:
            reqs.append(request('probe', ag.bulk_model, elig, {}, ctl_items, parties(), labels, system=prompts.PROBE_SYSTEM,
                                question=prompts.PROBE_QUESTION, schema=prompts.probe_schema(labels)))
    return agents, reqs


def agent_reached(a: dict, what_if: str) -> bool:
    if a['group'] == 'foreign_white_alien':
        return False  # can't vote in either world
    if what_if == 'no-19th':
        return a['sex'] == 'F' or a['group'] == 'native_white'  # women, plus native men as a cross-check
    if what_if == 'fifteenth':
        return a['state'] in SOUTH and a['group'] in ('black', 'native_white')
    return True
