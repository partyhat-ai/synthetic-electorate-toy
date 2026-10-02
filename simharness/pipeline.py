"""The pipeline's stages: backbone, plan, ask, analyze and evaluate. Each writes
into runs/<run id>/ and can be rerun alone; run.py is the command line.
"""
from __future__ import annotations

import json
import pickle
import random
import time

import numpy as np

from . import agentlayer, aggregate, backbone, cohorts as cohorts_mod, data, evaluate, llm, paired, quotes
from .config import RUNS, RunConfig
from .stats import logit
from .whatifs import REGISTRY, apply_effects


CAND = {0: 'Harding', 1: 'Cox', 2: 'another candidate'}


class Run:
    def __init__(self, cfg: RunConfig):
        self.cfg = cfg
        self.inp, self.extras = data.load(cfg)
        self.manifest = self.extras['manifest']
        self.id = cfg.run_id(self.manifest)
        # Short model names in request ids; the analysis pairs on these, not on a hardcoded 'sonnet'.
        self.bulk = agentlayer.SHORT.get(cfg.agents.bulk_model, cfg.agents.bulk_model)
        self.check = agentlayer.SHORT.get(cfg.agents.check_model, cfg.agents.check_model)
        self.models = tuple(dict.fromkeys((self.bulk, self.check)))
        self.year = cfg.election
        self.cand = CAND
        self.dir = RUNS / self.id
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / 'config.json').write_text(json.dumps({'run_id': self.id, 'config': cfg.to_dict(),
                                                          'data': self.manifest}, indent=2))

    # ── backbone ──
    def backbone(self):
        fit = backbone.fit(self.inp, self.cfg.draws, self.cfg.seed)
        with open(self.dir / 'fit.pkl', 'wb') as f:
            pickle.dump(fit, f)
        return fit

    def fit(self):
        p = self.dir / 'fit.pkl'
        if not p.exists():
            return self.backbone()
        with open(p, 'rb') as f:
            return pickle.load(f)

    def state_index(self, fit):
        states = fit.diagnostics['states']
        return states, np.array([states.index(s) for s in fit.cells.state])

    # ── agents ──
    def plan(self):
        fit = self.fit()
        cells = fit.cells
        cohorts, cell_to = cohorts_mod.build(cells, cap=self.cfg.agents.max_cohorts)
        agents, reqs = agentlayer.build_requests(self.cfg, cohorts, self.extras, self.inp, REGISTRY)
        out = self.dir / 'agents'
        out.mkdir(exist_ok=True)
        (out / 'cohorts.json').write_text(json.dumps({'cohorts': cohorts, 'cell_to': {int(k): v for k, v in cell_to.items()}}, indent=1))
        (out / 'agents.json').write_text(json.dumps(agents, indent=1, default=str))
        with open(out / 'all_requests.jsonl', 'w') as f:
            for r in reqs:
                f.write(json.dumps(r) + '\n')
        counts = {}
        for r in reqs:
            k = (r['meta']['arm'].split(':')[0], r['model'])
            counts[str(k)] = counts.get(str(k), 0) + 1
        ag = self.cfg.agents
        return {'agents': len(agents), 'requests': len(reqs), 'by_arm_model': counts, 'cohorts': len(cohorts),
                'cohort_keys': sorted(cohorts, key=lambda k: -cohorts[k].get('adults', 0))[:12],
                'estimate': llm.estimate(reqs, ag.max_tokens, ag.backend == 'anthropic-batch')}

    def requests(self):
        return [json.loads(l) for l in (self.dir / 'agents/all_requests.jsonl').read_text().splitlines() if l.strip()]

    def ask(self):
        ag = self.cfg.agents
        be = llm.backend(ag.backend, self.dir / 'agents/transcript', ag.effort, ag.max_tokens)
        reqs = self.requests()
        merged = None
        if self.cfg.agents.backend == 'transcript':
            merged = llm.merge_answers(self.dir / 'agents/transcript', reqs)
            (self.dir / 'agents/transcript/merge_report.json').write_text(json.dumps(merged, indent=1))
        path = self.dir / 'agents/answers.jsonl'
        have = set()
        if path.exists():
            have = {json.loads(l)['id'] for l in path.read_text().splitlines() if l.strip() and json.loads(l).get('ok')}
        todo = [r for r in reqs if r['id'] not in have]
        batch = ag.backend == 'anthropic-batch'
        est = llm.estimate(todo, ag.max_tokens, batch)
        print(f"estimate: {est['requests']} requests, ~${est['typical']} typical, ${est['worst']} worst case", flush=True)
        if ag.max_requests is not None and len(todo) > ag.max_requests:
            raise SystemExit(f'refusing: {len(todo)} requests > max_requests {ag.max_requests}')
        if ag.max_dollars is not None and est['worst'] > ag.max_dollars:
            raise SystemExit(f"refusing: worst case ${est['worst']} > max_dollars {ag.max_dollars}")
        t0 = time.time()
        got = be.run(todo) if todo else []
        spent = sum(llm.cost(g['model'], g.get('usage') or {}, batch) for g in got)
        with open(path, 'a') as f:
            for g in got:
                f.write(json.dumps(g) + '\n')
        return {'sent': len(todo), 'seconds': round(time.time() - t0, 1), 'dollars': round(spent, 4),
                'answered': sum(1 for g in got if g.get('ok')), 'failed': sum(1 for g in got if not g.get('ok')),
                'merge': None if merged is None else {'merged': merged['merged'], 'rejected': len(merged['rejected']), 'missing': len(merged['missing'])}}

    def answers(self) -> dict:
        path = self.dir / 'agents/answers.jsonl'
        out = {}
        if path.exists():
            for l in path.read_text().splitlines():
                if l.strip():
                    g = json.loads(l)
                    if g.get('ok'):
                        out[g['id']] = g
        return out

    # ── analysis ──
    def analyze(self):
        fit = self.fit()
        reqs = {r['id']: r for r in self.requests()}
        ans = self.answers()
        agents = {a['id']: a for a in json.loads((self.dir / 'agents/agents.json').read_text())}
        co = json.loads((self.dir / 'agents/cohorts.json').read_text())
        cohorts, cell_to = co['cohorts'], {int(k): v for k, v in co['cell_to'].items()}
        rng = np.random.default_rng(self.cfg.seed + 11)
        pyrng = random.Random(self.cfg.seed + 11)

        def norm(rid):
            if rid not in ans:
                return None
            lab = reqs[rid]['meta']['label_of']
            row = paired.normalize(ans[rid]['data'], {v: k for k, v in lab.items()})
            if row:
                d = ans[rid]['data']
                row.update({'reason': d.get('reason', ''), 'quote': d.get('quote', ''), 'sources_used': d.get('sources_used', []),
                            'agent': reqs[rid]['meta']['agent'], 'model': ans[rid]['model']})
            return row

        # Backbone cohort shares in the point draw's median over draws
        w = fit.world
        v = w.adults * w.can * w.t
        backbone_r2, backbone_turn, backbone_o = {}, {}, {}
        for k in cohorts:
            idx = [i for i, kk in cell_to.items() if kk == k]
            vv = v[:, idx]
            R = (vv * w.share[:, idx, 0]).sum(axis=1)
            Dm = (vv * w.share[:, idx, 1]).sum(axis=1)
            # per legally eligible adult (what an agent's p_vote means), exclusion included
            elig = (w.adults[:, idx] * (w.can[:, idx] + w.barred_by['excluded'][:, idx])).sum(axis=1)
            backbone_r2[k] = float(np.median(R / np.maximum(R + Dm, 1e-9)))
            backbone_turn[k] = float(np.median(vv.sum(axis=1) / np.maximum(elig, 1e-9)))
            backbone_o[k] = float(np.median((vv * w.share[:, idx, 2]).sum(axis=1) / np.maximum(vv.sum(axis=1), 1e-9)))

        # L1 recall probe (the winner is Harding)
        won = 0
        probes = []
        for rid, r in reqs.items():
            if r['meta']['kind'] != 'probe' or rid not in ans:
                continue
            d = ans[rid]['data']
            lab = r['meta']['label_of']
            cands = {k: str(v).lower() for k, v in (d.get('candidates') or {}).items()}
            probes.append({
                'cohort': r['meta']['cohort'],
                'year': str(d.get('year', '')).strip().startswith(str(self.year)),
                'names': all(self.cand[i].lower() in cands.get(lab[p], '') for i, p in enumerate('RD') if p in lab),
                'winner': self.cand[won].lower() in str(d.get('winner_name', '')).lower() or d.get('winner_label') == lab.get('RDO'[won]),
            })
        by_cohort = {}
        for p in probes:
            by_cohort.setdefault(p['cohort'], []).append(p)
        exposed = {k for k, ps in by_cohort.items() if np.mean([p['winner'] for p in ps]) > 0.5}
        l1 = {'n': len(probes),
              'year_rate': float(np.mean([p['year'] for p in probes])) if probes else None,
              'names_rate': float(np.mean([p['names'] for p in probes])) if probes else None,
              'winner_rate': float(np.mean([p['winner'] for p in probes])) if probes else None,
              'exposed_cohorts': sorted(exposed),
              'by_cohort': {k: {'n': len(ps), 'winner_rate': float(np.mean([p['winner'] for p in ps]))} for k, ps in by_cohort.items()}}
        nationally_exposed = bool(l1['winner_rate'] is not None and l1['winner_rate'] > 0.5)

        # L2 label swap
        swaps = []
        for rid, r in reqs.items():
            if r['meta']['kind'] != 'swap' or rid not in ans:
                continue
            ctl = norm(f'control|{r["meta"]["agent"]}|{self.bulk}')
            if not ctl or ctl['choice'] not in ('R', 'D'):
                continue
            chosen = ans[rid]['data'].get('choice')
            plat = {x['label']: x['platform_of'] for x in r['meta']['displayed']}
            if chosen not in plat:
                continue
            swaps.append({'follows_platform': plat[chosen] == ctl['choice'],
                          'follows_label': chosen == r['meta']['label_of'][ctl['choice']]})
        l2 = {'n': len(swaps), 'label_rate': float(np.mean([s['follows_label'] for s in swaps])) if swaps else None,
              'platform_rate': float(np.mean([s['follows_platform'] for s in swaps])) if swaps else None}

        # Paired effects per what-if (agent-mode what-ifs apply them; others are cross-checks)
        effects, pairs_out = {}, {}
        for wk in self.cfg.what_ifs:
            pairs = {}
            for aid, a in agents.items():
                if a['group'] == 'foreign_white_alien' and REGISTRY[wk]['mode'] == 'backbone':
                    continue  # planned in error for p1 (brief contradicted itself); excluded, see EVAL.md
                for model in self.models:
                    c, f = norm(f'control|{aid}|{model}'), norm(f'cf:{wk}|{aid}|{model}')
                    if c and f:
                        pairs.setdefault(a['cohort'], []).append((c, f, a['paraphrase'], model))
            if not pairs:
                continue
            region_of = {k: cohorts[k]['region'] for k in pairs}
            eff = paired.effects(pairs, backbone_r2, region_of, 200, rng, exposed=exposed if not nationally_exposed else set(pairs),
                                 weights={k: cohorts[k]['adults'] for k in pairs})
            # A3: paraphrase and model spread of the national two-party effect
            by_para, by_model = {}, {}
            for k, ps in pairs.items():
                for c, f, p, m in ps:
                    by_para.setdefault(p, []).append((c, f))
                    by_model.setdefault(m, []).append((c, f))
            def nat(ps):
                return paired.diff(paired.cohort_stats([x[1] for x in ps]), paired.cohort_stats([x[0] for x in ps]))
            eff['by_paraphrase'] = {str(p): nat(ps) for p, ps in by_para.items()}
            eff['by_model'] = {m: nat(ps) for m, ps in by_model.items()}
            # the Sonnet/Opus comparison uses only agents asked on both
            both = [(c, f, m) for ps in pairs.values() for c, f, p, m in ps]
            ids_opus = {c['agent'] for c, f, m in both if m == self.check}
            shared = {m: [(c, f) for c, f, mm in both if mm == m and c['agent'] in ids_opus] for m in self.models}
            eff['shared_subsample'] = {m: nat(ps) for m, ps in shared.items() if ps}
            effects[wk] = eff
            pairs_out[wk] = {k: [{'control': c, 'cf': f, 'paraphrase': p, 'model': m} for c, f, p, m in ps] for k, ps in pairs.items()}

        # A2 variance compression (control, sonnet)
        a2 = []
        for k in cohorts:
            rows = [norm(f'control|{aid}|{self.bulk}') for aid, a in agents.items() if a['cohort'] == k]
            rows = [r for r in rows if r and r['p_vote'] > 0 and not np.isnan(r['R'])]
            if len(rows) < 2:
                continue
            ch = [r['choice'] for r in rows]
            top = max(ch.count(x) for x in set(ch)) / len(ch)
            r2 = [r['R'] / max(r['R'] + r['D'], 1e-9) for r in rows]
            a2.append({'cohort': k, 'n': len(rows), 'sd_R2': float(np.std(r2)), 'modal_share': top,
                       'backbone_r2': backbone_r2[k], 'homogenized': bool(top >= 0.9 and 0.2 <= backbone_r2[k] <= 0.8)})
        eligible_a2 = [x for x in a2 if 0.2 <= x['backbone_r2'] <= 0.8]
        a2s = {'cohorts': a2, 'homogenization_index': float(np.mean([x['homogenized'] for x in eligible_a2])) if eligible_a2 else None,
               'eligible_cohorts': len(eligible_a2)}

        # A4 stereotype audit
        reasons = [norm(rid) for rid in reqs if rid.startswith(('control|', 'cf:')) and rid in ans]
        a4 = quotes.audit([r for r in reasons if r], 0.2, pyrng)

        # A1 cohort bias and TVD (control, sonnet)
        a1 = []
        for k in cohorts:
            rows = [norm(f'control|{aid}|{self.bulk}') for aid, a in agents.items() if a['cohort'] == k]
            rows = [r for r in rows if r]
            if not rows:
                continue
            st = paired.cohort_stats(rows)
            ch = [r['choice'] for r in rows]
            agent_dist = [ch.count('R'), ch.count('D'), ch.count('O'), ch.count('home') + ch.count('barred')]
            t = backbone_turn[k]
            bb = backbone_r2[k]
            bb_dist = [t * bb, t * (1 - bb), 0.0, 1 - t]
            a1.append({'cohort': k, 'label': cohorts[k]['label'], 'n': len(rows),
                       'agent_turnout': st['turnout'], 'backbone_turnout': t,
                       'agent_r2': st['R2'], 'backbone_r2': bb,
                       'bias_logit': float(logit(st['R2']) - logit(bb)) if not np.isnan(st['R2']) else None,
                       'tvd': float(0.5 * np.abs(np.array(agent_dist) / max(sum(agent_dist), 1) - np.array(bb_dist) / sum(bb_dist)).sum()),
                       'exposed': k in exposed})

        result = {'l1': l1, 'l2': l2, 'a1': a1, 'a2': a2s, 'a4': a4, 'nationally_exposed': nationally_exposed,
                  'effects': {wk: {'national': e['national'], 'national_bias': e['national_bias'],
                                   'by_paraphrase': e['by_paraphrase'], 'by_model': e['by_model'],
                                   'shared_subsample': e.get('shared_subsample'),
                                   'cohorts': {k: {kk: vv for kk, vv in c.items() if kk != 'draws'} for k, c in e['cohorts'].items()}}
                              for wk, e in effects.items()}}
        (self.dir / 'analysis.json').write_text(json.dumps(result, indent=1, default=float))
        with open(self.dir / 'effects.pkl', 'wb') as f:
            pickle.dump({'effects': effects, 'pairs': pairs_out, 'exposed': exposed,
                         'nationally_exposed': nationally_exposed}, f)
        return result

    def uncertainty_budget(self, what_if: str, draws: int = 200) -> dict:
        """Spread of the what-if's national R two-party share and Harding EV:
        full, with population noise off, and with only the agent layer varying
        (one backbone draw, all effect draws)."""
        fit = self.fit()
        states, sidx = self.state_index(fit)
        ev = self.inp.ev.reindex(states).fillna(0).to_numpy()
        spec = REGISTRY[what_if]
        eff = pickle.load(open(self.dir / 'effects.pkl', 'rb')) if (self.dir / 'effects.pkl').exists() else None
        co = json.loads((self.dir / 'agents/cohorts.json').read_text()) if (self.dir / 'agents/cohorts.json').exists() else None
        cell_to = [co['cell_to'][str(i)] for i in range(len(fit.cells))] if co else []

        def measure(f, world):
            if spec['mode'] == 'backbone':
                world = spec['apply'](f, world, self.inp)
            elif eff and what_if in eff['effects']:
                world = apply_effects(f, world, cell_to, eff['effects'][what_if]['cohorts'])
            else:
                return None
            sv = aggregate.by_state(world, sidx, len(states))
            out = aggregate.outcome(sv, ev)
            nat = sv.sum(axis=1)
            return {'r2_sd': float(np.std(nat[:, 0] / (nat[:, 0] + nat[:, 1])) * 100), 'ev_sd': float(np.std(out['ev'][:, 0]))}

        full = measure(fit, fit.world)
        zero = {k: 0.0 for k in backbone.GROUPS}
        no_pop = backbone.fit(self.inp, draws, self.cfg.seed, pop_cv=zero)
        params_only = measure(no_pop, no_pop.world)
        agents_only = None
        if spec['mode'] == 'agents' and eff and what_if in eff['effects']:
            w = fit.world
            one = aggregate.World(adults=np.repeat(w.adults[:1], draws, 0), can=np.repeat(w.can[:1], draws, 0),
                                  t=np.repeat(w.t[:1], draws, 0), share=np.repeat(w.share[:1], draws, 0),
                                  barred_by={k: np.repeat(v[:1], draws, 0) for k, v in w.barred_by.items()})
            agents_only = measure(fit, one)
        return {'what_if': what_if, 'full': full, 'backbone_params_only': params_only, 'agents_only': agents_only,
                'note': 'SD in points of the national R two-party share and in Harding EV. Population share ≈ full − params-only (variances).'}

    # ── evaluate ──
    def evaluate(self):
        from . import benchmarks
        fit = self.fit()
        states, sidx = self.state_index(fit)
        base_votes = aggregate.by_state(fit.world, sidx, len(states))
        checks = [evaluate.r1_reproduction(fit, self.inp, base_votes)]
        ho = evaluate.holdout(fit, self.inp, self.cfg.holdout, self.cfg.draws, self.cfg.seed)
        checks += ho['checks']
        checks += benchmarks.natural_experiment(fit, self.inp, self.extras)
        an = json.loads((self.dir / 'analysis.json').read_text()) if (self.dir / 'analysis.json').exists() else None
        checks += benchmarks.agent_checks(an, fit, self, self.extras)
        summary = {'passed': sum(1 for c in checks if c['pass'] is True),
                   'failed': [c['id'] for c in checks if c['pass'] is False],
                   'not_run': [c['id'] for c in checks if c['pass'] is None]}
        budget = [self.uncertainty_budget(k) for k in self.cfg.what_ifs]
        out = {'summary': summary, 'checks': checks, 'holdout_rows': ho['rows'], 'uncertainty_budget': budget}
        (self.dir / 'validation.json').write_text(json.dumps(out, indent=1, default=float))
        return out
