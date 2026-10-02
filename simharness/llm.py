"""The voice layer's model calls, behind one interface with four backends.

- anthropic        one Messages API call per request (Anthropic Python SDK >= 1.0)
- anthropic-batch  the Message Batches API: half price, asynchronous; the
                   production path for precomputed runs
- transcript       writes requests to a JSONL file and reads answers from
                   another, so any external runner can answer them (the
                   prototype used Claude Code subagents this way; see EVAL.md)
- mock             deterministic answers for pipeline tests only; results
                   carrying a mock answer are never serialized for the page

Every request is a dict: {id, model, system, user, schema, meta}. Every answer
is {id, model, backend, ok, data, usage, raw, error}.

Model notes: Sonnet 5.5 rejects non-default
sampling parameters, so variance is added by persona diversity, not
temperature. Opus 5.5 can't disable thinking; both run at a low effort here.
Structured outputs go through output_config.format (json_schema).
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import time
from pathlib import Path

from .config import ROOT

# $ per million tokens: input, output, cache read. Batch is half of each.
PRICES = {
    'claude-sonnet-5-5': (2.00, 10.00, 0.20),
    'claude-opus-5-5': (4.00, 20.00, 0.20),
    'claude-haiku-4-5': (1.00, 5.00, 0.10),
}


def cost(model: str, usage: dict, batch: bool = False) -> float:
    p_in, p_out, p_cache = PRICES.get(model, PRICES['claude-sonnet-5-5'])
    fresh = usage.get('input_tokens', 0)
    cached = usage.get('cache_read_input_tokens', 0)
    written = usage.get('cache_creation_input_tokens', 0)
    out = usage.get('output_tokens', 0)
    dollars = (fresh * p_in + written * p_in * 1.25 + cached * p_cache + out * p_out) / 1e6
    return dollars * (0.5 if batch else 1.0)


KEY_FILE = Path.home() / '.config/simulacra/anthropic.env'


def api_key() -> str | None:
    """ANTHROPIC_API_KEY if set, else ~/.config/simulacra/anthropic.env. Never printed or logged."""
    if os.environ.get('ANTHROPIC_API_KEY'):
        return os.environ['ANTHROPIC_API_KEY']
    if KEY_FILE.exists():
        for line in KEY_FILE.read_text().splitlines():
            if line.startswith('ANTHROPIC_API_KEY='):
                return line.split('=', 1)[1].strip()
    return None


def estimate(requests: list[dict], max_tokens: int, batch: bool = False, typical_out: int = 600) -> dict:
    """Dry-run dollars: input at ~4 chars/token (system uncached, to be safe),
    output at a typical `typical_out` tokens (600 fits an interview answer) and
    at the max_tokens worst case."""
    typical = worst = 0.0
    for r in requests:
        tin = (len(r['system']) + len(r['user']) + len(json.dumps(r['schema']))) / 4
        typical += cost(r['model'], {'input_tokens': tin, 'output_tokens': min(typical_out, max_tokens)}, batch)
        worst += cost(r['model'], {'input_tokens': tin, 'output_tokens': max_tokens}, batch)
    return {'requests': len(requests), 'typical': round(typical, 4), 'worst': round(worst, 4)}


def _parse(text: str):
    text = text.strip()
    if text.startswith('```'):
        text = text.strip('`').split('\n', 1)[-1]
    start, end = text.find('{'), text.rfind('}')
    return json.loads(text[start:end + 1])


class Backend:
    name = 'base'

    def run(self, requests: list[dict]) -> list[dict]:
        raise NotImplementedError


class AnthropicBackend(Backend):
    name = 'anthropic'

    def __init__(self, effort: str = 'low', max_tokens: int = 4000):
        import anthropic  # imported lazily: the backbone needs no SDK
        self.anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key())
        self.effort = effort
        self.max_tokens = max_tokens

    def params(self, r: dict) -> dict:
        out = {
            'model': r['model'],
            'max_tokens': self.max_tokens,
            # The system prompt is identical across every agent in a run, so it
            # is the cache prefix.
            'system': [{'type': 'text', 'text': r['system'], 'cache_control': {'type': 'ephemeral'}}],
            'messages': [{'role': 'user', 'content': r['user']}],
            'output_config': {
                'effort': self.effort,
                'format': {'type': 'json_schema', 'schema': r['schema']},
            },
        }
        if 'haiku' in r['model']:
            del out['output_config']['effort']  # Haiku 4.5 rejects effort
        return out

    def _one(self, r: dict) -> dict:
        a = self.anthropic
        for attempt in range(5):
            try:
                msg = self.client.messages.create(**self.params(r))
                if msg.stop_reason == 'refusal':
                    return {'id': r['id'], 'model': r['model'], 'backend': self.name, 'ok': False,
                            'error': f'refusal: {getattr(msg.stop_details, "category", None)}', 'usage': msg.usage.model_dump()}
                text = next(b.text for b in msg.content if b.type == 'text')
                return {'id': r['id'], 'model': r['model'], 'backend': self.name, 'ok': True,
                        'data': json.loads(text), 'usage': msg.usage.model_dump(), 'raw': text}
            except a.RateLimitError:
                time.sleep(2 ** attempt + random.random())
            except a.BadRequestError as e:
                return {'id': r['id'], 'model': r['model'], 'backend': self.name, 'ok': False, 'error': str(e)}
            except a.APIStatusError as e:
                if e.status_code < 500:
                    return {'id': r['id'], 'model': r['model'], 'backend': self.name, 'ok': False, 'error': str(e)}
                time.sleep(2 ** attempt)
            except a.APIConnectionError:
                time.sleep(2 ** attempt)
        return {'id': r['id'], 'model': r['model'], 'backend': self.name, 'ok': False, 'error': 'retries exhausted'}

    def run(self, requests):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as pool:
            return list(pool.map(self._one, requests))


class AnthropicBatchBackend(AnthropicBackend):
    name = 'anthropic-batch'

    def run(self, requests, poll_seconds: int = 30):
        from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
        from anthropic.types.messages.batch_create_params import Request
        batch = self.client.messages.batches.create(requests=[
            Request(custom_id=r['id'], params=MessageCreateParamsNonStreaming(**self.params(r))) for r in requests
        ])
        while self.client.messages.batches.retrieve(batch.id).processing_status != 'ended':
            time.sleep(poll_seconds)
        by_id = {r['id']: r for r in requests}
        out = []
        for res in self.client.messages.batches.results(batch.id):
            r = by_id[res.custom_id]
            if res.result.type != 'succeeded':
                out.append({'id': r['id'], 'model': r['model'], 'backend': self.name, 'ok': False, 'error': res.result.type})
                continue
            msg = res.result.message
            text = next((b.text for b in msg.content if b.type == 'text'), '')
            try:
                data = json.loads(text)
                out.append({'id': r['id'], 'model': r['model'], 'backend': self.name, 'ok': True,
                            'data': data, 'usage': msg.usage.model_dump(), 'raw': text})
            except json.JSONDecodeError as e:
                out.append({'id': r['id'], 'model': r['model'], 'backend': self.name, 'ok': False, 'error': str(e)})
        return out


class TranscriptBackend(Backend):
    """Hands requests to an external runner through files.

    `run` writes every request without an answer to `requests.jsonl` and returns
    the answers already present in `responses.jsonl` (one JSON object per line:
    {"id", "model", "answer": <text or object>}). Call it again after the runner
    has written its answers.
    """
    name = 'transcript'

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def answers(self) -> dict:
        path = self.folder / 'responses.jsonl'
        got = {}
        if path.exists():
            for line in path.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    got[row['id']] = row
        return got

    def run(self, requests):
        got = self.answers()
        pending = [r for r in requests if r['id'] not in got]
        if pending:
            with open(self.folder / 'requests.jsonl', 'w') as f:
                for r in pending:
                    f.write(json.dumps(r) + '\n')
        out = []
        for r in requests:
            row = got.get(r['id'])
            if row is None:
                continue
            try:
                data = row['answer'] if isinstance(row['answer'], dict) else _parse(row['answer'])
                out.append({'id': r['id'], 'model': row.get('model', r['model']), 'backend': self.name, 'ok': True,
                            'data': data, 'usage': row.get('usage', {}), 'raw': row['answer']})
            except Exception as e:  # a malformed answer is logged, not guessed at
                out.append({'id': r['id'], 'model': r['model'], 'backend': self.name, 'ok': False, 'error': repr(e)})
        return out


def merge_answers(folder: Path, requests: list[dict]) -> dict:
    """Fold answers/<batch>.jsonl files into responses.jsonl, checking each
    answer against its request's schema (required keys, enums, p_choice)."""
    folder = Path(folder)
    by_id = {r['id']: r for r in requests}
    good, bad = {}, []
    for f in sorted((folder / 'answers').glob('*.jsonl')):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                req = by_id[row['id']]
                ans = row['answer'] if isinstance(row['answer'], dict) else _parse(row['answer'])
                sch = req['schema']
                missing = [k for k in sch['required'] if k not in ans]
                if missing:
                    raise ValueError(f'missing {missing}')
                for k, spec in sch['properties'].items():
                    if 'enum' in spec and ans.get(k) not in spec['enum']:
                        raise ValueError(f'{k}={ans.get(k)!r} not in enum')
                row['answer'] = ans
                good[row['id']] = row
            except Exception as e:
                bad.append({'file': f.name, 'line': line[:120], 'error': repr(e)})
    with open(folder / 'responses.jsonl', 'w') as out:
        for row in good.values():
            out.write(json.dumps(row) + '\n')
    return {'merged': len(good), 'rejected': bad, 'missing': sorted(set(by_id) - set(good))}


class MockBackend(Backend):
    """Deterministic stand-in answers keyed on the request id. Tests only."""
    name = 'mock'

    def run(self, requests):
        out = []
        for r in requests:
            h = int(hashlib.sha256(r['id'].encode()).hexdigest(), 16)
            rng = random.Random(h)
            kind = r['meta'].get('kind')
            if kind == 'probe':
                data = {'year': 1920, 'label_names': {}, 'winner_label': '', 'winner_name': '', 'confidence': 10}
            else:
                labels = r['meta'].get('labels', ['K', 'M'])
                a = rng.randint(20, 80)
                data = {'able_to_vote': 'yes', 'p_vote': rng.randint(30, 95), 'choice': rng.choice(labels),
                        'p_choice': {labels[0]: a, labels[1]: 100 - a, 'other': 0}, 'confidence': 50,
                        'reason': 'mock', 'quote': 'mock', 'sources_used': []}
            out.append({'id': r['id'], 'model': r['model'], 'backend': self.name, 'ok': True, 'data': data, 'usage': {}})
        return out


def backend(name: str, folder: Path | None = None, effort: str = 'low', max_tokens: int = 4000) -> Backend:
    if name == 'anthropic':
        return AnthropicBackend(effort=effort, max_tokens=max_tokens)
    if name == 'anthropic-batch':
        return AnthropicBatchBackend(effort=effort, max_tokens=max_tokens)
    if name == 'transcript':
        return TranscriptBackend(folder)
    if name == 'mock':
        return MockBackend()
    raise ValueError(name)


# ── Answer cache: an identical request is the same instrument ──
# Keyed on model, system, user and schema (never on meta, run or prompt-version
# labels), so a run that adds one what-if pays only for its new briefs. Only
# live API answers are cached; transcript (subagent) and mock answers never are.

def request_key(r: dict) -> str:
    blob = json.dumps([r['model'], r['system'], r['user'], r['schema']], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


class AnswerCache:
    LIVE = ('anthropic', 'anthropic-batch')

    def __init__(self, runs_dir: Path):
        self.runs = Path(runs_dir)
        self.file = self.runs / '_cache/answers.jsonl'
        self.index = {}
        if self.file.exists():
            for line in self.file.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    self.index[row['key']] = row['answer']
        # Backfill from earlier runs' requests and live answers.
        for req_file in self.runs.glob('*/agents/all_requests.jsonl'):
            ans_file = req_file.parent / 'answers.jsonl'
            if not ans_file.exists():
                continue
            answers = {}
            for line in ans_file.read_text().splitlines():
                if line.strip():
                    g = json.loads(line)
                    if g.get('ok') and g.get('backend') in self.LIVE:
                        answers[g['id']] = g | {'cached_from': req_file.parent.parent.name}
            for line in req_file.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    if r['id'] in answers:
                        self.index.setdefault(request_key(r), answers[r['id']])

    def get(self, r: dict) -> dict | None:
        hit = self.index.get(request_key(r))
        if not hit:
            return None
        return {**hit, 'id': r['id'], 'cached': True, 'usage': {}}

    def put(self, r: dict, answer: dict):
        if not answer.get('ok') or answer.get('backend') not in self.LIVE:
            return
        k = request_key(r)
        self.index[k] = answer
        self.file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file, 'a') as f:
            f.write(json.dumps({'key': k, 'answer': answer}) + '\n')


# ── Spend ledger: every paid call, for the daily cap ──

LEDGER = ROOT / 'sessions/spend.jsonl'
DAILY_DOLLARS = float(os.environ.get('SIMULACRA_DAILY_DOLLARS', '2.0'))


def record_spend(stage: str, dollars: float, run: str = '', note: str = ''):
    if dollars <= 0:
        return
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, 'a') as f:
        f.write(json.dumps({'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'day': time.strftime('%Y-%m-%d'),
                            'stage': stage, 'dollars': round(dollars, 5), 'run': run, 'note': note}) + '\n')


def spent_today() -> float:
    if not LEDGER.exists():
        return 0.0
    day = time.strftime('%Y-%m-%d')
    return sum(json.loads(l)['dollars'] for l in LEDGER.read_text().splitlines() if l.strip() and json.loads(l)['day'] == day)


def guard_daily(worst: float, what: str):
    today = spent_today()
    if today + worst > DAILY_DOLLARS:
        raise SystemExit(f'refusing {what}: ${today:.2f} spent today + ${worst:.2f} worst case > daily cap ${DAILY_DOLLARS:.2f} '
                         '(SIMULACRA_DAILY_DOLLARS)')
