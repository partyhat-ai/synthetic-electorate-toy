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
import random
import time
from pathlib import Path

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
        self.client = anthropic.Anthropic()
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
