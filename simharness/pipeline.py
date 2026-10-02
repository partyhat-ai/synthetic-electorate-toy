"""The pipeline's stages other than publish (publish.py): backbone, plan, ask,
analyze, verify, dryrun and evaluate. Each writes into runs/<run id>/ and can be
rerun alone; run.py is the command line.
"""
from __future__ import annotations

import json
import pickle
import random
import time

import numpy as np

from . import agentlayer, aggregate, backbone, cohorts as cohorts_mod, data, evaluate, evidence, llm, paired, quotes, scenario, serialize
from .config import RUNS, RunConfig
from .geo import STATE_NAME
from .publish import Publisher
from .stats import logit
from .whatifs import REGISTRY, apply_effects, for_year


class Run(Publisher):
    def __init__(self, cfg: RunConfig):
        self.cfg = cfg
        self.inp, self.extras = data.load(cfg)
        # Compiled what-ifs' specs and every what-if's evidence are part of the instrument.
        self.manifest = {**self.extras['manifest'], **scenario.manifest(cfg.what_ifs)}
        self.id = cfg.run_id(self.manifest)
        # Short model names in request ids; the analysis pairs on these, not on a hardcoded 'sonnet'.
        self.bulk = agentlayer.SHORT.get(cfg.agents.bulk_model, cfg.agents.bulk_model)
        self.check = agentlayer.SHORT.get(cfg.agents.check_model, cfg.agents.check_model)
        self.models = tuple(dict.fromkeys((self.bulk, self.check)))
        # The election's profile: names, sources and how the robot speaks of it.
        self.prof = self.extras['profile']
        self.year = cfg.election
        n = self.prof['names']
        # An unopposed year's empty line (1789 D, 1820 R) still needs a printable name.
        self.cand = {0: n['R'] or 'no candidate', 1: n['D'] or 'no candidate', 2: n['O']}
        self.dir = RUNS / self.id
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / 'config.json').write_text(json.dumps({'run_id': self.id, 'config': cfg.to_dict(),
                                                          'data': self.manifest}, indent=2))

    # ── backbone ──
    def backbone(self):
        if self.extras.get('base_inp') is not None:
            # A carried-forward year: fit the base year, then recalibrate to this year's returns.
            base = backbone.fit(self.extras['base_inp'], self.cfg.draws, self.cfg.seed)
            fit = backbone.carry_forward(base, self.inp, self.year, self.cfg.seed)
        elif self.year != 1920:
            # Every other year: calibrated exactly to its own returns, group splits from priors (backbone.general_fit).
            fit = backbone.general_fit(self.inp, self.year, self.cfg.draws, self.cfg.seed)
        else:
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
        cohorts, cell_to = cohorts_mod.build(cells, cap=self.cfg.agents.max_cohorts, year=self.year)
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

    def ask(self, cap: float | None = None):
        """cap: an extra dollar ceiling from the caller (a typed what-if's remaining budget)."""
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
        live = ag.backend in llm.AnswerCache.LIVE
        cache = llm.AnswerCache(RUNS) if live else None
        reused = [c for c in (cache.get(r) for r in todo) if c] if cache else []
        todo = [r for r in todo if r['id'] not in {c['id'] for c in reused}]
        batch = ag.backend == 'anthropic-batch'
        est = llm.estimate(todo, ag.max_tokens, batch)
        print(f"estimate: {est['requests']} requests, ~${est['typical']} typical, ${est['worst']} worst case"
              f" ({len(reused)} reused from identical earlier requests)", flush=True)
        if ag.max_requests is not None and len(todo) > ag.max_requests:
            raise SystemExit(f'refusing: {len(todo)} requests > max_requests {ag.max_requests}')
        if ag.max_dollars is not None and est['worst'] > ag.max_dollars:
            raise SystemExit(f"refusing: worst case ${est['worst']} > max_dollars {ag.max_dollars}")
        if cap is not None and est['worst'] > cap:
            raise SystemExit(f"refusing: worst case ${est['worst']} > ${cap:.3f} left for this what-if")
        if live and todo:
            llm.guard_daily(est['worst'], 'ask')
        t0 = time.time()
        got = be.run(todo) if todo else []
        spent = sum(llm.cost(g['model'], g.get('usage') or {}, batch) for g in got)
        if live:
            llm.record_spend('ask', spent, self.id)
            by_id = {r['id']: r for r in todo}
            for g in got:
                cache.put(by_id[g['id']], g)
        with open(path, 'a') as f:
            for g in got + reused:
                f.write(json.dumps(g) + '\n')
        out = {'sent': len(todo), 'reused': len(reused), 'seconds': round(time.time() - t0, 1), 'dollars': round(spent, 4),
               'answered': sum(1 for g in got if g.get('ok')), 'failed': sum(1 for g in got if not g.get('ok')),
               'merge': None if merged is None else {'merged': merged['merged'], 'rejected': len(merged['rejected']), 'missing': len(merged['missing'])}}
        if spent > 0.01 and spent > 1.5 * est['typical']:
            raise SystemExit(f"STOP: ask cost ${spent:.4f}, more than 1.5x its ${est['typical']} estimate. Answers are saved; "
                             f"check output lengths before the next run. {json.dumps(out)}")
        return out

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

        # L1 recall probe (the winner is the historical one: R in 1920, D in 1960)
        states_, sidx_ = self.state_index(fit)
        won = int(np.argmax(aggregate.outcome(aggregate.by_state(fit.world, sidx_, len(states_))[:1],
                                              self.inp.ev.reindex(states_).fillna(0).to_numpy(), self._fixed_ev(states_), self._split_ev(states_), o_single=self._o_single(states_))['ev'][0]))
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
            pairs, checks = {}, []
            for aid, a in agents.items():
                if a['group'] == 'foreign_white_alien' and REGISTRY[wk]['mode'] == 'backbone':
                    continue  # planned in error for p1 (brief contradicted itself); excluded, see EVAL.md
                for model in self.models:
                    fid = f'cf:{wk}|{aid}|{model}'
                    c, f = norm(f'control|{aid}|{model}'), norm(fid)
                    chk = reqs[fid]['meta'].get('news_check') if fid in reqs else None
                    if c and f and chk:
                        # p5 manipulation check: a person who took the news to be about the
                        # other candidate answered a different question; left out, and counted.
                        got = ans[fid]['data'].get('news_about')
                        checks.append({'agent': aid, 'expected': chk['expected'], 'got': got, 'ok': got == chk['expected']})
                        if got != chk['expected']:
                            continue
                    if c and f:
                        pairs.setdefault(a['cohort'], []).append((c, f, a['paraphrase'], model))
            misread = {'checked': len(checks), 'misread': sum(not x['ok'] for x in checks), 'rows': checks}
            if not pairs and checks:
                # Everyone misread the change: nothing was measured, so nothing moves.
                zero = {k: {'mean': 0.0, 'lo': 0.0, 'hi': 0.0} for k in ('dt', 'dr', 'do')}
                effects[wk] = {'cohorts': {}, 'regions': {}, 'national': zero, 'national_bias': 0.0, 'by_paraphrase': {},
                               'by_model': {}, 'manipulation': misread, 'blended': False,
                               'agreement': {'verdict': 'untested', 'detail': 'Every interview misread the change.', 'measures': []},
                               'agent_stats': {'n': 0, 'measure': 'dr', 'spans_zero': True, 'paraphrase_flip': False,
                                               'exposed': nationally_exposed, 'checked': misread['checked'], 'misread': misread['misread']}}
                pairs_out[wk] = {}
                continue
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
            # History: does the record agree with the interviews? For compiled
            # (exploratory) what-ifs the evidence is also a prior on each cohort.
            spec, ev = REGISTRY[wk], scenario.load_evidence(wk)
            wts = {k: cohorts[k]['adults'] for k in pairs}
            tot = sum(wts.values()) or 1.0
            nat_base = {m: sum(b[k] * wts[k] for k in pairs) / tot
                        for m, b in (('turnout', backbone_turn), ('r2', backbone_r2), ('o', backbone_o))}
            mkey = 'do' if spec['kind'] == 'candidate' else 'dr'
            signs = {float(np.sign(v[mkey])) for v in eff['by_paraphrase'].values() if abs(v[mkey]) > 0.02}
            eff['agent_stats'] = {'n': sum(len(ps) for ps in pairs.values()), 'measure': mkey,
                                  'spans_zero': bool(eff['national'][mkey]['lo'] < 0 < eff['national'][mkey]['hi']),
                                  'paraphrase_flip': len(signs) > 1, 'exposed': nationally_exposed,
                                  'checked': misread['checked'], 'misread': misread['misread']}
            eff['manipulation'] = misread
            eff['agreement'] = evidence.agreement(ev, eff['national'], nat_base, spec['kind'])
            if spec.get('withdraws'):
                from .whatifs import transfer
                eff['transfer'] = transfer([(c, f) for ps in pairs.values() for c, f, _, _ in ps], 200, rng)
            eff['blended'] = False
            if ev and spec.get('evidence_mode') == 'blend':
                eff['cohorts'] = {k: evidence.blend(c, evidence.prior(ev, cohorts[k], {'turnout': backbone_turn[k], 'r2': backbone_r2[k],
                                                                                        'o': backbone_o[k]}))
                                  for k, c in eff['cohorts'].items()}
                eff['blended'] = any(c['evidence_blend'] for c in eff['cohorts'].values())
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
                                   'agent_stats': e.get('agent_stats'), 'agreement': e.get('agreement'), 'blended': e.get('blended'),
                                   'manipulation': e.get('manipulation'),
                                   'transfer': {'point': e['transfer']['point'], 'n': e['transfer']['n']} if e.get('transfer') else None,
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
            out = aggregate.outcome(sv, ev, self._fixed_ev(states), self._split_ev(states), o_single=self._o_single(states))
            nat = sv.sum(axis=1)
            return {'r2_sd': float(np.std(nat[:, 0] / (nat[:, 0] + nat[:, 1])) * 100), 'ev_sd': float(np.std(out['ev'][:, 0]))}

        full = measure(fit, fit.world)
        zero = {k: 0.0 for k in backbone.GROUPS}
        if self.year == 1920 or self.extras.get('base_inp') is not None:
            no_pop = backbone.fit(self.extras.get('base_inp') or self.inp, draws, self.cfg.seed, pop_cv=zero)
            if self.extras.get('base_inp') is not None:
                no_pop = backbone.carry_forward(no_pop, self.inp, self.year, self.cfg.seed)
        else:
            no_pop = backbone.general_fit(self.inp, self.year, draws, self.cfg.seed, pop_cv=zero)
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

    # ── verify (any year) ──
    def verify(self):
        """The unchanged rerun reproduces every state's certified votes (R1), and,
        for a carried-forward year, the held-out women's turnout benchmark."""
        fit = self.fit()
        states, sidx = self.state_index(fit)
        sv = aggregate.by_state(fit.world, sidx, len(states))
        # Certified R/D/O per state; a state missing from the returns, or whose legislature
        # chose the electors (no popular vote), is checked against zero.
        no_pop = set(getattr(self.inp, 'no_popular', None) or ()) | set(fit.diagnostics.get('no_popular') or ())
        cert = np.array(self.inp.returns.reindex(states)[self._ret_cols()].fillna(0), dtype=float)
        cert[[s in no_pop for s in states]] = 0.0
        out = aggregate.outcome(sv, self.inp.ev.reindex(states).fillna(0).to_numpy(), self._fixed_ev(states), self._split_ev(states), o_single=self._o_single(states))
        err = np.abs(sv - cert[None, :, :])
        worst = float(err.max()) if err.size else 0.0
        by_state = err.max(axis=(0, 2))
        res = {'year': self.year, 'R1_worst_vote_error': worst, 'R1_pass': bool(worst <= 0.5), 'R1_states': len(states),
               'R1_no_popular': sorted(no_pop & set(states)),
               'R1_worst_states': [{'state': s, 'error': round(float(e), 3)}
                                   for s, e in sorted(zip(states, by_state), key=lambda x: -x[1])[:3]],
               'ev_by_draw': sorted({tuple(int(x) for x in e) for e in out['ev']})[:3]}
        d = fit.diagnostics
        if d.get('method') == 'general_fit':
            # general_fit's edge cases and the era priors it used (backbone.py, notes/B.md).
            flags = {k: d[k] for k in ('missing_returns', 'dropped_cell_states', 'synthetic_cell_states', 'legal_rules_contradicted',
                                       'T_column_mismatch', 'other_majority', 'black_south_bound_on') if d.get(k)}
            zp = {p: v for p, v in (d.get('zero_party') or {}).items() if v}
            if zp:
                flags['zero_party'] = zp
            scaled = {s: round(float(x), 3) for s, x in (d.get('adults_scaled_share') or {}).items() if x}
            if scaled:
                flags['adults_scaled_share'] = scaled
            res['fit_flags'] = flags
            res['priors'] = d.get('priors')
        from . import benchmarks  # validation stage: the held-out Corder–Wolbrecht turnout
        cw = benchmarks.corder_wolbrecht_any_year()
        cw = cw[(cw.year == self.year) & cw.state.isin(states)].set_index('state')
        if len(cw):
            # Corder–Wolbrecht's denominator: every adult 21+ of the sex, non-citizens included (EVAL.md N1).
            w = fit.world
            female = (fit.cells.sex == 'F').to_numpy()

            def rate(m):
                votes, adults = np.zeros((w.t.shape[0], len(states))), np.zeros((w.t.shape[0], len(states)))
                np.add.at(votes, (slice(None), sidx[m]), (w.adults * w.can * w.t)[:, m])
                np.add.at(adults, (slice(None), sidx[m]), w.adults[:, m])
                return votes / np.maximum(adults, 1)
            wt, mt = rate(female), rate(~female)
            rows = []
            for s in cw.index:
                i = states.index(s)
                rows.append({'state': s, 'women_model': round(float(np.median(wt[:, i])) * 100, 1),
                             'women_cw': round(float(cw.loc[s, 'women_turnout']) * 100, 1),
                             'men_model': round(float(np.median(mt[:, i])) * 100, 1),
                             'men_cw': round(float(cw.loc[s, 'men_turnout']) * 100, 1)})
            res['corder_wolbrecht'] = rows
            res['women_mae_points'] = round(float(np.mean([abs(r['women_model'] - r['women_cw']) for r in rows])), 1) if rows else None
        (self.dir / 'check.json').write_text(json.dumps(res, indent=1, default=float))
        return res

    def _fixed_ev(self, states):
        """[S, 3] electors by party for states whose legislature chose them (inp.ev_fixed:
        state → (R, D, O)); NaN rows elsewhere. None when the inputs carry no such table."""
        fx = getattr(self.inp, 'ev_fixed', None) or self.extras.get('franchise', {}).get('ev_fixed') or LEGISLATURE_EV.get(self.year)
        if not fx:
            return None
        out = np.full((len(states), 3), np.nan)
        for i, s in enumerate(states):
            if s in fx:
                v = fx[s]
                out[i] = [v.get(k, 0) for k in 'RDO'] if isinstance(v, dict) else list(v)
        return out

    def _o_single(self, states):
        """[S] the largest single "other" candidate's share of O (the named third P vs
        the rest), so a lumped O can't carry a state no one of its candidates won.
        None for 1916–1924 (their bundles stay as published)."""
        if self.year in (1916, 1920, 1924):
            return None
        r, yy = self.inp.returns.reindex(states).fillna(0), self.year % 100
        if f'P{yy}' not in r or f'O{yy}' not in r:
            return None
        o, p = r[f'O{yy}'].to_numpy(float), r[f'P{yy}'].clip(lower=0).to_numpy(float)
        p = np.minimum(p, o)
        return np.where(o > 0, np.maximum(p, o - p) / np.maximum(o, 1e-9), 1.0)

    def _split_ev(self, states):
        """[S, 3] historical electors by party for states that divided them (inp.ev_split:
        state → (R, D, O)); None when the inputs carry no such table."""
        sp = getattr(self.inp, 'ev_split', None) or self.extras.get('franchise', {}).get('ev_split')
        if not sp:
            return None
        out = np.full((len(states), 4), np.nan)
        cols = self._ret_cols()
        r = self.inp.returns.reindex(states).fillna(0)
        osg = self._o_single(states)
        for i, s in enumerate(states):
            if s in sp:
                v = sp[s]
                out[i, :3] = [v.get(k, 0) for k in 'RDO'] if isinstance(v, dict) else list(v)
                pv = r.loc[s, cols].to_numpy(float) * np.array([1, 1, osg[i] if osg is not None else 1])
                if pv.sum() > 0:
                    out[i, 3] = pv.argmax()   # the historical popular winner keeps the historical division
        return out

    def _ret_cols(self) -> list[str]:
        """This year's certified R, D and other columns in the returns (R1920… or the older R20…)."""
        r, y = self.inp.returns, self.year
        for suf in (str(y), f'{y % 100:02d}', str(y % 100)):  # R1920 first: R20 is ambiguous across centuries
            cols = [f'R{suf}', f'D{suf}', f'O{suf}']
            if all(c in r for c in cols):
                return cols
        raise SystemExit(f'No certified {y} returns (R/D/O columns) in the inputs: {list(r.columns)[:12]}')

    # ── dry run (free: no model calls) ──
    def dryrun(self, samples: int = 1) -> dict:
        """backbone (if not fitted) → verify → plan. Brief samples: one control per page slice,
        one counterfactual per what-if; counts of agents, requests and eligibility lines."""
        if not (self.dir / 'fit.pkl').exists():
            self.backbone()
        check = self.verify()
        plan = self.plan()
        reqs = self.requests()
        agents = json.loads((self.dir / 'agents/agents.json').read_text())
        by_agent = {a['id']: a for a in agents}
        out_slices, seen = {}, {}
        for r in reqs:
            a = by_agent[r['meta']['agent']]
            sl = serialize.slice_of(type('R', (), {'group': a['group'], 'south': a['state'] in agentlayer.SOUTH, 'sex': a['sex']}))
            out_slices[sl] = out_slices.get(sl, 0) + (r['meta']['kind'] == 'control')
            k = ('control', sl) if r['meta']['kind'] == 'control' else (r['meta']['arm'], None) if r['meta']['kind'] == 'cf' else None
            if k and seen.get(k, 0) < samples:
                seen[k] = seen.get(k, 0) + 1
                seen.setdefault('_briefs', []).append({'arm': r['meta']['arm'], 'slice': sl, 'agent': a['id'], 'user': r['user']})
        elig = {}
        for a in agents:
            line = a['eligibility'].replace(STATE_NAME.get(a['state'], a['state']), '<state>')
            elig[line] = elig.get(line, 0) + 1
        groups = {}
        for a in agents:
            g = a['group'] + (f':{a["status"]}' if a.get('status') else '') + (f':{a["origin"]}' if a.get('origin') else '')
            groups[g] = groups.get(g, 0) + 1
        res = {'year': self.year, 'run': self.id, 'era': agentlayer.era(self.year),
               'R1_worst_vote_error': check['R1_worst_vote_error'], 'R1_pass': check['R1_pass'], 'ev_by_draw': check['ev_by_draw'],
               'what_ifs': {k: k in for_year([k], self.year) for k in self.cfg.what_ifs},
               'cohorts': plan['cohorts'], 'agents': plan['agents'], 'requests': plan['requests'],
               'by_arm_model': plan['by_arm_model'], 'estimate': plan['estimate'],
               'controls_by_slice': out_slices, 'agents_by_group': groups,
               'eligibility_lines': dict(sorted(elig.items(), key=lambda x: -x[1])), 'briefs': seen.get('_briefs', [])}
        (self.dir / 'dryrun.json').write_text(json.dumps(res, indent=1, default=float))
        return res

    # ── evaluate ──
    def evaluate(self):
        from . import benchmarks
        if self.year != 1920:
            raise SystemExit('evaluate: the pre-registered checks are 1920\'s; every other year is checked by '
                             '`run verify` (reproduction, and Corder–Wolbrecht where it exists).')
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


# Electors chosen by a legislature, by party slot (R, D, O), 1828–1876: a fallback until the
# data layer supplies inp.ev_fixed (which wins). Before 1828 the data layer must supply it.
LEGISLATURE_EV = {
    1828: {'DE': (3, 0, 0), 'SC': (0, 11, 0)}, 1832: {'SC': (0, 0, 11)}, 1836: {'SC': (0, 0, 11)},
    1840: {'SC': (0, 11, 0)}, 1844: {'SC': (0, 9, 0)}, 1848: {'SC': (0, 9, 0)}, 1852: {'SC': (0, 8, 0)},
    1856: {'SC': (0, 8, 0)}, 1860: {'SC': (0, 0, 8)}, 1868: {'FL': (3, 0, 0)}, 1876: {'CO': (3, 0, 0)},
}
