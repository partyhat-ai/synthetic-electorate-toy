"""Versioned prompts: the blinded control brief, the non-hypothetical
counterfactual brief, the recall probe and the label-swap perturbation.

Rules the templates enforce:
- The candidates are neutral letters, drawn per agent from letters that match
  no 1920 candidate's or party's initial, in a random order.
- Every dated item in a brief is dated on or before the context cutoff, and
  shows its date.
- A counterfactual is never phrased as a hypothesis. The changed fact is
  written into the person's world as settled; anything in the brief that the
  change would contradict is removed; the exact change is logged in the
  request's meta (never shown to the model as a change).
"""
from __future__ import annotations

import datetime as dt
import random

# p1: the 1920 prototype's answers. p2: brief dated on the context cutoff (p1 dated
# briefs 30 Oct but admitted items to 1 Nov); non-citizens get no franchise counterfactual.
# p3: quote capped at 25 words, no letter labels (DISCLOSURES D11).
# p4: a candidate what-if's counterfactual ballot carries a third labelled line (a named
# independent); every other brief is byte-identical to p3's, so p3 answers to them are reused.
# p5: news about one nominee sits on that nominee's ballot line, and those counterfactuals
# carry a manipulation check (news_about) (DISCLOSURES D21). Briefs without such news are
# byte-identical to p4's.
PROMPT_VERSION = 'p5'

NEWS_CHECK = ('Also fill news_about: the label of the candidate the recent news on the ballot concerns, '
              '"neither" if it concerns neither, or "unsure".')

# No H(arding), C(ox), D(ebs), R(epublican), D(emocrat), S(ocialist),
# F(armer-Labor), W(ilson), L(eague).
LABEL_POOL = ['K', 'M', 'N', 'P', 'T', 'V']

SYSTEM = """You give voice to one invented person living in the United States. The brief you receive is that person's life and world as they stand on the date it gives: their circumstances, their memories, and what they have lately read or heard. Every line of the brief is settled fact about the world. It is not a scenario or a hypothesis, and you never comment on it as one.

Answer only from what this person could know on that date. The person does not know anything that happens after it, including how any election turns out. Where the brief leaves something open, answer as this particular person plausibly would given their own circumstances, not as a type or a stereotype of any group.

Fill the requested JSON:
- able_to_vote: whether this person can lawfully cast a ballot for president this year and, in practice, will be allowed to.
- p_vote: the chance, 0 to 100, that this person casts a presidential ballot.
- choice: the candidate this person would vote for if they vote (a label), "other", or "none".
- p_choice: this person's leanings as chances that add to 100, over the labelled candidates and "other".
- confidence: 0 to 100, how settled the person's mind is.
- reason: one or two sentences, in the third person, naming the circumstances in the brief that drove the answer.
- quote: one or two sentences, at most 25 words, the person might say aloud to a neighbour. Plain English of the period, specific to their own circumstances. Never use a candidate's letter label in the quote; a person would say "the Republican", "the man from Ohio" or "the administration's man", never "Candidate K" or "K". No slurs, no melodrama.
- sources_used: the ids of the dated items in the brief the answer rests on."""

PROBE_SYSTEM = """You are a careful historian. Answer the question about the document you are given. If you do not know, answer "unknown". Fill the requested JSON."""

QUESTIONS = [
    'Election Day is Tuesday. Can this person vote, how likely are they to vote, and if they vote, for whom?',
    'A neighbour asks what this person will do on Tuesday, 2 November. Will they cast a ballot for president, and for which candidate?',
    'Think about Tuesday\'s presidential election from where this person stands. How likely are they to vote, and which candidate would get their vote?',
]

WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')


def questions(day_phrase: str = 'Tuesday, 2 November') -> list[str]:
    """The three paraphrases for an election day (1920's are QUESTIONS, unchanged). Before
    1845 states chose electors on different days, and the profile's day_phrase is a clause
    ("the day this person's state has set…"): the questions then say "election day"."""
    day = day_phrase.split(',')[0].strip()
    if day == 'Tuesday':
        return [q.replace('Tuesday, 2 November', day_phrase) for q in QUESTIONS]
    if day in WEEKDAYS:
        return [q.replace('Tuesday, 2 November', day_phrase).replace('Election Day is Tuesday.', f'Election Day is {day}.')
                .replace("Tuesday's presidential election", f"{day}'s presidential election") for q in QUESTIONS]
    return [q.replace('Tuesday, 2 November', 'election day').replace('Election Day is Tuesday.', 'The presidential election is near.')
            .replace("Tuesday's presidential election", 'the coming presidential election') for q in QUESTIONS]


PROBE_QUESTION = (
    'Set the person aside. Which year\'s United States presidential election does this brief describe? '
    'Which real candidates stand behind each label? Who won that election? '
    'Answer "unknown" for anything you cannot tell.'
)


def answer_schema(labels: list[str], news_check: bool = False) -> dict:
    choice_props = {l: {'type': 'integer'} for l in labels}
    choice_props['other'] = {'type': 'integer'}
    if news_check:
        s = answer_schema(labels)
        s['properties']['news_about'] = {'type': 'string', 'enum': labels + ['neither', 'unsure']}
        s['required'].append('news_about')
        return s
    return {
        'type': 'object',
        'properties': {
            'able_to_vote': {'type': 'string', 'enum': ['yes', 'no', 'unsure']},
            'p_vote': {'type': 'integer'},
            'choice': {'type': 'string', 'enum': labels + ['other', 'none']},
            'p_choice': {'type': 'object', 'properties': choice_props,
                         'required': list(choice_props), 'additionalProperties': False},
            'confidence': {'type': 'integer'},
            'reason': {'type': 'string'},
            'quote': {'type': 'string'},
            'sources_used': {'type': 'array', 'items': {'type': 'string'}},
        },
        'required': ['able_to_vote', 'p_vote', 'choice', 'p_choice', 'confidence', 'reason', 'quote', 'sources_used'],
        'additionalProperties': False,
    }


def probe_schema(labels: list[str]) -> dict:
    return {
        'type': 'object',
        'properties': {
            'year': {'type': 'string'},
            'candidates': {'type': 'object', 'properties': {l: {'type': 'string'} for l in labels},
                           'required': labels, 'additionalProperties': False},
            'winner_label': {'type': 'string'},
            'winner_name': {'type': 'string'},
            'confidence': {'type': 'integer'},
        },
        'required': ['year', 'candidates', 'winner_label', 'winner_name', 'confidence'],
        'additionalProperties': False,
    }


def long_date(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return f'{d.strftime("%A")}, {d.day} {d.strftime("%B %Y")}'


OTHERS_1920 = 'Other candidates on some ballots, including a Socialist and a Farmer-Labor nominee (answer "other").'


def ballot_block(state_name: str, parties: list[dict], labels: list[str], others: str = OTHERS_1920,
                 note: str | None = None) -> list[str]:
    """parties: [{key, descriptor, planks: [str]}] in display order, already
    paired with labels in the same order. note: a profile's ballot note for this
    state (profile 'ballot_notes', e.g. 1964 Alabama's unpledged electors), last."""
    lines = [f'On the ballot for president in {state_name}:']
    for label, p in zip(labels, parties):
        planks = ' '.join(p['planks'])
        news = f' Recent news: {" ".join(p["news"])}' if p.get('news') else ''
        lines.append(f'- Candidate {label}: {p["descriptor"]}.{news} {planks}'.rstrip())
    lines.append(f'- {others}')
    if note:
        lines.append(f'- {note}')
    return lines


def brief(persona: dict, world: dict, items: list[dict], ballot: list[str], asof: str, day_phrase: str = 'Tuesday, 2 November') -> str:
    lines = [f'Date: {long_date(asof)}. The presidential election is on {day_phrase}.', '', 'This person:']
    lines += [f'- {line}' for line in persona['lines']]
    if world.get('facts'):
        lines += ['', 'How things stand:']
        lines += [f'- {f}' for f in world['facts']]
    if items:
        lines += ['', 'What this person has lately read or heard (dated):']
        for it in items:
            lines.append(f'[{it["id"]}] {it["newspaper"]}, {it["place"]}, {long_date(it["date"])}: "{it["text"]}"')
    lines += [''] + ballot
    return '\n'.join(lines)


def assign_labels(rng: random.Random, keys: list[str], pool: list[str] = LABEL_POOL) -> dict:
    """{party key: label}, and the display order."""
    labels = rng.sample(pool, len(keys))
    order = keys[:]
    rng.shuffle(order)
    return dict(zip(keys, labels)), order
