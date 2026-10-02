"""Any typed what-if → a what-if the pipeline can run.

`compile_text` asks the model to turn a reader's words into a structured
change of one of five kinds, each with generic mechanics:

- franchise   backbone only: bar a group, enfranchise it (it turns out and
              chooses like a named observed group), or give it another
              group's turnout.
- population  backbone only: scale a group's adults (no reapportionment).
- issue       agents: settled facts in every reached person's brief, dated
- event       topics and platform planks the change contradicts removed.
- candidate   agents: a third labelled line on the ballot for a named
              person, with neutral dated positions; the third choice counts
              in O (other), and publish applies the effect there.

A compiled what-if is written to `harness/whatifs/<key>.json` (the spec,
exploratory) with its evidence in
`harness/whatifs/evidence/<key>.json`. Both are hashed into a run's id.
`load_generated` merges the specs into `whatifs.REGISTRY` at import.

Nothing a compiler writes reaches a brief unchecked: facts that name a
nominee or party (data.NAMES) are sent back once for rewording, then
masked.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path

import numpy as np

from .aggregate import World
from .config import ROOT
from .geo import REGIONS, SOUTH

WHATIFS_DIR = ROOT / 'whatifs'
EVIDENCE_DIR = WHATIFS_DIR / 'evidence'
COMPILER_VERSION = 'c4'  # c4: as asked, never a silent substitute (D34)  # c3: about + nominee_news (D21)  # c2: drop_topics only for contradicted topics (DISCLOSURES D17)

KINDS = ['franchise', 'population', 'issue', 'event', 'candidate']
GROUPS = ['native_white', 'foreign_white_naturalized', 'foreign_white_alien', 'black']
REGION_KEYS = ['northeast', 'midwest', 'south', 'border', 'west']
TOPICS = {
    'T1': 'women registering or voting for the first time', 'T2': 'the League of Nations and the peace treaty',
    'T3': 'cost of living, prices, wages, strikes, farm prices', 'T4': 'Prohibition in the campaign',
    'T5': 'Black citizens registering or kept from registering', 'T6': 'immigrant and ethnic grievances (Irish, German, Italian)',
    'T7': 'whether Georgia and Mississippi women could register in time', 'T8': 'Western states where women already voted',
}
PLANK_TOPICS = ['League of Nations', 'cost of living', 'labor', 'agriculture', 'women', 'immigration', 'Prohibition']
R_DESC = 'the party that has held a majority in Congress since the 1918 elections'
D_DESC = 'the party of the administration in office since 1913'

COMPILE_SYSTEM = f"""You turn a reader's what-if about the 1920 United States presidential election into a change a simulation can model.

The simulation has two layers. A calibrated backbone knows, for every state, how many adults of each census group (men and women; native-born white, naturalized immigrant, non-citizen immigrant and Black; plus region) could vote, turned out, and chose each candidate in 1920. Invented voters are interviewed with a brief dated on the context date: their circumstances, a few dated newspaper items, and the ballot. The two major nominees are blinded in those briefs: never name them or their parties.

Kinds of change:
- franchise: who may vote (bar a group, enfranchise one, or change a group's turnout). Say whose observed behaviour the newly able borrow.
- population: how many adults of a group live in the country (scale).
- issue: a policy question settled or changed, or another year's issue in the campaign.
- event: something that happened or didn't: a scandal, war, strike, economic shock, a person acting differently.
- candidate: a named person on the ballot as an independent or third-party candidate.

Model what the reader asked, as they asked it. If their words describe something that could not have happened by the context date (it needs events that in reality came later, or a different course of history), never swap in a nearer or more plausible change. Write the world in which it did happen by the context date: state as settled fact the earlier departures from history it requires (a war entered sooner and lost sooner, a law passed years early), and grade it "a-stretch" or "fantastical". Choose another reading only when the words genuinely allow several, and then the one closest to them.

Write:
- fidelity: "as-asked" when the change you model is the one the reader's words describe; "reinterpreted" when it is a different change (another reading, a narrower or a substitute change). reinterpretation: when reinterpreted, one sentence the reader sees first, saying what they asked, what is modelled instead, and why; otherwise "".
- withdraws: "O" when the change is that the labelled third candidate on this year's ballot (if there is one) does not run or withdraws; otherwise "none". Then kind is "candidate", and facts say when and how he left the race, without naming him.
- about: "R" or "D" when the change concerns one of the two major nominees personally (something he did, said, revealed or suffered); otherwise "none".
- nominee_news (only when about is R or D): one or two sentences of recent news about that nominee, in the third person ("He announced…", "Editors have denounced him…"), never naming him or his party. They are printed on his own line of the ballot, so no reader has to work out whom they concern. Then facts carry only the wider world, and never refer to the nominee again; facts may be empty.
- facts: one to three sentences stating the change as settled fact in the world on the context date, dated on or before it, in plain, neutral wording of the period. Never phrase it as a hypothesis ("what if", "imagine", "suppose", "would have"). Never name Harding, Cox, Coolidge, Franklin Roosevelt, Debs, Christensen or Wilson, and never write "Republican", "Democrat", "Democratic" or "G.O.P.". Call the Republicans "{R_DESC}" and the Democrats "{D_DESC}"; call Wilson "the President".
- candidate (kind candidate only): the person's name as known in 1920; descriptor: a neutral one-line identity on the context date; positions: up to three neutral, dated paraphrases of stances the person actually held or voiced by the context date (positions_source "documented"), or plausible ones when nothing is on record (positions_source "inferred"). Each position is a plain statement of the stance as voters would read it on the ballot, with no notes, brackets, hedges or "would likely". Never quote a real person or put words in their mouth. eligibility_note: if the Constitution would bar the person from the office (under 35, not a natural-born citizen, fewer than 14 years resident), say so in one sentence; otherwise "".
- reach: the sexes, groups and regions the change touches directly. Empty lists mean everyone.
- drop_topics: dated newspaper topics the settled facts would make false, from: {json.dumps(TOPICS)}. Only those: never drop a topic because the change would crowd it out of the news. Usually this list is empty.
- drop_planks: platform plank topics the change would remove, from {PLANK_TOPICS}. add_planks: a plank a party would add, in a neutral paraphrase.
- plausibility: "documented" (it nearly happened, or it did in some form), "within-reach" (plausible in 1920), "a-stretch" (possible only with large changes), "fantastical" (impossible in 1920). anachronism: true if it needs things that didn't exist in 1920; say what in anachronism_note.
- label: a Title Case name of three to six words, naming the change you model. detail: one sentence a reader sees. assumption: the modelling assumption, plainly.
- words: three to eight lowercase words or phrases a reader might type for this change.
- research_questions: two to four questions a historian could answer about how these people behaved in the same or the most similar situation.
- same_as: the key of an existing what-if if the reader asked for exactly that change in other words; otherwise "".
- modelable: false only if the text isn't a change to the 1920 election at all, or asks for something hateful or harmful; then give why_not. A fantastical change is still modelable: it will be flagged as extremely low confidence."""

GROUPS_PHRASE = 'native-born white, naturalized immigrant, non-citizen immigrant and Black'


def party_names(prof: dict) -> dict | None:
    """What people called the parties in slots R and D before 1856 (a profile's
    'party_names' wins); None from 1856, when they are the Republicans and Democrats."""
    if prof.get('party_names'):
        return prof['party_names']
    y = prof.get('year', 1920)
    if y >= 1856:
        return None
    if y <= 1792:
        return {'R': 'Federalists', 'D': 'Anti-Federalists'}
    if y <= 1820:
        return {'R': 'Federalists', 'D': 'Republicans'}
    if y == 1824:
        return {'R': 'Adams faction', 'D': 'Jackson faction'}
    if y <= 1832:
        return {'R': 'National Republicans', 'D': 'Democrats'}
    return {'R': 'Whigs', 'D': 'Democrats'}


def third_phrase(prof: dict) -> str:
    """How compiled text and masks call the labelled third candidate: compile_desc['O'],
    else 1924's wording, else "the " + the profile's ballot descriptor."""
    cd = prof.get('compile_desc') or {}
    if cd.get('O'):
        return cd['O']
    if prof.get('year') == 1924:
        return 'the independent Progressive candidate'
    d = (prof.get('descriptors') or {}).get('O')
    return f'the {re.split(r"[;:]|, an? ", d)[0].rstrip(".")}' if d else 'the third candidate'


def compile_system(prof: dict | None = None) -> str:
    """COMPILE_SYSTEM (1920) with another year's names, descriptors, groups, topics and planks.
    1924's text is exactly what it was when its compiled what-ifs were cached."""
    if not prof or prof['year'] == 1920:
        return COMPILE_SYSTEM
    from .agentlayer import groups_for
    y, cd = str(prof['year']), prof['compile_desc']
    s = COMPILE_SYSTEM.replace('1920', y)
    s = s.replace(GROUPS_PHRASE, groups_for(prof['year'])['phrase'])
    s = s.replace('Harding, Cox, Coolidge, Franklin Roosevelt, Debs, Christensen or Wilson', prof['never_name'])
    parties = party_names(prof)  # e.g. {"R": "Whigs", "D": "Democrats"} before 1856; None from 1856
    if parties:
        s = s.replace('never write "Republican", "Democrat", "Democratic" or "G.O.P.". Call the Republicans',
                      f'never write a party\'s name ({", ".join(chr(34) + v + chr(34) for v in parties.values())}). '
                      f'Call the {parties["R"]}').replace('and the Democrats "', f'and the {parties["D"]} "')
    s = s.replace(R_DESC, cd['R']).replace(D_DESC, cd['D']).replace('call Wilson "the President"', f'call {cd["president"]} "the President"')
    if prof.get('third'):
        third = third_phrase(prof)
        s = s.replace('call ' + cd['president'] + ' "the President".',
                      f'call {cd["president"]} "the President"; call {prof["names"]["O"]} "{third}".')
    s = s.replace(json.dumps(TOPICS), '[] (this year has no dated newspaper items: always an empty list)')
    return s.replace(str(PLANK_TOPICS), str(prof['plank_order']))


def compile_schema(prof: dict | None = None) -> dict:
    if not prof or prof['year'] == 1920:
        return COMPILE_SCHEMA
    s = json.loads(json.dumps(COMPILE_SCHEMA))
    s['properties']['drop_topics']['items']['enum'] = ['none']
    s['properties']['drop_planks']['items']['enum'] = list(prof['plank_order'])
    if prof['year'] >= 1972:  # 'other' (US-born Hispanic, Asian, American Indian…) is interviewed and reachable
        for r in (s['properties']['reach'], s['properties']['franchise']['properties']['borrow']):
            r['properties']['group']['items']['enum'] = GROUPS + ['other']
    return s


REACH = {'type': 'object', 'properties': {
    'sex': {'type': 'array', 'items': {'type': 'string', 'enum': ['M', 'F']}},
    'group': {'type': 'array', 'items': {'type': 'string', 'enum': GROUPS}},
    'region': {'type': 'array', 'items': {'type': 'string', 'enum': REGION_KEYS}},
}, 'required': ['sex', 'group', 'region'], 'additionalProperties': False}

COMPILE_SCHEMA = {
    'type': 'object',
    'properties': {
        'modelable': {'type': 'boolean'}, 'why_not': {'type': 'string'}, 'same_as': {'type': 'string'},
        'fidelity': {'type': 'string', 'enum': ['as-asked', 'reinterpreted']}, 'reinterpretation': {'type': 'string'},
        'kind': {'type': 'string', 'enum': KINDS},
        'about': {'type': 'string', 'enum': ['R', 'D', 'none']},
        'withdraws': {'type': 'string', 'enum': ['O', 'none']},
        'nominee_news': {'type': 'array', 'items': {'type': 'string'}},
        'label': {'type': 'string'}, 'detail': {'type': 'string'}, 'assumption': {'type': 'string'},
        'plausibility': {'type': 'string', 'enum': ['documented', 'within-reach', 'a-stretch', 'fantastical']},
        'anachronism': {'type': 'boolean'}, 'anachronism_note': {'type': 'string'},
        'facts': {'type': 'array', 'items': {'type': 'string'}},
        'reach': REACH,
        'drop_topics': {'type': 'array', 'items': {'type': 'string', 'enum': list(TOPICS)}},
        'drop_planks': {'type': 'array', 'items': {'type': 'string', 'enum': PLANK_TOPICS}},
        'add_planks': {'type': 'array', 'items': {'type': 'object', 'properties': {
            'party': {'type': 'string', 'enum': ['R', 'D']}, 'text': {'type': 'string'}},
            'required': ['party', 'text'], 'additionalProperties': False}},
        'candidate': {'type': 'object', 'properties': {
            'name': {'type': 'string'}, 'descriptor': {'type': 'string'},
            'positions': {'type': 'array', 'items': {'type': 'string'}},
            'positions_source': {'type': 'string', 'enum': ['documented', 'inferred', 'none']},
            'eligibility_note': {'type': 'string'}},
            'required': ['name', 'descriptor', 'positions', 'positions_source', 'eligibility_note'], 'additionalProperties': False},
        'franchise': {'type': 'object', 'properties': {
            'action': {'type': 'string', 'enum': ['none', 'bar', 'enfranchise', 'turnout']},
            'borrow': REACH},
            'required': ['action', 'borrow'], 'additionalProperties': False},
        'population_scale': {'type': 'number'},
        'words': {'type': 'array', 'items': {'type': 'string'}},
        'research_questions': {'type': 'array', 'items': {'type': 'string'}},
    },
    'required': ['modelable', 'why_not', 'same_as', 'fidelity', 'reinterpretation', 'kind', 'about', 'withdraws', 'nominee_news', 'label', 'detail', 'assumption', 'plausibility', 'anachronism',
                 'anachronism_note', 'facts', 'reach', 'drop_topics', 'drop_planks', 'add_planks', 'candidate', 'franchise',
                 'population_scale', 'words', 'research_questions'],
    'additionalProperties': False,
}


def compile_request(text: str, registry: dict, cutoff: str, model: str, retry_note: str | None = None, prof: dict | None = None) -> dict:
    year = prof['year'] if prof else 1920
    existing = '\n'.join(f'- {k}: {v["label"]}. {v["detail"]}' for k, v in registry.items() if year in (v.get('years') or [v.get('year', 1920)]))
    day = prof['day_phrase'] if prof else 'Tuesday, 2 November'
    user = f'Context date: {cutoff}. Election day: {day} {year}.\n\nExisting what-ifs:\n{existing}\n\nThe reader typed: "{text}"'
    if retry_note:
        user += f'\n\n{retry_note}'
    return {'id': f'compile|{year}|{hashlib.sha256(text.encode()).hexdigest()[:10]}', 'model': model, 'system': compile_system(prof),
            'user': user, 'schema': compile_schema(prof), 'meta': {'kind': 'compile', 'compiler_version': COMPILER_VERSION, 'year': year}}


def naming_violations(spec: dict, year: int = 1920) -> list[str]:
    from .profiles import names_re
    NAMES = names_re(year)
    texts = list(spec.get('facts', [])) + list(spec.get('nominee_news', [])) + [p['text'] for p in spec.get('add_planks', [])]
    c = spec.get('candidate') or {}
    texts += [c.get('descriptor', '')] + list(c.get('positions', []))
    return [t for t in texts if NAMES.search(t)]


MASKS = {
    1920: ((r'\bPresident Wilson\b|\bWilson\b', 'the President'), (r'\bG\.\s?O\.\s?P\.?', 'the congressional majority party'),
           (r'\bRepublicans?\b', 'the congressional majority party'), (r'\bDemocrat(?:s|ic)?\b', 'the administration party'),
           (r'\bHarding\b', 'the majority party\'s nominee'), (r'\bCox\b', 'the administration party\'s nominee'),
           (r'\b(?:Coolidge|Roosevelt|Debs|Christensen)\b', 'a nominee')),
    1924: ((r'\bPresident Coolidge\b|\bCoolidge\b', 'the President'), (r'\bLa ?Follette\b', 'the independent Progressive candidate'),
           (r'\bG\.\s?O\.\s?P\.?', 'the administration party'), (r'\bRepublicans?\b', 'the administration party'),
           (r'\bDemocrat(?:s|ic)?\b', 'the party out of power'), (r'\bDavis\b', 'the nominee of the party out of power'),
           (r'\bHarding\b', 'the late President'), (r'\bWilson\b', 'the former President'),
           (r'\b(?:Dawes|Bryan|Wheeler)\b', 'a running mate')),
}


def auto_masks(prof: dict) -> tuple:
    """Masks from a profile's names when it lists none: the President, each nominee's
    names, the third candidate, and the two parties by their descriptions."""
    cd, out = prof.get('compile_desc') or {}, []
    pres = cd.get('president')
    if pres:
        out.append((rf'\bPresident {re.escape(pres)}\b|\b{re.escape(pres)}\b', 'the President'))
    for k, rep in (('R', f"the nominee of {cd.get('R', 'one party')}"), ('D', f"the nominee of {cd.get('D', 'the other party')}"),
                   ('O', third_phrase(prof))):
        names = {n for n in (prof.get('names', {}).get(k), prof.get('full_names', {}).get(k)) if n and n != 'another candidate'}
        names |= {n.split()[-1] for n in names}
        if names:
            out.append((r'\b(?:' + '|'.join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + r')\b', rep))
    parties = party_names(prof) or {'R': 'Republicans', 'D': 'Democrats'}
    if parties.get('R') and cd.get('R'):
        out.append((r'\bG\.\s?O\.\s?P\.?', cd['R']))
        out.append((rf'\b{re.escape(parties["R"].rstrip("s"))}s?\b', cd['R']))
    if parties.get('D') and cd.get('D'):
        out.append((rf'\b{re.escape(parties["D"].rstrip("s"))}(?:s|ic)?\b', cd['D']))
    return tuple(out)


def mask_names(text: str, year: int = 1920) -> str:
    if year in MASKS:
        masks = MASKS[year]
    else:
        from . import profiles
        masks = profiles.get(year).get('masks') or auto_masks(profiles.get(year))
    for pat, rep in masks:
        text = re.sub(pat, rep, text)
    # "the Republicans" → "the the administration party": keep one article.
    return re.sub(r'\b([Tt]he) the\b', r'\1', text)


ANNOTATION = re.compile(r'\s*\((?:documented|inferred|source|note)[^)]*\)', re.I)


def clean_position(text: str, year: int = 1920) -> str:
    """A ballot position as voters read it: names masked, modelling notes stripped."""
    return ANNOTATION.sub('', mask_names(text, year)).strip()


def _third(year: int) -> bool:
    from . import profiles
    try:
        return bool(profiles.get(year).get('third'))
    except SystemExit:
        return year != 1920


def finalize(raw: dict, text: str, registry: dict, model: str, year: int = 1920) -> dict:
    """Compiled answer → a registry-shaped spec (JSON-safe; `apply`/`facts` are bound at load)."""
    from .evidence import slug
    kind = raw['kind']
    base = slug(raw['candidate']['name'] + ' runs') if kind == 'candidate' and raw['candidate']['name'] else slug(raw['label'])
    key, n = base, 2
    while key in registry:
        key, n = f'{base}-{n}', n + 1
    reach = {k: v for k, v in raw['reach'].items() if v}
    mode = 'backbone' if kind in ('franchise', 'population') else 'agents'
    spec = {
        'key': key, 'label': raw['label'], 'kind': 'issue' if kind == 'event' else kind, 'subkind': kind, 'mode': mode,
        'detail': raw['detail'], 'assumption': raw['assumption'], 'plausibility': raw['plausibility'],
        'anachronism': raw['anachronism'], 'anachronism_note': raw['anachronism_note'],
        'year': year, 'years': [year],
        'withdraws': 'O' if raw.get('withdraws') == 'O' and _third(year) else None,
        'facts_text': [mask_names(f, year) for f in raw['facts']], 'reach': reach,
        'about': raw.get('about') if raw.get('about') in ('R', 'D') else None,
        'nominee_news': [mask_names(n, year) for n in raw.get('nominee_news', [])] if raw.get('about') in ('R', 'D') else [],
        'drop_topics': [t for t in raw['drop_topics'] if t in TOPICS] if year == 1920 else [], 'drop_planks': raw['drop_planks'],
        'add_planks': [p | {'text': mask_names(p['text'], year)} for p in raw['add_planks']],
        'candidate': (raw['candidate'] | {'descriptor': mask_names(raw['candidate']['descriptor'], year),
                                          'positions': [clean_position(p, year) for p in raw['candidate']['positions']][:3]})
        if kind == 'candidate' else None,
        'franchise': raw['franchise'] if kind == 'franchise' else None,
        'population_scale': raw['population_scale'] if kind == 'population' else None,
        # D34: a reinterpreted change never claims the reader's own words, so typing them again
        # reaches the compiler instead of being served the substitute.
        'fidelity': raw.get('fidelity', 'as-asked'),
        'reinterpretation': (raw.get('reinterpretation') or '') if raw.get('fidelity') == 'reinterpreted' else '',  # reader-facing: unmasked
        'words': sorted({w.lower().strip() for w in raw['words'] if len(w.strip()) >= 3
                         and not (raw.get('fidelity') == 'reinterpreted' and _same_words(w, text))}),
        'research_questions': raw['research_questions'],
        'slices': slices_reached(reach),
        'borrowed': describe_reach(raw['franchise']['borrow'], year) if kind == 'franchise' and raw['franchise']['action'] == 'enfranchise' else None,
        'source_text': text, 'generated': True, 'exploratory': True, 'evidence_mode': 'blend',
        'compiled': {'model': model, 'version': COMPILER_VERSION, 'at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')},
    }
    return spec


def _same_words(a: str, b: str) -> bool:
    norm = lambda t: ' '.join(re.sub(r'[^a-z0-9 ]', ' ', t.lower()).split())
    return norm(a) == norm(b) or norm(a) in norm(b)


def slices_reached(reach: dict) -> list[str]:
    out = []
    sex, grp, reg = reach.get('sex') or ['M', 'F'], reach.get('group') or GROUPS, reach.get('region') or REGION_KEYS
    nonsouth = any(r != 'south' for r in reg)
    if 'foreign_white_alien' in grp:
        out.append('immigrants')
    citizen = [g for g in grp if g != 'foreign_white_alien']
    if citizen and nonsouth:
        out += [s for s, x in (('men', 'M'), ('women', 'F')) if x in sex]
    if 'south' in reg and any(g != 'black' for g in citizen):
        out.append('south-white')
    if 'south' in reg and 'black' in grp:
        out.append('black-south')
    return out


def describe_reach(r: dict, year: int = 1920) -> str:
    from .cohorts import GROUP_LABEL, SEX_LABEL
    labels = GROUP_LABEL
    if not 1868 <= year < 1972:
        from .agentlayer import groups_for
        labels = groups_for(year)['labels']
    g = ' and '.join(labels[x] for x in r.get('group', [])) or 'all'
    s = ' and '.join(SEX_LABEL[x] for x in r.get('sex', [])) or 'adults'
    where = f' in the {", ".join(r["region"])}' if r.get('region') else ''
    return f'{g} {s}{where}'


# ── Mechanics ──

def cell_mask(cells, reach: dict) -> np.ndarray:
    m = np.ones(len(cells), bool)
    if reach.get('sex'):
        m &= cells.sex.isin(reach['sex']).to_numpy()
    if reach.get('group'):
        m &= cells.group.isin(reach['group']).to_numpy()
    if reach.get('region'):
        states = [s for r in reach['region'] for s in REGIONS.get(r, [])]
        m &= cells.state.isin(states).to_numpy()
    if reach.get('state'):
        m &= cells.state.isin(reach['state']).to_numpy()
    return m


def _borrowed(world: World, m: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """[D] turnout and [D, 3] shares of the borrowed group, vote-weighted."""
    can_vote = world.adults[:, m] * world.can[:, m]
    t = (can_vote * world.t[:, m]).sum(axis=1) / np.maximum(can_vote.sum(axis=1), 1e-9)
    v = can_vote * world.t[:, m]
    share = (v[..., None] * world.share[:, m, :]).sum(axis=1) / np.maximum(v.sum(axis=1), 1e-9)[:, None]
    return t, share


def make_apply(spec: dict):
    reach = spec.get('reach') or {}

    def franchise(fit, world: World, inp) -> World:
        w = world.copy()
        m = cell_mask(fit.cells, reach)
        f = spec['franchise'] or {'action': 'none'}
        share = float(np.clip(f.get('share') or 1.0, 0.0, 1.0))
        if f['action'] == 'bar' and share < 1.0:
            # Part of every reached cell (an age band the cells don't split: 18–20 of 18+),
            # barred with the cell's own behaviour [I].
            w.barred_by['legal'][:, m] += share * world.can[:, m]
            w.can[:, m] *= (1.0 - share)
            return w
        if f['action'] == 'enfranchise' and f.get('reason') == 'felony':
            # Lift only the felony bar (Inputs.black_can / white_can for 1972+): the newly
            # eligible vote like the rest of their cell [I].
            c = fit.cells
            for i in np.flatnonzero(m):
                if c.group.iloc[i] == 'foreign_white_alien':
                    continue
                st = c.state.iloc[i]
                fel = (inp.black_can if c.group.iloc[i] == 'black' else inp.white_can).get(st, 1.0)
                if fel < 1.0:
                    new = np.minimum(1.0, world.can[:, i] / fel)
                    w.barred_by['legal'][:, i] = np.maximum(0.0, w.barred_by['legal'][:, i] - (new - world.can[:, i]))
                    w.can[:, i] = new
            return w
        if f['action'] == 'bar':
            w.barred_by['legal'][:, m] = 1.0
            for k in w.barred_by:
                if k != 'legal':
                    w.barred_by[k][:, m] = 0.0
            w.can[:, m] = 0.0
            return w
        b = cell_mask(fit.cells, f.get('borrow') or {})
        if not b.any():
            b = ~m
        t_b, share_b = _borrowed(world, b)
        if f['action'] == 'enfranchise':
            w.can[:, m] = 1.0
            for k in w.barred_by:
                w.barred_by[k][:, m] = 0.0
            w.t[:, m] = t_b[:, None]
            w.share[:, m, :] = share_b[:, None, :]
        elif f['action'] == 'turnout':
            w.t[:, m] = t_b[:, None]
        return w

    def population(fit, world: World, inp) -> World:
        w = world.copy()
        m = cell_mask(fit.cells, reach)
        w.adults[:, m] *= float(np.clip(spec.get('population_scale') or 1.0, 0.0, 5.0))
        return w

    return franchise if spec['kind'] == 'franchise' else population if spec['kind'] == 'population' else None


def make_facts(spec: dict):
    reach = spec.get('reach') or {}

    def facts(agent: dict, inp, year: int = 1920) -> dict:
        # A staged world (world.py) adds its consequences to the settled facts and drops,
        # by id, the dated items the change makes false.
        world = spec.get('world') or {}
        out = {'facts': list(spec.get('facts_text') or []) + list(world.get('consequences') or []), 'eligibility': None,
               'drop_items': {c['id'] for c in world.get('contradicted') or []}, 'world': world or None,
               'about': spec.get('about'), 'nominee_news': list(spec.get('nominee_news') or []),
               'withdraws': spec.get('withdraws'),
               'drop_topics': set(spec.get('drop_topics') or []), 'drop_planks': set(spec.get('drop_planks') or []),
               'add_planks': spec.get('add_planks') or []}
        if spec['kind'] == 'candidate' and spec.get('candidate') and not spec.get('withdraws'):
            out['candidate'] = spec['candidate']
        if spec['kind'] == 'franchise' and agent_reached(spec, agent):
            f = spec.get('franchise') or {}
            if float(f.get('share') or 1.0) < 1.0 or f.get('reason'):
                pass  # a slice of each cell (an age band, people with felony records): most agents unaffected
            elif f.get('action') == 'bar':
                out['eligibility'] = 'This person cannot vote for president this year.'
            elif f.get('action') == 'enfranchise':
                out['eligibility'] = 'This person is registered and can vote this year.'
        return out
    return facts


def agent_reached(spec: dict, a: dict) -> bool:
    reach = spec.get('reach') or {}
    if reach.get('sex') and a['sex'] not in reach['sex']:
        return False
    if reach.get('group') and a['group'] not in reach['group']:
        return False
    if reach.get('region'):
        region = 'south' if a['state'] in SOUTH else a['region']
        if region not in reach['region']:
            return False
    if reach.get('state') and a['state'] not in reach['state']:
        return False
    return True


# ── Storage ──

def spec_path(key: str) -> Path:
    return WHATIFS_DIR / f'{key}.json'


def evidence_path(key: str) -> Path:
    return EVIDENCE_DIR / f'{key}.json'


def save_spec(spec: dict):
    WHATIFS_DIR.mkdir(exist_ok=True)
    spec_path(spec['key']).write_text(json.dumps(spec, indent=1))


def load_evidence(key: str) -> dict | None:
    p = evidence_path(key)
    return json.loads(p.read_text()) if p.exists() else None


def save_evidence(key: str, ev: dict):
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    evidence_path(key).write_text(json.dumps(ev, indent=1, default=float))


WORDS_FILE = WHATIFS_DIR / 'words.json'


def extra_words() -> dict:
    """Keywords learned from typed requests that meant an existing what-if (the cheapest fix: republish only)."""
    return json.loads(WORDS_FILE.read_text()) if WORDS_FILE.exists() else {}


def add_words(key: str, words: list[str]):
    cur = extra_words()
    cur[key] = sorted(set(cur.get(key, [])) | {w.lower().strip() for w in words if len(w.strip()) >= 3})
    WHATIFS_DIR.mkdir(exist_ok=True)
    WORDS_FILE.write_text(json.dumps(cur, indent=1))


def bind(spec: dict) -> dict:
    """A stored spec → a live registry entry."""
    return {**spec, 'apply': make_apply(spec), 'facts': make_facts(spec)}


def load_generated(registry: dict) -> dict:
    """Every compiled what-if, whatever its year: a spec without `years` applies to its
    `year` (1920 for the oldest specs); an unreadable file is skipped, not fatal."""
    if WHATIFS_DIR.exists():
        for p in sorted(WHATIFS_DIR.glob('*.json')):
            if p.name == 'words.json':
                continue
            try:
                spec = json.loads(p.read_text())
            except (OSError, ValueError):
                continue
            if not isinstance(spec, dict) or not spec.get('key') or spec['key'] in registry:
                continue
            if not spec.get('years'):
                spec['years'] = [int(spec.get('year') or 1920)]
            registry[spec['key']] = bind(spec)
    return registry


def manifest(keys: list[str]) -> dict:
    """Hashes of the spec and evidence files a run depends on (its id changes with them)."""
    out = {}
    for k in keys:
        for p in (spec_path(k), evidence_path(k)):
            if p.exists():
                out[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    return out


def third_label(rng, taken: list[str], name: str, pool: list[str]) -> str:
    initials = {w[0].upper() for w in name.split() if w}
    free = [l for l in pool if l not in taken and l not in initials] or [l for l in pool if l not in taken]
    return rng.choice(free)

