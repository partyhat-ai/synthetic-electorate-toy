"""Builds every model request for a run (control, counterfactuals, label swap,
recall probe, second-model check) and reads the answers back.

Request id: <arm>|<agent id>|<model short>   arm ∈ control, cf:<what-if>, swap, probe
"""
from __future__ import annotations

import random

from . import prompts, scenario, world
from .agents import persona_lines, sample_agents
from .geo import SOUTH, STATE_NAME
from .whatifs import ELECTION_YEARS  # noqa: F401 (re-exported: the table of election years)

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


# ── Eras: what the five backbone slots mean, and how briefs and the page name them ──
#
# The backbone always has five groups per state × sex. Their meaning shifts:
#   early    1789–1864  white men (no nativity before 1850); Black adults free and enslaved;
#                       American Indians (rarely citizens)
#   classic  1868–1968  the 1920 meanings (native-born white, naturalized, alien, Black, other)
#   modern   1972–      native_white = white non-Hispanic US-born; foreign_white_naturalized =
#                       naturalized citizens of any race; foreign_white_alien = noncitizens;
#                       black = Black US-born; other = US-born Hispanic, Asian, American Indian
#                       and others
SLAVE_STATES = {'AL', 'AR', 'DE', 'FL', 'GA', 'KY', 'LA', 'MD', 'MS', 'MO', 'NC', 'SC', 'TN', 'TX', 'VA', 'DC'}
# [I] Modern 'other' (US-born, not white non-Hispanic, not Black): persona origin only, never counted.
OTHER_ORIGIN = {'Hispanic': 0.6, 'Asian American': 0.15, 'American Indian': 0.1, 'multiracial': 0.15}
# [I] Share of adults barred by a felony conviction (Uggen, Larson & Shannon / Sentencing Project
# national estimates, rounded; Black adults about 3.5×). Used only to decide a persona's line,
# never counted. A state table in franchise['felony_share'] replaces it.
FELONY_SHARE = {1972: 0.008, 1976: 0.008, 1980: 0.009, 1984: 0.010, 1988: 0.012, 1992: 0.014, 1996: 0.017,
                2000: 0.023, 2004: 0.024, 2008: 0.024, 2012: 0.025, 2016: 0.025, 2020: 0.023, 2024: 0.017}
NO_FELONY_BAN = {'ME', 'VT', 'DC'}


def era(year: int) -> str:
    return 'early' if year < 1868 else 'modern' if year >= 1972 else 'classic'


def groups_for(year: int = 1920) -> dict:
    """The one table of era meanings: persona words, cohort labels, page slice labels,
    which groups are interviewed, and the phrase prompts use for the groups."""
    from .agents import GROUP_WORDS
    from .cohorts import GROUP_LABEL
    from .serialize import SLICES
    e = era(year)
    if e == 'classic':
        return {'era': e, 'words': dict(GROUP_WORDS), 'labels': dict(GROUP_LABEL), 'slices': dict(SLICES),
                'interview': ['native_white', 'foreign_white_naturalized', 'foreign_white_alien', 'black'],
                'phrase': 'native-born white, naturalized immigrant, non-citizen immigrant and Black',
                'min_age': 21}
    if e == 'early':
        nativity = year >= 1850
        return {'era': e,
                'words': {'native_white': 'a white {noun} born in the United States' if nativity else 'a white {noun}',
                          'foreign_white_naturalized': 'a white {noun} born abroad and naturalized as a United States citizen',
                          'foreign_white_alien': 'a white {noun} born abroad who is not a United States citizen',
                          'black': 'a Black {noun}', 'other': 'an American Indian {noun}'},
                'labels': {'native_white': 'native-born white' if nativity else 'white',
                           'foreign_white_naturalized': 'naturalized immigrant', 'foreign_white_alien': 'immigrant non-citizen',
                           'black': 'Black (free and enslaved)', 'other': 'American Indian'},
                'slices': {**dict(SLICES), 'black-south': 'Black Southerners, most of them enslaved'},
                'interview': ['native_white', 'foreign_white_naturalized', 'foreign_white_alien', 'black'],
                'phrase': ('native-born white, naturalized immigrant, non-citizen immigrant and Black (free and enslaved)'
                           if nativity else 'white and Black (free and enslaved); there is no nativity before 1850'),
                'min_age': 21}
    return {'era': e,
            'words': {'native_white': 'a non-Hispanic white {noun} born in the United States',
                      'foreign_white_naturalized': 'a {noun} born abroad and naturalized as a United States citizen',
                      'foreign_white_alien': 'a {noun} born abroad who is not a United States citizen',
                      'black': 'a Black {noun} born in the United States',
                      'other': 'a {origin} {noun} born in the United States'},
            'labels': {'native_white': 'US-born non-Hispanic white', 'foreign_white_naturalized': 'naturalized citizen',
                       'foreign_white_alien': 'noncitizen', 'black': 'US-born Black',
                       'other': 'US-born Hispanic, Asian, American Indian and other'},
            'slices': {'men': 'Men outside the South (citizens)', 'women': 'Women outside the South (citizens)',
                       'south-white': 'White and other Southerners (citizens)', 'black-south': 'Black Southerners (US-born)',
                       'immigrants': 'Noncitizens'},
            'interview': ['native_white', 'foreign_white_naturalized', 'foreign_white_alien', 'black', 'other'],
            'phrase': ('US-born non-Hispanic white, naturalized citizens of any race, noncitizens, US-born Black, and '
                       'US-born Hispanic, Asian, American Indian and other'),
            'min_age': 18}


def _draw(agent: dict, what: str) -> float:
    return random.Random(f'{agent["id"]}:{what}').random()


def describe_agent(agent: dict, fr: dict, year: int, inp=None):
    """Era facts about one invented person that the cohort doesn't fix (status, origin).
    Classic years add nothing, so their agents and briefs are unchanged."""
    e = era(year)
    if e == 'early' and agent['group'] == 'black':
        es = (fr.get('enslaved_share') or getattr(inp, 'enslaved_share', None) or {}).get(agent['state'])
        if es is not None:
            agent['status'] = 'enslaved' if _draw(agent, 'enslaved') < es else 'free'
        else:
            agent['status'] = 'free' if agent['state'] not in SLAVE_STATES else 'unknown'
    if e == 'modern' and agent['group'] == 'other':
        u, acc = _draw(agent, 'origin'), 0.0
        for k, w in OTHER_ORIGIN.items():
            acc += w
            if u < acc:
                agent['origin'] = k
                break
        else:
            agent['origin'] = 'multiracial'
    return agent


def _felony(agent: dict, fr: dict, year: int) -> bool:
    if agent['state'] in NO_FELONY_BAN:
        return False
    tab = fr.get('felony_share') or {}
    p = tab.get(agent['state'])
    if p is None:
        p = FELONY_SHARE.get(year, FELONY_SHARE[min(FELONY_SHARE, key=lambda y: abs(y - year))])
        if agent['group'] == 'black':
            p *= 3.5
        if agent['sex'] == 'F':
            p *= 0.25
    return _draw(agent, 'felony') < p


def eligibility_line(agent: dict, fr: dict, year: int = 1920, inp=None) -> str:
    s, name = agent['state'], STATE_NAME.get(agent['state'], agent['state'])
    e = era(year)
    table = fr['table']
    poll = bool(table.loc[s].get('poll_tax', 0)) if s in table.index else False
    lit = bool(table.loc[s].get('literacy_test', 0)) if s in table.index else False
    if year < 1890:
        poll = lit = False  # the franchise table describes the disfranchisement era (data has no earlier devices)
    if year >= 1964:
        poll = False  # Twenty-fourth Amendment
    if year >= (1968 if s in SOUTH else 1972):
        lit = False  # Voting Rights Act (1965), nationwide ban (1970)
    alien_ok = fr.get('alien_voting', set()) if year < 1928 else set()
    no_popular = set(getattr(inp, 'no_popular', None) or fr.get('no_popular') or ())
    if s in no_popular:
        return f'The {name} legislature chooses the state\'s presidential electors, so no one in {name} votes for president this year.'
    if agent['group'] == 'foreign_white_alien' and s not in alien_ok:
        return 'This person is not a United States citizen and cannot vote.'
    if agent['sex'] == 'F' and s in fr.get('closed_1920', ()) and year == 1920:
        return f'Registration in {name} closed before women could enrol, so this person cannot vote for president this year.'
    if agent['group'] == 'other' and e != 'modern':
        oc = (getattr(inp, 'other_citizen', None) or {}).get(s, 1.0 if year >= 1924 else 0.0)
        if year < 1924 and _draw(agent, 'citizen') >= oc:
            return 'This person is not counted a United States citizen, and cannot vote.'
    if agent['sex'] == 'F' and year < 1920:
        wv = set(getattr(inp, 'women_vote', None) or ())
        pres = fr.get('pres_year', {})
        if not wv:
            wv = {x for x, y in pres.items() if y and y == y and int(y) <= year}
        if s not in wv:
            return f'Women cannot vote for president in {name}.'
    if e == 'early' and agent['group'] == 'black':
        if agent.get('status') == 'enslaved':
            return 'This person is enslaved and cannot vote.'
        bc = (getattr(inp, 'black_can', None) or {}).get(s)
        if bc is None:
            bc = 0.0 if s in SLAVE_STATES else 1.0
        es = (fr.get('enslaved_share') or getattr(inp, 'enslaved_share', None) or {}).get(s)
        free_can = min(1.0, bc / max(1e-9, 1 - es)) if es is not None and agent.get('status') == 'free' else bc
        if free_can <= 0:
            return f'{name} law does not let Black people vote.'
        if free_can < 1 and _draw(agent, 'legal') >= free_can:
            return f'{name} law lets few Black men vote (a property requirement, or the right to vote taken away), and this person cannot vote.'
    parts = []
    devices = ' and '.join(x for x, on in (('a poll tax', poll), ('a literacy or "understanding" test', lit)) if on)
    if agent['group'] == 'black' and s in SOUTH and 1868 <= year < 1972:
        if year <= 1876:
            return (f'This person is a citizen. Black men in {name} have registered and voted since 1867, though threats '
                    'and violence have kept many from the polls in some counties.')
        if year < 1890:
            return ('This person is a citizen and the law lets them vote, but in this county fraud, threats and violence '
                    'keep many Black men from the polls.')
        if year >= 1968:
            return (f'This person can vote. Since the Voting Rights Act of 1965, Black citizens in {name} register and vote '
                    'in growing numbers.')
        line = 'This person is a citizen.'
        if devices:
            line += f' {name} requires {devices} to register,'
        else:
            line += f' In {name}'
        return line + ' and in this county few Black citizens have been allowed to register or vote.'
    if e == 'early' and agent['group'] != 'black' and agent['sex'] == 'M':
        wc = (getattr(inp, 'white_can', None) or {}).get(s, 1.0)
        if wc < 1:
            if _draw(agent, 'legal') >= wc:
                return f'{name} lets only men who own property or pay taxes vote, and this person does not qualify, so cannot vote.'
            parts.append(f'{name} lets only men who own property or pay taxes vote; this person qualifies and can vote.')
    if e == 'modern' and _felony(agent, fr, year):
        return f'This person is a citizen, but a felony conviction bars them from voting under {name} law.'
    if parts:
        pass
    elif agent['sex'] == 'F' and year < 1920:
        y = fr.get('pres_year', {}).get(s)
        if y and y == y and int(y) <= year - 4:
            parts.append(f'Women have voted for president in {name} since {int(y)}.')
        elif y and y == y and int(y) <= year:
            parts.append(f'{name} law gave women the vote for president in {int(y)}, so this is the first presidential '
                         'election this person can vote in.')
        else:
            parts.append(f'{name} law lets women who meet its requirements vote, and this person can vote.')
    elif e == 'modern':
        if agent.get('age', 99) < 21:
            parts.append('Since the Twenty-sixth Amendment lowered the voting age to 18 in 1971, this person can vote.')
        else:
            parts.append('This person can vote.')
    elif agent['sex'] == 'F' and year > 1920:
        y = fr['pres_year'].get(s)
        since = int(y) if s in fr['women_pre19'] and y and y == y and int(y) <= 1920 else 1920
        parts.append(f'Women have voted for president in {name} since {since}.')
    elif agent['sex'] == 'F':
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
    prof = extras.get('profile') or {'year': 1920, 'descriptors': {'R': R_DESCRIPTOR, 'D': D_DESCRIPTOR}, 'third': None,
                                     'label_pool': prompts.LABEL_POOL, 'others_line': prompts.OTHERS_1920,
                                     'plank_order': ORDER_1920, 'day_phrase': 'Tuesday, 2 November'}
    # An unopposed year (1789, 1792, 1820) has no second line: its descriptor is null.
    keys = [k for k in ('R', 'D') if prof['descriptors'].get(k)] + ([prof['third']] if prof['third'] else [])
    year = prof['year']
    era_groups = groups_for(year)
    qs = prompts.questions(prof['day_phrase'])
    agents, reqs = [], []
    asof = cfg.context_cutoff  # p1 used '1920-10-30' with items to 1 Nov
    no_popular = set(getattr(inp, 'no_popular', None) or ())
    this_year = [wk for wk in cfg.what_ifs if wk in registry and registry[wk]['facts'] is not None
                 and year in (registry[wk].get('years') or [registry[wk].get('year', 1920)])]

    def draw(key: str) -> list[dict]:
        """The people interviewed in one cohort (none where no one can be)."""
        co = cohorts[key]
        if co['group'] not in era_groups['interview']:
            return []  # 1868–1968: too few adults per region for a cohort; counted by the backbone only
        if no_popular:
            # No one votes for president where the legislature chose the electors: nobody to interview there.
            by_state = {s: n for s, n in co['adults_by_state'].items() if s not in no_popular}
            if not by_state:
                return []
            co = {**co, 'adults_by_state': by_state}
        return sample_agents(co, ag.per_cohort, corpus, cfg.seed, extras['urban'], year=year, min_age=era_groups['min_age'])

    for key in sorted(cohorts):
        if not ag.only_cohorts or key in ag.only_cohorts:
            agents += draw(key)

    # D33: the groups a staged what-if names as decisive are interviewed for it even when
    # only_cohorts leaves them out. The focus_cohorts slots go round the named groups in turn
    # (newest what-if first; within a group, its largest cohort first), so every named group
    # is reached before any gets a second.
    if ag.focus_cohorts and ag.only_cohorts:
        queues = []
        for wk in reversed(this_year):
            for f in (registry[wk].get('world') or {}).get('focus') or []:
                queues.append((wk, sorted((k for k, c in cohorts.items() if k not in ag.only_cohorts
                                           and c['group'] != 'foreign_white_alien' and world.cohort_matches(c, f)),
                                          key=lambda k: -cohorts[k]['adults'])))
        chosen, drawn = {}, {}
        while len(chosen) < ag.focus_cohorts and any(q for _, q in queues):
            for wk, q in queues:
                while q and len(chosen) < ag.focus_cohorts:
                    k = q.pop(0)
                    if k in chosen:
                        chosen[k].add(wk)  # already named by another group: it counts for this what-if too
                        continue
                    if k not in drawn:
                        drawn[k] = draw(k)
                    if drawn[k]:
                        chosen[k] = {wk}
                        break
        for k, wks in chosen.items():
            for a in drawn[k]:
                a['focus_for'] = sorted(wks)
            agents += drawn[k]
    for n, a in enumerate(agents):
        rng = random.Random(f'{cfg.seed}:{a["id"]}')
        label_of, order = prompts.assign_labels(rng, keys, prof['label_pool'])
        labels = [label_of[p] for p in order]
        a['label_of'] = label_of
        a['paraphrase'] = n % ag.paraphrases
        describe_agent(a, fr, year, inp)
        elig = eligibility_line(a, fr, year, inp)
        a['eligibility'] = elig
        q = qs[a['paraphrase']]

        def parties(drop=frozenset(), swap=False, add=(), news=None):
            desc = dict(prof['descriptors'])
            plank = {p: party_planks(platforms, p, drop, order=prof['plank_order']) for p in keys}
            for x in add:  # a compiled what-if's added plank, after the party's own
                plank[x['party']] = plank[x['party']] + [x['text'].rstrip('.') + '.']
            if swap:
                plank = {**plank, 'R': plank['D'], 'D': plank['R']}
                desc = {**desc, 'R': desc['D'], 'D': desc['R']}
            return [{'key': p, 'descriptor': desc[p], 'planks': plank[p], **({'news': news[p]} if news and news.get(p) else {})}
                    for p in order]

        def request(arm, model, persona_elig, world, items, ballot_parties, disp_labels, system=prompts.SYSTEM,
                    question=q, schema=None, meta=None):
            text = prompts.brief({'lines': persona_lines(a, persona_elig, year)}, world, items,
                                 prompts.ballot_block(STATE_NAME.get(a['state'], a['state']), ballot_parties, disp_labels, prof['others_line'],
                                                     (prof.get('ballot_notes') or {}).get(a['state'])),
                                 asof, prof['day_phrase'])
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
            if spec['facts'] is None or year not in (spec.get('years') or [spec.get('year', 1920)]):
                continue
            if spec['mode'] == 'backbone' and not reached(spec, a, wk):
                continue
            if a['group'] == 'foreign_white_alien' and spec['mode'] == 'agents':
                continue  # can't vote in either world; no effect to measure
            if a.get('focus_for') and wk not in a['focus_for']:
                continue  # interviewed only for the what-if that named this group as decisive (D33)
            f = spec['facts'](a, inp, year=year)
            if not f['facts'] and f.get('eligibility') is None and not f.get('nominee_news'):
                continue
            items = items_for(a, f.get('drop_topics', set()), f.get('drop_after'))
            staged = f.get('world') or {}
            if f.get('drop_items'):
                items = [i for i in items if i['id'] not in f['drop_items']]  # D33: items the change makes false
            added = world.items_for_agent(staged, a, STATE_NAME.get(a['state'], a['state'])) if staged else []
            items = items + added
            drop_planks = set(f.get('drop_planks') or ()) or ({'League of Nations'} if 'platform_override' in f else frozenset())
            change = {'what_if': wk, 'facts': f['facts'], 'eligibility': f.get('eligibility'),
                      'dropped_sources': [i['id'] for i in ctl_items if i not in items], 'dropped_planks': sorted(drop_planks),
                      'added_planks': list(f.get('add_planks') or []),
                      **({'added_items': [{'id': i['id'], 'date': i['date'], 'text': i['text']} for i in added]} if added else {})}
            about = f.get('about') if f.get('about') in ('R', 'D') else None
            news = {about: f['nominee_news']} if about and f.get('nominee_news') else None
            ballot, cf_labels, extra = parties(drop_planks, add=f.get('add_planks') or (), news=news), labels, {}
            q_cf = q
            if news:
                # p5 manipulation check: whose news did the person take it to be?
                extra = {'news_check': {'expected': label_of[about], 'about': about}}
                q_cf = f'{q} {prompts.NEWS_CHECK}'
            if f.get('withdraws') and f['withdraws'] in label_of:
                # The third candidate leaves the race: his line comes off this ballot (labels and order otherwise kept).
                gone = label_of[f['withdraws']]
                ballot = [p for p in ballot if p['key'] != f['withdraws']]
                cf_labels = [l for l in labels if l != gone]
                extra = {**extra, 'withdrawn': {'label': gone, 'party': f['withdraws']}}
            cand = f.get('candidate')
            if cand:
                # p4: a third labelled line, after the two parties (their order and labels as in the control).
                third = scenario.third_label(random.Random(f'{cfg.seed}:{a["id"]}:{wk}'), labels, cand['name'], prof['label_pool'])
                line = f'{cand["name"]}, {cand["descriptor"].rstrip(".")}, running as an independent'
                ballot = ballot + [{'key': 'X', 'descriptor': line, 'planks': [p.rstrip('.') + '.' for p in cand['positions']]}]
                cf_labels = labels + [third]
                extra = {**extra, 'candidate': {'label': third, 'name': cand['name']}}
            for model in (models if spec['mode'] == 'agents' else [ag.bulk_model]):
                reqs.append(request(f'cf:{wk}', model, f.get('eligibility') or elig, {'facts': f['facts']}, items,
                                    ballot, cf_labels, question=q_cf,
                                    schema=prompts.answer_schema(cf_labels, news_check=True) if news else None,
                                    meta={'change': change, **extra}))
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
    if ag.arms:
        reqs = [r for r in reqs if r['meta']['kind'] in ag.arms]
    return agents, reqs


def reached(spec: dict, a: dict, what_if: str) -> bool:
    """Whether a backbone-mode what-if's cross-check interviews this person."""
    if spec.get('generated'):
        return scenario.agent_reached(spec, a)
    return agent_reached(a, what_if)


def agent_reached(a: dict, what_if: str) -> bool:
    if a['group'] == 'foreign_white_alien':
        return False  # can't vote in either world
    if what_if == 'no-19th':
        return a['sex'] == 'F' or a['group'] == 'native_white'  # women, plus native men as a cross-check
    if what_if == 'fifteenth':
        return a['state'] in SOUTH and a['group'] in ('black', 'native_white')
    return True
