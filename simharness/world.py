"""Staging a compiled what-if's world before the interviews (D33).

A once-per-what-if pass on the strongest model, at high effort. It runs once
per change rather than once per voter, so it costs little next to the
interviews, and it decides whether the interviews measure the change at all.

**Stage** (before the interviews). The compiler wrote the change as a few
   settled facts; staging makes the rest of the person's world agree with them:
   - `contradicted`: the year's dated newspaper items the change makes false
     (neutrality news in a world at war). They leave the counterfactual brief.
     This replaces the 1920-only topic codes (drop_topics) with item ids, so
     it works for every year that has a corpus.
   - `consequences`: up to three settled downstream facts any adult would know
     on the context date, aimed first at the real memory the change overturns
     (a model that knows 1916 "kept us out of war" needs telling it didn't).
   - `items`: two to four in-world dated news items (a casualty list, a draft
     notice), regional where the change is regional. Printed as "a local
     newspaper", never as a real masthead.
   - `check`: one multiple-choice question about the world (not the vote) that
     a person who took the change as true answers one way and a person in the
     world as it was answers the other.
   - `focus`: the groups whose votes the change most plausibly moves, from
     history: interviewed even when the config's only_cohorts leaves them out.

Nothing staged reaches a brief unmasked: names are masked like compiled
facts, and a sentence that still names a nominee or party is dropped.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re

from .scenario import REGION_KEYS, mask_names

WORLD_VERSION = 'w2'  # w2: the check asks a consequence the brief never states

WORLD_SYSTEM = """You are a historian staging a counterfactual for an election simulation. A change has been written into the world of the {year} United States presidential election as settled fact. Invented voters will be interviewed with a brief dated {cutoff}: their circumstances, a few dated newspaper items from that autumn, and the ballot. The simulation compares each person's answer in the world as it was with their answer in the changed world, so the changed world must hang together: nothing in a person's brief may contradict the change, and the change must be as present in daily life as it would really be.

The voices are language models that know the real history. Left alone they fall back on it: a voter told the country went to war in 1915 still says the President "kept us out of war". Your job is to close those gaps.

Fill the JSON:
- contradicted: every listed newspaper item whose content the change makes false, impossible or plainly out of place in the changed world (news of neutrality when the country is at war; a nominee's speech he could not have given). Give its id and a short why. Do not list an item only because it is irrelevant or would be crowded out of the news; a suit sale stays.
- consequences: up to three sentences of settled fact, true in the changed world on {cutoff}, that any adult would know and that follow directly from the change. Lead with the one that overturns the best-known real fact the change makes false (a slogan, a policy, an event everybody remembers). Plain, neutral wording of the period. Never phrase a hypothesis.
- items: two to four short dated news items (at most 60 words each) that a newspaper in the changed world would have printed in the ten weeks before {cutoff}: concrete, local and ordinary (a casualty list, a draft notice, a price, a meeting, a ruling), never a summary of the change. date: YYYY-MM-DD, on or before {cutoff}. regions: the regions where it is local news, from {regions}; empty for national news. kind: a few words ("casualty list").
- check: one multiple-choice question about the world, not about the election or any candidate, that a person who has taken the change in answers one way and a person in the world as it was answers another way. It tests whether the person reasons from the changed world, not whether they can read: ask about something that follows from the change but that neither the settled facts, your consequences nor your items state, so the answer can't be copied from the brief. A person who only half took the change in, and still carries the real world in their head, should get it wrong. (Change: the country went to war in 1915. Weak: "Is the country at war?", stated outright. Good: "Is there a draft for young men this year?") Three or four short options, none of them obviously absurd. expected: the option true in the changed world. control: the option true in the world as it was. They must differ. The question must not hint at the answer or at any party.
- focus: up to four groups whose votes the change most plausibly moves, from what historians know of how such people behaved: sex (M, F), group (from {groups}) and region (from {regions}); empty lists mean any. why: one sentence.

Never name {never_name}, and never write a party's name: call them {parties}. Write in the third person, never addressing the reader."""

def _schema(groups: list[str]) -> dict:
    reach = {'type': 'object', 'properties': {
        'sex': {'type': 'array', 'items': {'type': 'string', 'enum': ['M', 'F']}},
        'group': {'type': 'array', 'items': {'type': 'string', 'enum': groups}},
        'region': {'type': 'array', 'items': {'type': 'string', 'enum': REGION_KEYS}},
        'why': {'type': 'string'}}, 'required': ['sex', 'group', 'region', 'why'], 'additionalProperties': False}
    return {
        'type': 'object',
        'properties': {
            'contradicted': {'type': 'array', 'items': {'type': 'object', 'properties': {
                'id': {'type': 'string'}, 'why': {'type': 'string'}}, 'required': ['id', 'why'], 'additionalProperties': False}},
            'consequences': {'type': 'array', 'items': {'type': 'string'}},
            'items': {'type': 'array', 'items': {'type': 'object', 'properties': {
                'date': {'type': 'string'}, 'kind': {'type': 'string'},
                'regions': {'type': 'array', 'items': {'type': 'string', 'enum': REGION_KEYS}},
                'text': {'type': 'string'}}, 'required': ['date', 'kind', 'regions', 'text'], 'additionalProperties': False}},
            'check': {'type': 'object', 'properties': {
                'question': {'type': 'string'}, 'options': {'type': 'array', 'items': {'type': 'string'}},
                'expected': {'type': 'string'}, 'control': {'type': 'string'}},
                'required': ['question', 'options', 'expected', 'control'], 'additionalProperties': False},
            'focus': {'type': 'array', 'items': reach},
        },
        'required': ['contradicted', 'consequences', 'items', 'check', 'focus'],
        'additionalProperties': False,
    }


def _prof_bits(prof: dict) -> tuple[str, str]:
    from .scenario import party_names
    cd = prof.get('compile_desc') or {}
    names = party_names(prof)
    if names:
        parties = f'"{cd.get("R", "one party")}" ({names["R"]}) and "{cd.get("D", "the other")}" ({names["D"]})'
    else:
        parties = f'"{cd.get("R", "one party")}" (Republicans) and "{cd.get("D", "the other")}" (Democrats)'
    return prof.get('never_name') or 'any nominee', parties


def change_lines(spec: dict) -> list[str]:
    """The compiled change as the voters were told it."""
    out = [f'Label: {spec["label"]}. {spec.get("detail", "")}']
    out += [f'Settled fact: {f}' for f in spec.get('facts_text') or []]
    out += [f'News printed on a nominee\'s ballot line: {n}' for n in spec.get('nominee_news') or []]
    out += [f'Plank added ({p["party"]}): {p["text"]}' for p in spec.get('add_planks') or []]
    out += [f'Plank topic removed: {t}' for t in spec.get('drop_planks') or []]
    c = spec.get('candidate') or {}
    if c.get('name') and spec.get('kind') == 'candidate' and not spec.get('withdraws'):
        out.append(f'A third line on the ballot: {c["name"]}, {c.get("descriptor", "")}')
    if spec.get('withdraws'):
        out.append('The labelled third candidate has left the race.')
    return out


def stage_request(spec: dict, prof: dict, cutoff: str, corpus: list[dict], model: str, effort: str,
                  ev: dict | None = None) -> dict:
    from .agentlayer import groups_for
    year = prof['year']
    groups = groups_for(year)['interview']
    never, parties = _prof_bits(prof)
    system = WORLD_SYSTEM.format(year=year, cutoff=cutoff, regions=REGION_KEYS, groups=groups, never_name=never, parties=parties)
    lines = [f'Election: {year}, election day {prof.get("day_phrase", "")}. Context date: {cutoff}.', '',
             'The change, as written into the voters\' world:'] + [f'- {x}' for x in change_lines(spec)]
    if ev and ev.get('summary'):
        lines += ['', f'What historians found (for choosing the focus groups; never quote it): {ev["summary"]}']
        pops = sorted({json.dumps(f['population'], sort_keys=True) for f in ev.get('findings', []) if f.get('population')})
        if pops:
            lines.append('Populations the findings concern: ' + '; '.join(pops[:12]))
    items = [c for c in corpus if not c.get('identifying')]
    if items:
        lines += ['', f'The {len(items)} dated newspaper items voters may be shown (id, date, place: text):']
        lines += [f'[{c["id"]}] {c["date"]}, {c.get("place", c.get("state", ""))}: {c["text"]}' for c in items]
    else:
        lines += ['', f'No period newspaper items exist for {year}; contradicted is an empty list, and your items are the only news voters read.']
    user = '\n'.join(lines)
    return {'id': f'stage|{year}|{spec["key"]}|{hashlib.sha256(user.encode()).hexdigest()[:8]}', 'model': model, 'effort': effort,
            'system': system, 'user': user, 'schema': _schema(groups), 'meta': {'kind': 'stage', 'version': WORLD_VERSION}}


def _clean(text: str, year: int, names) -> str | None:
    t = ' '.join(mask_names(str(text), year).split())
    return None if not t or names.search(t) else t


def finalize(raw: dict, spec: dict, prof: dict, cutoff: str, corpus: list[dict], model: str, effort: str) -> dict:
    """A staging answer → spec['world'], checked: ids exist, dates fall on or before the
    cutoff, every sentence masked (a sentence that still names someone is dropped), and a
    check whose two worlds answer alike is discarded (it can't tell them apart)."""
    from .profiles import names_re
    year = prof['year']
    names = names_re(year)
    ids = {c['id'] for c in corpus if not c.get('identifying')}
    contradicted = [{'id': x['id'], 'why': x['why']} for x in raw.get('contradicted', []) if x.get('id') in ids]
    consequences = [t for t in (_clean(x, year, names) for x in raw.get('consequences', [])[:3]) if t]
    items = []
    for j, it in enumerate(raw.get('items', [])[:4]):
        text = _clean(it.get('text', ''), year, names)
        if not text:
            continue
        try:
            d = dt.date.fromisoformat(str(it.get('date', ''))[:10]).isoformat()
        except ValueError:
            d = cutoff
        items.append({'id': f'W{j + 1}', 'date': min(d, cutoff), 'kind': it.get('kind', ''),
                      'regions': [r for r in it.get('regions', []) if r in REGION_KEYS], 'text': ' '.join(text.split()[:70])})
    check = None
    c = raw.get('check') or {}
    opts = [o.strip() for o in c.get('options', []) if str(o).strip()][:4]
    q = _clean(c.get('question', ''), year, names)
    if q and len(opts) >= 2 and c.get('expected') in opts and c.get('control') in opts and c['expected'] != c['control'] \
            and not any(names.search(o) for o in opts):
        check = {'question': q, 'options': opts, 'expected': c['expected'], 'control': c['control']}
    focus = [{k: f.get(k, []) for k in ('sex', 'group', 'region')} | {'why': f.get('why', '')} for f in raw.get('focus', [])[:4]]
    return {'version': WORLD_VERSION, 'contradicted': contradicted, 'consequences': consequences, 'items': items,
            'check': check, 'focus': focus, 'model': model, 'effort': effort,
            'staged_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}


def items_for_agent(world: dict, agent: dict, state_name: str, k: int = 2) -> list[dict]:
    """The staged items an agent reads: local ones for their region first, then national."""
    region = 'south' if agent.get('region') == 'south' else agent.get('region')
    local = [i for i in world.get('items', []) if i['regions'] and region in i['regions']]
    national = [i for i in world.get('items', []) if not i['regions']]
    return [{'id': i['id'], 'newspaper': 'A local newspaper', 'place': state_name, 'date': i['date'], 'text': i['text'],
             'topic': 'staged', 'identifying': False, 'staged': True} for i in (local + national)[:k]]


def cohort_matches(cohort: dict, f: dict) -> bool:
    """Whether a cohort falls in one focus entry (empty lists match anyone)."""
    if f.get('sex') and cohort['sex'] not in f['sex']:
        return False
    if f.get('group') and cohort['group'] not in f['group']:
        return False
    return not (f.get('region') and not set(cohort.get('regions') or [cohort.get('region')]) & set(f['region']))


BARRED = re.compile(r'cannot vote|bars them from voting|no one in .* votes for president', re.I)


def barred(eligibility_line: str | None) -> bool:
    """Whether a brief's eligibility line says this person can't vote for president."""
    return bool(eligibility_line and BARRED.search(eligibility_line))
