"""Typed what-if intake: a reader's words → a what-if the page can serve.

    python -m simharness.run whatif --text "charlie chaplin ran as an independent" --config configs/live-1920.json
    python -m simharness.run whatif --queue --config configs/live-1920.json    # what the router queued as unknown
    python -m simharness.run research --config configs/live-1920.json          # evidence for the config's what-ifs

Stages, each priced before it is sent and recorded in sessions/spend.jsonl:

1. compile   (research.compile_model, structured): the words become a spec;
             or `same_as` an existing what-if, in which case only its keywords
             grow and the bundle is republished; or not modelable.
2. research  (research.research_model + web search): notes with citations.
3. extract   (research.extract_model, structured): graded findings, each
             grounded in a source the search returned.
4. register  whatifs/<key>.json and whatifs/evidence/<key>.json; the key
             joins the config's what_ifs.
5. run       backbone → plan → ask (identical earlier requests reused) →
             analyze → publish → serve/bundles/<year>.json.

Money: a typed what-if stops at research.whatif_dollars across all stages
(default $0.50), and every stage also checks the daily cap
(SIMULACRA_DAILY_DOLLARS, default $2). A stage whose actual cost exceeds 1.5×
its typical estimate stops the pipeline and says so.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import time
from pathlib import Path

from . import evidence, llm, scenario
from .config import ROOT, RunConfig
from .whatifs import REGISTRY

SESSIONS = ROOT / 'sessions'
QUEUE = SESSIONS / 'queue.jsonl'
DONE = SESSIONS / 'queue-done.jsonl'
FAILED = SESSIONS / 'queue-failed.jsonl'
LOCK = SESSIONS / 'intake.lock'
SERVE_BUNDLES = ROOT / 'serve/bundles'
STATUS = SESSIONS / 'intake-status.json'


class Progress:
    """What the worker is doing, for the router to show while the page waits
    (sessions/intake-status.json: {text, steps: [{text, state}], ts})."""

    def __init__(self, text: str | None):
        self.text, self.steps = (_norm(text) if text else None), []

    def step(self, label: str):
        if not self.text:
            return
        for s in self.steps:
            s['state'] = 'done'
        self.steps.append({'text': label, 'state': 'doing'})
        self._write()

    def finish(self):
        for s in self.steps:
            s['state'] = 'done'
        self._write()

    def _write(self):
        if not self.text:
            return
        SESSIONS.mkdir(exist_ok=True)
        tmp = STATUS.with_suffix('.tmp')
        tmp.write_text(json.dumps({'text': self.text, 'steps': self.steps, 'ts': dt.datetime.now().isoformat(timespec='seconds')}))
        tmp.replace(STATUS)


class Budget:
    def __init__(self, cap: float):
        self.cap, self.spent, self.lines = cap, 0.0, []

    def check(self, worst: float, what: str):
        if self.spent + worst > self.cap:
            raise SystemExit(f'refusing {what}: ${self.spent:.3f} spent on this what-if + ${worst:.3f} worst case > '
                             f'${self.cap:.2f} (research.whatif_dollars)')
        llm.guard_daily(worst, what)

    def add(self, dollars: float, stage: str, typical: float | None = None, note: str = '', record: bool = True):
        self.spent += dollars
        self.lines.append({'stage': stage, 'dollars': round(dollars, 4), 'typical': typical})
        if record:
            llm.record_spend(stage, dollars, note=note)
        if typical and dollars > 0.01 and dollars > 1.5 * typical:
            raise SystemExit(f'STOP: {stage} cost ${dollars:.4f}, more than 1.5x its ${typical:.4f} estimate. '
                             'Everything so far is saved; check the call before going on.')


# Typical output tokens by call (measured: a compile answer ran ~1,300 tokens on Sonnet 5.5).
TYPICAL_OUT = {'compile': 1600, 'compile-retry': 1600, 'extract': 3000}


def _structured(req: dict, max_tokens: int, budget: Budget, stage: str, note: str = '') -> dict:
    from .config import RUNS
    cache = llm.AnswerCache(RUNS)
    hit = cache.get(req)
    if hit:
        print(f'{stage}: reused an identical earlier answer', flush=True)
        return hit['data']
    est = llm.estimate([req], max_tokens, typical_out=TYPICAL_OUT.get(stage, 600))
    print(f'{stage}: ~${est["typical"]} typical, ${est["worst"]} worst ({req["model"]})', flush=True)
    budget.check(est['worst'], stage)
    ans = llm.AnthropicBackend(effort='low', max_tokens=max_tokens)._one(req)
    cache.put(req, ans | {'backend': 'anthropic'})
    budget.add(llm.cost(req['model'], ans.get('usage') or {}), stage, est['typical'], note)
    if not ans.get('ok'):
        raise SystemExit(f'{stage} failed: {ans.get("error")}')
    return ans['data']


def compile_text(text: str, cfg: RunConfig, budget: Budget) -> dict:
    rc = cfg.research
    raw = _structured(scenario.compile_request(text, REGISTRY, cfg.context_cutoff, rc.compile_model), 3000, budget,
                      'compile', text)
    bad = scenario.naming_violations(raw) if raw.get('modelable') else []
    if bad:
        note = ('These sentences name a nominee, a party or the President, which the blinded briefs cannot show. '
                'Rewrite them with the descriptions given: ' + json.dumps(bad))
        raw = _structured(scenario.compile_request(text, REGISTRY, cfg.context_cutoff, rc.compile_model, note), 3000, budget,
                          'compile-retry', text)
    return raw


def reextract(spec: dict, cfg: RunConfig, budget: Budget, have: dict) -> dict:
    """Extraction again from the saved notes (no new search)."""
    notes = {'text': have['notes'], 'sources': have['sources']}
    rc = cfg.research
    extracted = _structured(evidence.extract_request(spec, notes, rc.extract_model), 8000, budget, 'extract', spec['key'])
    ev = {**have, **evidence.ground(extracted, notes, spec.get('about')), 'models': {**have.get('models', {}), 'extract': rc.extract_model},
          'reextracted_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}
    scenario.save_evidence(spec['key'], ev)
    return ev


def research(spec: dict, cfg: RunConfig, budget: Budget, refresh: bool = False, again: bool = False) -> dict:
    """Evidence for one what-if (cached in whatifs/evidence/<key>.json). again: re-extract the saved notes."""
    import anthropic
    key = spec['key']
    have = scenario.load_evidence(key)
    if have and again and have.get('notes'):
        return reextract(spec, cfg, budget, have)
    if have and not refresh:
        return have
    rc = cfg.research
    est = evidence.research_estimate(rc.research_model, rc.max_searches, rc.research_max_tokens)
    print(f'research {key}: ~${est["typical"]} typical, ${est["worst"]} worst ({rc.research_model}, '
          f'≤{rc.max_searches} searches)', flush=True)
    budget.check(est['worst'], 'research')
    client = anthropic.Anthropic(api_key=llm.api_key())
    notes = evidence.research(client, spec, {'year': cfg.election, 'day': cfg.election_day}, rc.research_model,
                              rc.max_searches, 'low', rc.research_max_tokens)
    # Priced against the estimate only after the notes are saved (a stop mustn't waste them).
    budget.add(notes['dollars'], 'research', None, key)
    print(f'  {len(notes["queries"])} searches, {len(notes["sources"])} sources '
          f'({sum(s["tier"] == "A" for s in notes["sources"])} scholarly or official), ${notes["dollars"]}', flush=True)
    extracted = _structured(evidence.extract_request(spec, notes, rc.extract_model), 8000, budget, 'extract', key)
    ev = evidence.ground(extracted, notes, spec.get('about'))
    ev.update({'key': key, 'version': evidence.EVIDENCE_VERSION,
               'researched_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
               'models': {'research': rc.research_model, 'extract': rc.extract_model}, 'queries': notes['queries'],
               'sources': notes['sources'], 'notes': notes['text'], 'prompt': notes['prompt'], 'usage': notes['usage'],
               'dollars': round(sum(x['dollars'] for x in budget.lines if x['stage'] in ('research', 'extract')), 4)})
    scenario.save_evidence(key, ev)
    if notes['dollars'] > 0.01 and notes['dollars'] > 1.5 * est['typical']:
        raise SystemExit(f'STOP: research cost ${notes["dollars"]:.4f}, more than 1.5x its ${est["typical"]:.4f} estimate. '
                         f'The evidence is saved in whatifs/evidence/{key}.json; check the search volume before going on.')
    return ev


def documented_positions(spec: dict, ev: dict, cutoff: str):
    """A candidate's positions from the record, when the research found any on
    or before the cutoff (masked like any brief text); else they stay inferred."""
    keep = []
    for p in ev.get('actor_positions', []):
        d = p.get('date', '')
        try:
            ok = dt.date.fromisoformat(d[:10]).isoformat() <= cutoff
        except ValueError:
            m = re.search(r'\b(1[6-9]\d\d)\b', d)
            ok = bool(m) and int(m.group(1)) < int(cutoff[:4])
        if ok:
            keep.append(scenario.clean_position(p['text']))
    if keep:
        spec['candidate']['positions'] = keep[:3]
        spec['candidate']['positions_source'] = 'documented'


def _add_to_config(config_path: Path, key: str):
    raw = json.loads(config_path.read_text())
    if key not in raw['what_ifs']:
        raw['what_ifs'].append(key)
        config_path.write_text(json.dumps(raw, indent=2) + '\n')


def run_pipeline(config_path: Path, budget: Budget, publish_only: bool = False, progress: Progress | None = None) -> dict:
    from .run import Run
    progress = progress or Progress(None)
    run = Run(RunConfig.load(config_path))
    if not publish_only:
        if not (run.dir / 'fit.pkl').exists():
            run.backbone()
        run.plan()
        progress.step(f'Interviewing voters in your {run.cfg.election}, with the real one as a control.')
        asked = run.ask(cap=max(0.0, budget.cap - budget.spent))
        budget.add(asked['dollars'], 'ask', None, record=False)  # ask records its own spend
        progress.step('Comparing the interviews with the historical record.')
        run.analyze()
    progress.step(f'Rerunning the {run.cfg.election} election 100 times.')
    run.publish()
    SERVE_BUNDLES.mkdir(parents=True, exist_ok=True)
    src = run.dir / 'published' / f'{run.cfg.election}.json'
    shutil.copyfile(src, SERVE_BUNDLES / f'{run.cfg.election}.json')
    return {'run': run.id, 'bundle': str(src)}


def report(year: int, key: str) -> dict:
    b = json.loads((SERVE_BUNDLES / f'{year}.json').read_text())
    r = b['runs'].get(key) or {}
    return {'key': key, 'label': REGISTRY[key]['label'], 'summary': r.get('summary'), 'ev': r.get('ev'),
            'confidence': r.get('confidenceTier'), 'flags': r.get('confidenceFlags'),
            'evidence': [{'strength': e['strength'], 'agreement': e['agreement'], 'detail': e.get('agreementDetail')}
                         for e in r.get('evidence', [])]}


def whatif(text: str, config_path: str | Path, refresh: bool = False) -> dict:
    config_path = Path(config_path)
    cfg = RunConfig.load(config_path)
    budget = Budget(cfg.research.whatif_dollars)
    progress = Progress(text)
    progress.step('Turning your words into a change I can model.')
    raw = compile_text(text, cfg, budget)
    if not raw['modelable']:
        progress.finish()
        return {'status': 'not-modelable', 'why': raw['why_not'], 'dollars': round(budget.spent, 4)}
    if raw['same_as'] in REGISTRY:
        key = raw['same_as']
        scenario.add_words(key, raw['words'] + [text.lower().strip()[:80]])
        in_config = key in cfg.what_ifs
        _add_to_config(config_path, key)
        progress.step(f'That’s {REGISTRY[key]["label"]}, which I’ve modelled already.')
        out = run_pipeline(config_path, budget, publish_only=in_config, progress=progress)
        progress.finish()
        return {'status': 'keyword', 'key': key, **out, 'dollars': round(budget.spent, 4), 'costs': budget.lines,
                'report': report(cfg.election, key)}
    spec = scenario.finalize(raw, text, REGISTRY, cfg.research.compile_model)
    progress.step(f'Setting the scene: autumn {cfg.election}…')
    ev = research(spec, cfg, budget, refresh)
    n = len(ev.get('findings', []))
    progress.step(f'Clarifying historical context: {n or "no"} finding{"" if n == 1 else "s"}.')
    if spec['kind'] == 'candidate' and spec['candidate']['positions_source'] != 'documented':
        documented_positions(spec, ev, cfg.context_cutoff)
    scenario.save_spec(spec)
    REGISTRY[spec['key']] = scenario.bind(spec)
    _add_to_config(config_path, spec['key'])
    out = run_pipeline(config_path, budget, progress=progress)
    progress.finish()
    return {'status': 'modelled', 'key': spec['key'], **out, 'dollars': round(budget.spent, 4), 'costs': budget.lines,
            'report': report(cfg.election, spec['key'])}


def research_config(config_path: str | Path, refresh: bool = False, only: str | None = None, again: bool = False) -> dict:
    """Evidence for every what-if in a config that lacks it (pre-registered ones included: there it grades confidence only)."""
    cfg = RunConfig.load(config_path)
    keys = [k for k in cfg.what_ifs if not only or k == only]
    budget = Budget(cfg.research.whatif_dollars * max(1, len(keys)))
    out = {}
    for k in keys:
        ev = research({**REGISTRY[k], 'key': k}, cfg, budget, refresh, again)
        out[k] = {'strength': evidence.strength(ev)['level'], 'findings': len(ev['findings']), 'summary': ev['summary'][:200]}
    return {'what_ifs': out, 'dollars': round(budget.spent, 4)}


# ── The router's queue ──

def _norm(text: str) -> str:
    return ' '.join(text.lower().split())


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _config_for(year: int, fallback: Path | None = None) -> Path | None:
    """The worker's own config when it is that year's; None when the year isn't simulated."""
    return fallback if fallback and Path(fallback).exists() and RunConfig.load(fallback).election == year else None


def process_queue(config_path: str | Path, limit: int = 3) -> list[dict]:
    """Model up to `limit` distinct queued (year, text) pairs, oldest first, within the caps."""
    SESSIONS.mkdir(exist_ok=True)
    if LOCK.exists() and _pid_alive(int(LOCK.read_text().strip() or 0)):
        return [{'status': 'busy', 'pid': LOCK.read_text().strip()}]
    LOCK.write_text(str(os.getpid()))
    try:
        done = set()
        for l in DONE.read_text().splitlines() if DONE.exists() else []:
            if l.strip():
                x = json.loads(l)
                done.add((x.get('year', 1920), x['text']))
        pending = []
        for l in QUEUE.read_text().splitlines() if QUEUE.exists() else []:
            if l.strip():
                q = json.loads(l)
                key = (int(q.get('year') or 1920), _norm(q['text']))
                if key not in done and key not in pending:
                    pending.append(key)
        results = []
        for year, t in pending[:limit]:
            cfg_path = _config_for(year, Path(config_path))
            try:
                if cfg_path is None:
                    r = {'status': 'not-modelable', 'why': f'I haven’t simulated {year} yet.'}
                else:
                    r = whatif(t, cfg_path)
            except (SystemExit, Exception) as e:
                # A cap or cost stop, or a bug: the text stays queued (not in DONE),
                # and the waiting page is told why (FAILED, read by the router).
                r = {'text': t, 'year': year, 'status': 'stopped' if isinstance(e, SystemExit) else 'error', 'why': str(e) or repr(e)}
                with open(FAILED, 'a') as f:
                    f.write(json.dumps(r | {'at': time.time()}) + '\n')
                results.append(r)
                break
            with open(DONE, 'a') as f:
                f.write(json.dumps({'text': t, 'year': year, 'ts': dt.datetime.now().isoformat(timespec='seconds'), 'status': r['status'],
                                    'key': r.get('key'), 'why': r.get('why'), 'dollars': r.get('dollars')}) + '\n')
            results.append({'text': t, **r})
        return results
    finally:
        LOCK.unlink(missing_ok=True)
