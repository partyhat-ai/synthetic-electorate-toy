"""Historical evidence for a what-if: what reliable sources say about how the
same people behaved in the same situation, or the nearest one on record.

Two model calls per what-if, both logged with their cost:

1. **Research** (web search): a historian's research assistant looks for
   peer-reviewed work, academic books, official statistics and archives on
   (a) the change itself, if it happened or nearly did, (b) the same
   populations in the most similar situations, nearest in time first, and
   (c) what any named real person actually said or did on or before the
   context date. Answers carry citations to pages the search returned.
2. **Extraction** (structured output): the notes become findings. A finding
   may cite only sources the search actually returned (`S1`…); anything else
   is dropped. Structured outputs can't be combined with web-search
   citations in one call, hence two calls.

Evidence never enters a voter's brief. The agents stay blind to it, and to
anything dated after the context cutoff. It is used after the interviews:

- **evaluate**: does the interviews' effect agree with the historical
  record in direction and size?
- **blend** (exploratory what-ifs only): the evidence becomes a prior on
  each cohort's effect, combined with the interview effect by precision.
- **confidence**: a tier from high to very low ("extremely low"), with the
  reasons shown to the reader.

Pre-registered what-ifs use evidence only to evaluate and grade confidence.
Their numbers follow METHOD.md.
"""
from __future__ import annotations

import json
import re
import time
from urllib.parse import urlparse

import numpy as np

from .stats import expit, logit

EVIDENCE_VERSION = 'e1'

# ── Source reliability ──
# A: peer-reviewed, academic press, official statistics, archives.
# B: reputable reference works and public history.
# C: tertiary or unknown: a pointer to evidence, not evidence.
TIER_A = (
    'jstor.org', 'doi.org', 'muse.jhu.edu', 'cambridge.org', 'academic.oup.com', 'global.oup.com', 'oup.com',
    'tandfonline.com', 'journals.uchicago.edu', 'onlinelibrary.wiley.com', 'journals.sagepub.com',
    'link.springer.com', 'sciencedirect.com', 'nber.org', 'dataverse.harvard.edu', 'icpsr.umich.edu',
    'presidency.ucsb.edu', 'millercenter.org', 'history.house.gov', 'senate.gov', 'loc.gov', 'archives.gov',
    'census.gov', 'nps.gov', 'press.princeton.edu', 'press.uchicago.edu', 'escholarship.org', 'historians.org', 'oah.org', 'aeaweb.org', 'apsanet.org',
    'journalofamericanhistory.org', 'americanhistory.si.edu', 'fraser.stlouisfed.org', 'hathitrust.org',
    'archive.org', 'chroniclingamerica.loc.gov', 'jhu.edu', 'harvard.edu', 'yale.edu', 'stanford.edu',
)
TIER_A_SUFFIX = ('.edu', '.gov', '.ac.uk')
TIER_A_PREFIX = ('upress.', 'scholarship.', 'journals.', 'press.')  # university presses and journal hosts
TIER_B = (
    'britannica.com', 'smithsonianmag.com', 'si.edu', 'pbs.org', 'npr.org', 'gilderlehrman.org',
    'americanyawp.com', 'ncpedia.org', 'tshaonline.org', 'mnopedia.org', 'encyclopediavirginia.org',
    'georgiaencyclopedia.org', 'encyclopediaofalabama.org', 'ohiohistory.org', 'wisconsinhistory.org',
    'history.state.gov', 'nytimes.com', 'theatlantic.com', 'washingtonpost.com', 'newyorker.com',
    'bbc.co.uk', 'bbc.com', 'historynet.com', 'americanheritage.com', 'blackpast.org', 'womenshistory.org',
    'mnhs.org', 'kshs.org', 'indianahistory.org', 'historycooperative.org', 'uselectionatlas.org',
)
TIER_WEIGHT = {'A': 1.0, 'B': 0.6, 'C': 0.25}

# Never worth a search result.
BLOCKED = ['reddit.com', 'quora.com', 'pinterest.com', 'youtube.com', 'tiktok.com', 'facebook.com', 'x.com',
           'twitter.com', 'answers.com', 'coursehero.com', 'studocu.com', 'chegg.com', 'brainly.com',
           'enotes.com', 'gradesaver.com', 'ipl.org', 'bartleby.com', 'ukessays.com', 'studymoose.com']

MATCH_WEIGHT = {'same-event': 1.0, 'same-period-similar': 0.7, 'other-period-similar': 0.45, 'distant': 0.2}

FLIP = {'toward-R': 'toward-D', 'toward-D': 'toward-R', 'more-turnout': 'less-turnout', 'less-turnout': 'more-turnout',
        'toward-other': 'mixed'}

SEARCH_DOLLARS = 10 / 1000  # web search: $10 per 1,000 searches


def tier_of(url: str) -> str:
    host = (urlparse(url).hostname or '').lower().removeprefix('www.')
    if 'wikipedia.org' in host:
        return 'C'
    if any(host == d or host.endswith('.' + d) for d in TIER_A) or host.endswith(TIER_A_SUFFIX) or host.startswith(TIER_A_PREFIX):
        return 'A'
    if any(host == d or host.endswith('.' + d) for d in TIER_B):
        return 'B'
    return 'C'


# ── 1. Research: web search, citations kept ──

RESEARCH_SYSTEM = """You are a research assistant to a historian of American elections. You search the web for reliable evidence and report it with citations.

What counts as reliable, best first:
1. Peer-reviewed journal articles and academic books by historians or political scientists.
2. Official statistics and archival collections: the Census Bureau, the Clerk of the House, the Library of Congress, the National Archives, state archives.
3. Reputable reference works: Britannica, university-hosted or state-historical-society encyclopedias.
Use Wikipedia only to find sources of the first three kinds; never rest a finding on it alone. Ignore forums, content farms, homework and essay sites.

Report, in this order:
1. Direct evidence. If this change happened, or nearly happened, what scholars say about its effect on voters and turnout.
2. Analogues. The same populations in the most similar situations on record, nearest in time and place first. Give numbers wherever the sources do: turnout, vote shares, swings, by group. Say when and where each happened.
3. Named people. For any real person the scenario names, what they actually said or did about the relevant questions on or before the scenario's date, with dates. Describe it; don't quote at length.
4. Limits. Why each analogue might not carry over.

Search before you write: run at least two searches, and more for anything you'd otherwise state from memory. A claim without a citation will be thrown away, however well you know it. Cite every factual sentence. Give changes in percentage points where you can. If you find nothing reliable, say so plainly. Don't stretch a weak source into a strong claim."""


def research_prompt(spec: dict, election: dict) -> str:
    reach = spec.get('reach') or {}
    who = ', '.join(f'{k}: {", ".join(v)}' for k, v in reach.items() if v) or 'every voter'
    lines = [
        f'Scenario for the {election["year"]} United States presidential election (election day {election["day"]}).',
        f'A reader asked: "{spec.get("source_text") or spec["label"]}".',
        f'As modelled: {spec["detail"]}',
        f'Kind of change: {spec["kind"]}. Populations it reaches first: {who}.',
    ]
    if (spec.get('candidate') or {}).get('name'):
        c = spec['candidate']
        lines.append(f'Named person on the ballot: {c["name"]} ({c.get("descriptor", "")}).')
    hint = {
        'candidate': 'Include the strongest third-party and independent runs nearest in time (1912 and 1924 above all), '
                     'which groups they drew from and what share they took; and any run by a famous non-politician.',
        'franchise': 'Include how newly enfranchised or newly barred groups actually turned out and voted the first times '
                     'the rules changed for them.',
        'population': 'Include how the groups whose numbers change turned out and voted in nearby elections.',
    }.get(spec['kind'], 'Include how the same groups swung, by how much, when comparable issues or shocks hit nearby elections.')
    lines.append(hint)
    qs = spec.get('research_questions') or []
    if qs:
        lines += ['', 'Questions to answer:'] + [f'- {q}' for q in qs]
    from .agentlayer import groups_for
    phrase = groups_for(int(election['year']))['phrase']
    lines += ['', f'Groups the simulation distinguishes: men and women; {phrase} adults; '
                  f'the Northeast, Midwest, South (the eleven former '
                  f'Confederate states), border states and West. Evidence by these groups is most useful.']
    return '\n'.join(lines)


def research(client, spec: dict, election: dict, model: str, max_uses: int = 4, effort: str = 'low',
             max_tokens: int = 6000) -> dict:
    """One web-search research turn (continuing through pause_turn). Returns
    {text (with [S#] markers), sources: [{id, url, title, tier, cited, page_age}], queries, usage, dollars}."""
    from . import llm
    tools = [{'type': 'web_search_20250305', 'name': 'web_search', 'max_uses': max_uses, 'blocked_domains': BLOCKED}]
    user = research_prompt(spec, election)
    params = {'model': model, 'max_tokens': max_tokens, 'system': RESEARCH_SYSTEM, 'tools': tools}
    if 'haiku' not in model:
        params['output_config'] = {'effort': effort}
    usage, searches = {'input_tokens': 0, 'output_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation_input_tokens': 0}, 0
    for attempt in range(2):
        assistant = []
        ask = user if attempt == 0 else user + ('\n\nSearch first. Your last answer ran no searches, so none of it could be '
                                                'used: every claim needs a citation to a page the search returns.')
        for _ in range(4):
            messages = [{'role': 'user', 'content': ask}] + ([{'role': 'assistant', 'content': assistant}] if assistant else [])
            msg = _create(client, messages=messages, **params)
            assistant += list(msg.content)
            u = msg.usage
            for k in usage:
                usage[k] += getattr(u, k, 0) or 0
            stu = getattr(u, 'server_tool_use', None)
            searches += (getattr(stu, 'web_search_requests', 0) or 0) if stu else 0
            if msg.stop_reason != 'pause_turn':
                break
        if any(getattr(b, 'type', None) == 'web_search_tool_result' for b in assistant):
            break  # a turn without a single search is retried once, then kept as it is
    sources, by_url, queries, parts = [], {}, [], []

    def src(url, title, page_age=None):
        if url not in by_url:
            by_url[url] = f'S{len(sources) + 1}'
            sources.append({'id': by_url[url], 'url': url, 'title': title or url, 'tier': tier_of(url),
                            'cited': [], 'page_age': page_age})
        return by_url[url]

    for b in assistant:
        t = getattr(b, 'type', None)
        if t == 'server_tool_use':
            queries.append((getattr(b, 'input', None) or {}).get('query'))
        elif t == 'web_search_tool_result':
            content = getattr(b, 'content', None)
            if isinstance(content, list):
                for r in content:
                    if getattr(r, 'type', None) == 'web_search_result':
                        src(r.url, r.title, getattr(r, 'page_age', None))
        elif t == 'text':
            ids = []
            for c in getattr(b, 'citations', None) or []:
                url = getattr(c, 'url', None)
                if not url:
                    continue
                sid = src(url, getattr(c, 'title', None))
                cited = (getattr(c, 'cited_text', '') or '').strip()
                if cited and cited not in sources[int(sid[1:]) - 1]['cited']:
                    sources[int(sid[1:]) - 1]['cited'].append(cited[:400])
                ids.append(sid)
            parts.append(b.text + (' [' + ', '.join(dict.fromkeys(ids)) + ']' if ids else ''))
    dollars = llm.cost(model, usage) + searches * SEARCH_DOLLARS
    return {'text': ''.join(parts).strip(), 'sources': sources, 'queries': [q for q in queries if q],
            'usage': usage | {'web_search_requests': searches}, 'dollars': round(dollars, 4), 'model': model,
            'prompt': user}


def research_estimate(model: str, max_uses: int, max_tokens: int = 6000) -> dict:
    """Search results are the bulk of a research call's input: about 8k tokens a
    search, re-read on each server-side step."""
    from . import llm
    typical = llm.cost(model, {'input_tokens': 15000 * max_uses, 'output_tokens': 2500}) + max(1, max_uses - 1) * SEARCH_DOLLARS
    worst = llm.cost(model, {'input_tokens': 12000 * max_uses * (max_uses + 1) // 2 + 3000, 'output_tokens': max_tokens}) + max_uses * SEARCH_DOLLARS
    return {'typical': round(typical, 4), 'worst': round(worst, 4)}


# ── 2. Extraction: notes → findings, grounded in the returned sources ──

EXTRACT_SYSTEM = """You turn a research assistant's notes into structured findings for an election simulation.

Rules:
- Extract every claim in the notes that carries a source marker like [S3] and says something about how people voted or turned out, including the loose analogues. Don't judge reliability yourself: the pipeline grades each source and each match afterwards and weights them. A finding resting on Wikipedia is still a finding.
- Copy the source ids exactly. Add nothing from your own knowledge.
- At most 12 findings, the most informative first; merge claims about the same situation. Keep each claim under 35 words, situation and limits under 20.
- Keep loose analogues too, graded by match ("distant" when the situation only loosely resembles the scenario): they are weighted down, not thrown away. Leave out only claims that say nothing about how people voted or turned out.
- population: the group the finding is about. Use "any" where the finding doesn't narrow it.
- match: how close the finding's situation is to the scenario. "same-event": this very change, in this very election. "same-period-similar": a similar situation within about a dozen years. "other-period-similar": a similar situation further away. "distant": a loose analogy.
- effects: numbers only when the notes give them, as percentage-point changes caused by the situation: "turnout" (share of eligible adults voting), "r2" (the Republican share of the two-party vote; positive means more Republican), "other" (the share of all votes going to a third candidate or party). pm is the plus-or-minus the notes give or imply; use half the effect's size when they give none. Leave effects empty when the notes give no number.
- direction and effects describe what happened in the finding's own situation, as the sources report it. Never flip them yourself.
- relation says how that situation maps onto the scenario: "like-scenario" when the scenario would bring about the same kind of situation (a third-party run, for a third-party scenario); "reverses-scenario" when the scenario removes or undoes it (the scenario settles an issue that in fact cost a party votes); "context" when it only describes the election or its setting without showing how people responded to a comparable change (who won, overall turnout). The pipeline flips reversed findings and sets context aside.
- direction: the finding's direction even without numbers, in that election's own party terms.
- role_direction: when the scenario concerns one nominee (the affected candidate, named below), which way the finding's voters moved relative to the candidate who stood in the same role in the finding's own situation (the scandal-hit candidate, say), whatever his party: "toward-affected" or "away-from-affected". "none" when there is no such role. Give its size, when the notes do, as the effect measure "affected": the change in that candidate's share of the two-party vote, in points.
- actor_positions: for a named real person, what they said or did on or before the scenario's date, in a neutral dated paraphrase (never a quotation), with its source ids.
- no_reliable_evidence: true only when there are no findings at all, or every one is a loose ("distant") analogy."""

POP = {'type': 'object', 'properties': {
    'sex': {'type': 'string', 'enum': ['any', 'M', 'F']},
    'group': {'type': 'string', 'enum': ['any', 'native_white', 'foreign_white_naturalized', 'foreign_white_alien', 'black']},
    'region': {'type': 'string', 'enum': ['any', 'northeast', 'midwest', 'south', 'border', 'west']},
}, 'required': ['sex', 'group', 'region'], 'additionalProperties': False}

EXTRACT_SCHEMA = {
    'type': 'object',
    'properties': {
        'summary': {'type': 'string'},
        'findings': {'type': 'array', 'items': {'type': 'object', 'properties': {
            'claim': {'type': 'string'},
            'source_ids': {'type': 'array', 'items': {'type': 'string'}},
            'population': POP,
            'situation': {'type': 'string'},
            'when': {'type': 'string'},
            'match': {'type': 'string', 'enum': list(MATCH_WEIGHT)},
            'relation': {'type': 'string', 'enum': ['like-scenario', 'reverses-scenario', 'context']},
            'role_direction': {'type': 'string', 'enum': ['toward-affected', 'away-from-affected', 'none']},
            'direction': {'type': 'string', 'enum': ['toward-R', 'toward-D', 'toward-other', 'more-turnout',
                                                     'less-turnout', 'mixed', 'none', 'unclear']},
            'effects': {'type': 'array', 'items': {'type': 'object', 'properties': {
                'measure': {'type': 'string', 'enum': ['turnout', 'r2', 'other', 'affected']},
                'pp': {'type': 'number'}, 'pm': {'type': 'number'},
            }, 'required': ['measure', 'pp', 'pm'], 'additionalProperties': False}},
            'limits': {'type': 'string'},
        }, 'required': ['claim', 'source_ids', 'population', 'situation', 'when', 'match', 'relation', 'role_direction', 'direction',
                        'effects', 'limits'],
            'additionalProperties': False}},
        'actor_positions': {'type': 'array', 'items': {'type': 'object', 'properties': {
            'text': {'type': 'string'}, 'date': {'type': 'string'},
            'source_ids': {'type': 'array', 'items': {'type': 'string'}},
        }, 'required': ['text', 'date', 'source_ids'], 'additionalProperties': False}},
        'caveats': {'type': 'array', 'items': {'type': 'string'}},
        'no_reliable_evidence': {'type': 'boolean'},
    },
    'required': ['summary', 'findings', 'actor_positions', 'caveats', 'no_reliable_evidence'],
    'additionalProperties': False,
}


def extract_request(spec: dict, notes: dict, model: str) -> dict:
    table = '\n'.join(f'{s["id"]}: {s["title"]} ({urlparse(s["url"]).hostname}, reliability {s["tier"]})' for s in notes['sources'])
    from .profiles import get
    full = get(spec.get('year', 1920))['full_names']
    role = {'R': f'the Republican nominee ({full["R"]})', 'D': f'the Democratic nominee ({full["D"]})'}.get(spec.get('about'))
    who = f'\nThe affected candidate: {role}.' if role else '\nThe scenario concerns neither nominee personally: role_direction is "none".'
    user = (f'Scenario: {spec["detail"]}{who}\n\nSources the search returned:\n{table or "(none)"}\n\n'
            f'Research notes:\n{notes["text"] or "(the assistant found nothing)"}')
    return {'id': f'extract|{spec["key"]}', 'model': model, 'system': EXTRACT_SYSTEM, 'user': user,
            'schema': EXTRACT_SCHEMA, 'meta': {'kind': 'extract', 'what_if': spec['key']}}


def ground(extracted: dict, notes: dict, about: str | None = None) -> dict:
    """Keep only findings whose sources the search returned; grade each. about: the nominee
    ('R' or 'D') the scenario concerns; findings from other elections then count by role
    (toward the scandal-hit candidate, say), not by that year's party labels (D22)."""
    by_id = {s['id']: s for s in notes['sources']}
    findings, dropped = [], 0
    for f in extracted.get('findings', []):
        ids = [i for i in f.get('source_ids', []) if i in by_id]
        if not ids:
            dropped += 1
            continue
        tier = min((by_id[i]['tier'] for i in ids), key='ABC'.index)
        # A finding resting only on tertiary sources is kept as a pointer, down-weighted.
        grade = TIER_WEIGHT[tier] * MATCH_WEIGHT.get(f['match'], 0.2)
        effects = [e for e in f.get('effects', []) if abs(e.get('pp', 0)) <= 60]
        direction = f['direction']
        if about in ('R', 'D'):
            sign = 1 if about == 'R' else -1
            rd = f.get('role_direction', 'none')
            if rd != 'none':
                toward = about if rd == 'toward-affected' else ('D' if about == 'R' else 'R')
                direction = f'toward-{toward}'
            # the affected candidate's two-party share, as the Republican two-party share
            effects = [e for e in effects if e['measure'] != 'r2'] + \
                      [e | {'measure': 'r2', 'pp': sign * e['pp']} for e in effects if e['measure'] == 'affected']
        effects = [e for e in effects if e['measure'] != 'affected']
        rel = f.get('relation', 'like-scenario')
        if rel == 'reverses-scenario':  # the scenario undoes this situation: its effect runs the other way
            direction = FLIP.get(direction, direction)
            effects = [e | {'pp': -e['pp']} for e in effects if e['measure'] != 'other']
        elif rel == 'context':
            direction, effects = 'none', []
        findings.append({**f, 'source_ids': ids, 'tier': tier, 'grade': round(grade, 3), 'effects': effects,
                         'direction': direction, 'reported_direction': f['direction']})
    positions = [p | {'source_ids': [i for i in p['source_ids'] if i in by_id]} for p in extracted.get('actor_positions', [])]
    positions = [p for p in positions if p['source_ids']]
    return {'summary': extracted.get('summary', ''), 'findings': findings, 'actor_positions': positions,
            'caveats': extracted.get('caveats', []), 'dropped_ungrounded': dropped,
            'no_reliable_evidence': bool(extracted.get('no_reliable_evidence')) or not findings}


def strength(ev: dict | None) -> dict:
    """strong ≥ 0.7, moderate ≥ 0.4, weak > 0, none. The best informative
    finding's grade, plus a little for corroboration (others graded ≥ 0.3)."""
    # Only findings that say which way people moved, or by how much, speak to the change;
    # context (turnout that year, who went to the pictures) informs the reader but not the strength.
    fs = [f for f in (ev or {}).get('findings', []) if f['effects'] or f['direction'] not in ('none', 'unclear', 'mixed')]
    if not fs:
        return {'level': 'none', 'score': 0.0, 'best': None}
    fs = sorted(fs, key=lambda f: -f['grade'])
    score = fs[0]['grade'] + 0.1 * sum(1 for f in fs[1:4] if f['grade'] >= 0.3)
    score = min(score, 1.0)
    level = 'strong' if score >= 0.7 else 'moderate' if score >= 0.4 else 'weak'
    return {'level': level, 'score': round(score, 3), 'best': fs[0]['claim']}


# ── 3. Evidence as a prior on cohort effects ──

def _applies(pop: dict, cohort: dict) -> bool:
    if pop['sex'] != 'any' and pop['sex'] != cohort['sex']:
        return False
    if pop['group'] != 'any' and pop['group'] != cohort['group']:
        return False
    if pop['region'] != 'any' and pop['region'] not in cohort.get('regions', [cohort.get('region')]):
        return False
    return True


def prior(ev: dict, cohort: dict, base: dict) -> dict:
    """{dt, dr, do: (mean, sd) on the logit scale} for one cohort, from the
    graded, quantified findings that apply to it. base: the cohort's backbone
    {turnout, r2, o}. A specific finding (group or region named) counts twice
    a general one. Weak evidence gives a wide prior: sd ∝ 1/√grade."""
    out = {}
    for measure, key, b in (('turnout', 'dt', base['turnout']), ('r2', 'dr', base['r2']), ('other', 'do', base['o'])):
        rows = []
        for f in ev.get('findings', []):
            if not _applies(f['population'], cohort):
                continue
            specific = 2.0 if (f['population']['group'] != 'any' or f['population']['region'] != 'any') else 1.0
            for e in f['effects']:
                if e['measure'] == measure:
                    rows.append((e['pp'], max(abs(e['pm']), 2.0), f['grade'] * specific))
        if not rows:
            continue
        w = np.array([r[2] for r in rows])
        pp = float(np.average([r[0] for r in rows], weights=w))
        spread = float(np.sqrt(np.average([(r[0] - pp) ** 2 for r in rows], weights=w)))
        pm = float(np.average([r[1] for r in rows], weights=w))
        g = float(min(1.0, w.max()))
        sd_pp = np.sqrt(pm ** 2 + spread ** 2 + 3.0 ** 2) / np.sqrt(max(g, 0.05))
        b = float(np.clip(b, 0.01, 0.99))
        new = float(np.clip(b + pp / 100, 0.005, 0.995))
        out[key] = (float(logit(new) - logit(b)), float(sd_pp / 100 / (b * (1 - b))), len(rows))
    return out


def blend(cohort_eff: dict, pri: dict) -> dict:
    """Precision-weighted combination of a cohort's interview draws with the
    evidence prior. The draws keep their shape, rescaled to the posterior sd."""
    draws = {k: np.asarray(v, float).copy() for k, v in cohort_eff['draws'].items()}
    used = {}
    for key, (mu_e, sd_e, n) in pri.items():
        d = draws[key]
        # A bootstrap over two or three people understates how wrong the model can be;
        # floor it near the Sonnet–Opus disagreement on the same people (D8, ~0.15 logit).
        mu_a, sd_a = float(d.mean()), max(float(d.std()), 0.2)
        prec_a, prec_e = 1 / sd_a ** 2, 1 / sd_e ** 2
        mu_p = (mu_a * prec_a + mu_e * prec_e) / (prec_a + prec_e)
        sd_p = (prec_a + prec_e) ** -0.5
        draws[key] = mu_p + (d - mu_a) * (sd_p / sd_a)
        used[key] = {'agents': round(mu_a, 3), 'evidence': round(mu_e, 3), 'evidence_sd': round(sd_e, 3),
                     'evidence_weight': round(prec_e / (prec_a + prec_e), 3), 'posterior': round(mu_p, 3), 'findings': n}
    return {**cohort_eff, 'draws': draws, 'evidence_blend': used}


# ── 4. Agreement and confidence ──

def _agree_one(ev: dict, national: dict, measure: str, key: str, b: float) -> dict | None:
    """One measure: the interviews' national effect (logit, 80% interval) against the findings, in points."""
    agent_pp = (float(expit(logit(b) + national[key]['mean'])) - b) * 100
    lo = (float(expit(logit(b) + national[key]['lo'])) - b) * 100
    hi = (float(expit(logit(b) + national[key]['hi'])) - b) * 100
    what = {'other': 'the third candidate\'s share', 'r2': 'the Republican two-party share', 'turnout': 'turnout'}[measure]
    rows = [(e['pp'], abs(e['pm']), f['grade']) for f in ev['findings'] for e in f['effects'] if e['measure'] == measure]
    if not rows:
        want = {'r2': ('toward-R', 'toward-D'), 'other': ('toward-other', None), 'turnout': ('more-turnout', 'less-turnout')}[measure]
        signs = [1 if f['direction'] == want[0] else -1 for f in ev['findings'] if f['grade'] >= 0.1 and f['direction'] in want]
        if not signs:
            return None
        s = np.sign(np.mean(signs))
        ok = np.sign(agent_pp) == s or abs(agent_pp) < 0.5
        return {'verdict': 'consistent' if ok else 'contradicted', 'measure': measure, 'agents_pp': round(agent_pp, 1),
                'detail': f'On {what}, the sources point {"the same way as" if ok else "the other way from"} the interviews '
                          f'({agent_pp:+.1f} points), without numbers.'}
    w = np.array([r[2] for r in rows])
    ev_pp = float(np.average([r[0] for r in rows], weights=w))
    spread = float(np.sqrt(np.average([(r[0] - ev_pp) ** 2 for r in rows], weights=w)))
    ev_pm = float(np.hypot(np.average([max(r[1], 2.0) for r in rows], weights=w), spread))  # the analogues disagree too
    overlap = not (hi < ev_pp - ev_pm or lo > ev_pp + ev_pm)
    same_sign = np.sign(ev_pp) == np.sign(agent_pp) or abs(ev_pp) < 1 or abs(agent_pp) < 0.5
    verdict = 'corroborated' if overlap and same_sign else 'consistent' if same_sign else 'contradicted'
    return {'verdict': verdict, 'measure': measure, 'agents_pp': round(agent_pp, 1), 'agents_range_pp': [round(lo, 1), round(hi, 1)],
            'evidence_pp': round(ev_pp, 1), 'evidence_pm': round(ev_pm, 1),
            'detail': f'Interviews move {what} {agent_pp:+.1f} points ({lo:+.1f} to {hi:+.1f}); the closest historical '
                      f'cases moved it {ev_pp:+.1f} ± {ev_pm:.1f}.'}


def agreement(ev: dict | None, national: dict, base: dict, kind: str) -> dict:
    """Does the record agree with the interviews? Checked on the vote measure
    (the third candidate's share for a candidate, else the two-party share)
    and on turnout. Any contradiction wins; then corroboration; then consistency."""
    if not ev or not ev.get('findings') or not national:
        return {'verdict': 'untested', 'detail': 'No historical evidence to compare with.', 'measures': []}
    vote = ('other', 'do', base['o']) if kind == 'candidate' else ('r2', 'dr', base['r2'])
    got = [x for x in (_agree_one(ev, national, m, k, b) for m, k, b in (vote, ('turnout', 'dt', base['turnout']))) if x]
    if not got:
        return {'verdict': 'untested', 'measures': [],
                'detail': 'The sources describe the situation but give no number or direction to compare with.'}
    for v in ('contradicted', 'corroborated', 'consistent'):
        if any(x['verdict'] == v for x in got):
            return {'verdict': v, 'measures': got, 'detail': ' '.join(x['detail'] for x in got)}


TIERS = ['very-low', 'low', 'medium', 'high']
TIER_LABEL = {'high': 'High confidence', 'medium': 'Medium confidence', 'low': 'Low confidence',
              'very-low': 'Extremely low confidence'}
BASE_TIER = {'franchise': 3, 'population': 2, 'issue': 1, 'event': 1, 'candidate': 1}


def confidence(spec: dict, ev: dict | None, agree: dict | None, agent: dict | None, generated: bool) -> dict:
    """A tier and the reasons for it. Agent-driven changes start at low; the
    record can lift one to medium only when strong evidence corroborates it.
    Fantasy, anachronism, contradiction or unstable interviews push it down."""
    kind = spec['kind']
    t = BASE_TIER.get(kind, 1)
    if generated and kind == 'franchise':
        t = 2  # borrowed behaviour chosen by the compiler, not by the pre-registration
    flags, reasons = [], []
    st = strength(ev) if ev is not None else {'level': 'not-researched'}
    plaus = spec.get('plausibility', 'documented')
    if plaus == 'fantastical' or spec.get('anachronism'):
        t = 0
        flags.append('fantastical' if plaus == 'fantastical' else 'anachronism')
        reasons.append(spec.get('anachronism_note') or f'Nothing like this was possible in {spec.get("year", 1920)}, so no one\'s behaviour on record speaks to it.')
    elif plaus == 'a-stretch':
        t -= 1
        flags.append('far-from-record')
        reasons.append('The change is far from anything that happened, so behaviour on record only loosely applies.')
    if ev is None:
        flags.append('not-researched')
    elif st['level'] == 'none':
        if kind in ('issue', 'event', 'candidate'):
            t -= 1
        flags.append('no-evidence')
        reasons.append('I found no reliable historical work on how people behaved in this or a similar situation.')
    elif st['level'] == 'weak':
        flags.append('weak-evidence')
        reasons.append('Historical evidence is thin: loose analogies or weak sources only.')
    verdict = (agree or {}).get('verdict')
    if verdict == 'contradicted':
        t -= 1
        flags.append('contradicts-record')
        reasons.append('The interviews point the other way from the historical record.')
    elif verdict == 'corroborated' and st['level'] == 'strong' and kind in ('issue', 'event', 'candidate'):
        t += 1
        reasons.append('Strong historical evidence agrees with the interviews.')
    if agent and spec.get('mode') == 'agents':  # backbone-mode interviews are a cross-check; they move no numbers
        unstable = agent.get('spans_zero') and agent.get('paraphrase_flip')
        backed = verdict == 'corroborated' or (verdict == 'consistent' and st['level'] == 'strong')
        if unstable and not backed:
            t -= 1
            flags.append('unstable-interviews')
            reasons.append('The interviews\' answer changes sign with the question\'s wording.')
        elif unstable:
            flags.append('unstable-interviews')
            reasons.append('The interviews\' answer changes sign with the question\'s wording, though the record points the same way.')
        checked, wrong = agent.get('checked') or 0, agent.get('misread') or 0
        if checked and wrong:
            flags.append('misread-change')
            reasons.append(f'{wrong} of {checked} people interviewed took the news to be about the other candidate; '
                           'their answers were left out.')
            if wrong / checked >= 0.5:
                t = 0
            elif wrong / checked > 0.25:
                t -= 1
        if agent.get('n', 99) < 6:
            t -= 1
            flags.append('few-interviews')
            reasons.append(f'Only {agent.get("n")} people were interviewed on it.')
        if agent.get('exposed'):
            flags.append('model-knows-outcome')
    cand = spec.get('candidate') or {}
    if cand.get('name') and cand.get('positions_source') == 'inferred':
        flags.append('positions-inferred')
        reasons.append(f'{cand["name"]}\'s positions are inferred, not documented.')
    if cand.get('name') and cand.get('eligibility_note'):
        flags.append('ineligible-candidate')
        reasons.append(cand['eligibility_note'])
    if generated:
        flags.append('exploratory')
    cap = 2 if kind in ('issue', 'event', 'candidate') else 3
    t = int(max(0, min(cap, t)))
    return {'tier': TIERS[t], 'label': TIER_LABEL[TIERS[t]], 'flags': flags, 'reasons': reasons,
            'evidence': st['level']}


def combine_tiers(tiers: list[dict]) -> dict:
    if not tiers:
        return {'tier': 'high', 'label': TIER_LABEL['high'], 'flags': [], 'reasons': [], 'evidence': None}
    worst = min(tiers, key=lambda c: TIERS.index(c['tier']))
    flags = list(dict.fromkeys(f for c in tiers for f in c['flags']))
    reasons = list(dict.fromkeys(r for c in tiers for r in c['reasons']))
    return {**worst, 'flags': flags, 'reasons': reasons}


def page_evidence(key: str, ev: dict | None, agree: dict | None, sources_limit: int = 4) -> dict | None:
    """What the page shows: the summary, the agreement, and the best findings with their sources."""
    if not ev:
        return None
    by_id = {s['id']: s for s in ev.get('sources', [])}
    fs = sorted(ev.get('findings', []), key=lambda f: -f['grade'])[:sources_limit]
    return {
        'whatIf': key, 'strength': strength(ev)['level'], 'summary': ev.get('summary', ''),
        'agreement': (agree or {}).get('verdict', 'untested'), 'agreementDetail': (agree or {}).get('detail'),
        'findings': [{'claim': f['claim'], 'when': f['when'], 'match': f['match'], 'tier': f['tier'],
                      'sources': [{'title': by_id[i]['title'], 'url': by_id[i]['url'], 'tier': by_id[i]['tier']}
                                  for i in f['source_ids'] if i in by_id]} for f in fs],
        'caveats': ev.get('caveats', [])[:3],
        **({'researchedAt': ev['researched_at']} if ev.get('researched_at') else {}),
    }


def _create(client, **params):
    """messages.create with the harness's retry rules (rate limits, 5xx)."""
    import anthropic
    for attempt in range(5):
        try:
            return client.messages.create(**params)
        except anthropic.RateLimitError:
            time.sleep(2 ** attempt + 1)
        except anthropic.APIStatusError as e:
            if e.status_code < 500:
                raise
            time.sleep(2 ** attempt)
        except anthropic.APIConnectionError:
            time.sleep(2 ** attempt)
    raise RuntimeError('retries exhausted')


def slug(text: str, n: int = 40) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return s[:n].rstrip('-') or 'what-if'


def dumps(x) -> str:
    return json.dumps(x, indent=1, default=float)
