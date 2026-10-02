"""The publish stage: every what-if combination → the page's result shape and bundle.

`Run` (pipeline.py) mixes `Publisher` in, so the methods here read the run's
fit, inputs, profile and agent files through `self`.
"""
from __future__ import annotations

import itertools
import json
import pickle
from pathlib import Path

import numpy as np

from . import agentlayer, aggregate, evidence, paired, prompts, quotes, scenario, serialize
from .config import ROOT
from .geo import STATE_NAME
from .whatifs import REGISTRY, apply_effects, for_year, text_for, withdraw

CONF = {'franchise': 'high', 'population': 'medium', 'issue': 'low', 'candidate': 'low'}
KIND_ORDER = ['franchise', 'population', 'issue', 'candidate']


def pre_interviews(run_dir: Path) -> dict | None:
    """The interviews done before any change, from a run's answered requests:
    each synthetic voter asked in the world as it was (the baseline the
    what-ifs are measured against), and the leakage probes when the run had
    them (L1 recall, L2 label swap; analysis.json)."""
    rq, an = run_dir / 'agents/all_requests.jsonl', run_dir / 'agents/answers.jsonl'
    if not rq.exists() or not an.exists():
        return None
    meta = {r['id']: r['meta'] for r in map(json.loads, rq.read_text().splitlines()) if r}
    done = [meta[a['id']] for a in map(json.loads, an.read_text().splitlines()) if a.get('ok', True) and a['id'] in meta]
    control = [m for m in done if m['kind'] == 'control']
    if not control:
        return None
    out = {'voters': len({m['agent'] for m in control}), 'interviews': len(control)}
    ap = run_dir / 'analysis.json'
    a = json.loads(ap.read_text()) if ap.exists() else {}
    if a.get('l1', {}).get('n'):
        out['recall'] = {'n': a['l1']['n'], 'winnerRate': a['l1']['winner_rate']}
    if a.get('l2', {}).get('n'):
        out['swap'] = {'n': a['l2']['n'], 'platformRate': a['l2']['platform_rate']}
    ag = run_dir / 'agents/agents.json'
    agents = {x['id']: x for x in json.loads(ag.read_text())} if ag.exists() else {}
    per = [len(agents[m['agent']].get('items', [])) for m in control if m['agent'] in agents]
    if per:
        out['items'] = [min(per), max(per)]
    out['asOf'] = max((m.get('context_date') or '' for m in control), default='') or None
    out['wordings'] = len({m.get('paraphrase') for m in control})
    return out


ITEM_SUMMARIES = ROOT / 'extracts' / 'item-summaries.json'



def briefs_record(run_dir: Path) -> dict:
    """What the synthetic voters were shown, from a run's requests and agents.
    told: per what-if, the exact lines that wrote the change into their world
    (settled facts; news printed on a nominee's ballot line; planks added or
    dropped). reading: every dated newspaper item in their briefs, with a
    one-line summary from extracts/item-summaries.json when it has one."""
    rq, ag = run_dir / 'agents/all_requests.jsonl', run_dir / 'agents/agents.json'
    told, reading = {}, []
    if rq.exists():
        by = {}
        for r in map(json.loads, rq.read_text().splitlines()):
            if r and r['meta']['kind'] == 'cf':
                by.setdefault(r['meta']['change']['what_if'], []).append(r)
        for wk, rs in by.items():
            ch = [r['meta']['change'] for r in rs]
            facts = max((c.get('facts', []) for c in ch), key=lambda f: sum(c.get('facts', []) == f for c in ch))
            t = {'facts': facts,
                 'added': sorted({p['text'] for c in ch for p in c.get('added_planks', [])}),
                 'dropped': sorted({p for c in ch for p in c.get('dropped_planks', [])}),
                 # D33: staged in-world news, and how many real items the change made false
                 'items': sorted({(i['date'], i['text']) for c in ch for i in c.get('added_items', [])}),
                 'removed': len({i for c in ch for i in c.get('dropped_sources', [])})}
            t['items'] = [{'date': d, 'text': x} for d, x in t['items']]
            sp = scenario.spec_path(wk)
            spec = json.loads(sp.read_text()) if sp.exists() else REGISTRY.get(wk, {})
            news = spec.get('nominee_news') or []
            if news and any(f'Recent news: {" ".join(news)}' in r['user'] for r in rs):
                t['news'] = news
            told[wk] = {k: v for k, v in t.items() if v}
    if ag.exists():
        sums = json.loads(ITEM_SUMMARIES.read_text()) if ITEM_SUMMARIES.exists() else {}
        seen = {}
        for a in json.loads(ag.read_text()):
            for i in a.get('items', []):
                seen.setdefault(i['id'], {'date': i['date'], 'newspaper': i['newspaper'], 'place': i['place'],
                                          **({'summary': sums[i['id']]} if i['id'] in sums else {})})
        reading = sorted(seen.values(), key=lambda x: (x['date'], x['newspaper']))
    return {'told': told, 'reading': reading}

class Publisher:
    """The publish stage and the bundle's parts. Needs the attributes and
    helpers `Run` sets up: cfg, inp, extras, prof, year, cand, dir, id, bulk,
    fit(), state_index(), requests(), answers(), _fixed_ev(), _split_ev(),
    _o_single() and _ret_cols()."""

    def publish(self):
        fit = self.fit()
        states, sidx = self.state_index(fit)
        ev = self.inp.ev.reindex(states).fillna(0).to_numpy()
        base_votes = aggregate.by_state(fit.world, sidx, len(states))
        base = aggregate.outcome(base_votes, ev, self._fixed_ev(states), self._split_ev(states), o_single=self._o_single(states))
        base_winner = base['winner'][0]
        base_sum = aggregate.summarize(base, base_winner)
        # Page key A is the historical winner (history.js): D → A in a year the D nominee won.
        self.key_of = serialize.key_map(base_sum['ev_point'])
        eff_path = self.dir / 'effects.pkl'
        eff = pickle.load(open(eff_path, 'rb')) if eff_path.exists() else {'effects': {}, 'pairs': {}, 'exposed': set(), 'nationally_exposed': False}
        co = json.loads((self.dir / 'agents/cohorts.json').read_text()) if (self.dir / 'agents/cohorts.json').exists() else None
        cell_to = [co['cell_to'][str(i)] for i in range(len(fit.cells))] if co else []

        available = [k for k in for_year(self.cfg.what_ifs, self.year) if REGISTRY[k]['mode'] == 'backbone' or k in eff['effects']]
        available += ['everyone'] if 'everyone' not in available else []
        runs, tables, results_meta = {}, {}, {}
        for n in range(0, min(len(available), self.cfg.max_combo) + 1):
            for combo in itertools.combinations(sorted(available), n):
                if 'everyone' in combo and len(combo) > 1:
                    continue
                if sum(REGISTRY[k]['kind'] == 'candidate' for k in combo) > 1:
                    continue  # two named third candidates would share the one O column
                world = fit.world
                for k in sorted(combo, key=lambda k: KIND_ORDER.index(REGISTRY[k]['kind'])):
                    spec = REGISTRY[k]
                    if spec['mode'] == 'backbone':
                        world = spec['apply'](fit, world, self.inp)
                    elif spec.get('withdraws') and 'transfer' in eff['effects'][k]:
                        world = withdraw(fit, world, eff['effects'][k]['transfer'], self._third_frac(fit))
                    else:
                        world = apply_effects(fit, world, cell_to, eff['effects'][k]['cohorts'])
                sv = aggregate.by_state(world, sidx, len(states))
                out = aggregate.outcome(sv, ev, self._fixed_ev(states), self._split_ev(states), o_single=self._o_single(states))
                summ = aggregate.summarize(out, base_winner)
                key = '+'.join(combo)
                runs[key] = (world, summ, out)
        bundle = self._bundle(fit, states, runs, base_sum, base_winner, eff)
        bundle['pre'] = pre_interviews(self.dir)
        bundle.update(briefs_record(self.dir))
        pub = self.dir / 'published'
        pub.mkdir(exist_ok=True)
        (pub / f'{self.cfg.election}.json').write_text(json.dumps(bundle, indent=1, default=float))
        return {k: {'ev': v[1]['ev_point'], 'drawsWon': v[1]['draws_won']} for k, v in runs.items()}

    def _third_frac(self, fit):
        """Per cell: the labelled third candidate's part of the state's `other` vote."""
        r = self.inp.returns
        col = next((c for c in (f'P{self.year}', f'P{self.year % 100}') if c in r), None)
        if col is None:
            return np.ones(len(fit.cells))
        frac = (r[col] / r[self._ret_cols()[2]].clip(lower=1)).clip(0, 1)
        return fit.cells.state.map(frac).fillna(0).to_numpy()

    def spec(self, k: str) -> dict:
        """A what-if's registry entry as this year's page reads it."""
        return text_for(REGISTRY[k], self.year)

    def _bundle(self, fit, states, runs, base_sum, base_winner, eff):
        state_names = {**{s: s for s in states}, **STATE_NAME}  # a state geo doesn't name (AK, HI) reads as its code
        sources_by_slice = self.prof['slice_sources']
        slice_labels = None if 1868 <= self.year < 1972 else agentlayer.groups_for(self.year)['slices']
        base_world = runs[''][0]
        base_point = base_sum['point']
        used = sorted({k for key in runs for k in key.split('+') if k})
        evs = {k: scenario.load_evidence(k) for k in used}
        conf_of = {k: evidence.confidence(REGISTRY[k], evs[k], eff['effects'].get(k, {}).get('agreement'),
                                          eff['effects'].get(k, {}).get('agent_stats'), bool(REGISTRY[k].get('generated')))
                   for k in used}
        election = {
            'slices': serialize.slices(fit, base_world, base_point, sources_by_slice, slice_labels, self.key_of),
            'whatIfs': [{'key': k, 'label': self.spec(k)['label'], 'kind': REGISTRY[k]['kind'], 'detail': self.spec(k)['detail'],
                         'slices': REGISTRY[k]['slices'], 'assumption': self.spec(k)['assumption'],
                         # additive
                         'confidenceTier': conf_of[k]['tier'], 'evidence': conf_of[k]['evidence'],
                         'exploratory': bool(REGISTRY[k].get('generated'))}
                        for k in used],
        }
        validation = {}
        vpath = self.dir / 'validation.json'
        if vpath.exists():
            validation = json.loads(vpath.read_text())
        out_runs, tables = {}, {}
        # Each what-if's own sentence comes from its single run, so a combined
        # run doesn't misattribute one change's people to another.
        single = {k: self._lead([k], fit, runs[''][0], runs[k][0], runs[k][1]) for k in runs if k and '+' not in k}
        for key, (world, summ, out) in runs.items():
            combo = [k for k in key.split('+') if k]
            tier = evidence.combine_tiers([conf_of[k] for k in combo])
            # The page knows high, medium and low; "very-low" reaches it as low plus the flag.
            conf = tier['tier'] if tier['tier'] in CONF.values() else 'low'
            sl = serialize.slices(fit, world, summ['point'], sources_by_slice, slice_labels, self.key_of)
            lead = ' '.join(single[k] for k in combo) if combo else self._lead([], fit, runs[''][0], world, summ)
            cand = dict(self.cand)
            for k in combo:
                if REGISTRY[k]['kind'] == 'candidate' and REGISTRY[k].get('candidate') and not REGISTRY[k].get('withdraws'):
                    cand[2] = REGISTRY[k]['candidate']['name']
            text = serialize.verdict(lead=lead, names=states, state_names=state_names, cand=cand, summary=summ,
                                     base_summary=base_sum, base_winner=base_winner, key_of=self.key_of)
            if tier['reasons'] and (tier['tier'] == 'very-low' or any(REGISTRY[k].get('generated') for k in combo)):
                text += f' {tier["label"]}. {tier["reasons"][0]}'
            ev_page = [x for x in (evidence.page_evidence(k, evs[k], eff['effects'].get(k, {}).get('agreement')) for k in combo) if x]
            ev_sources = list({s['url']: {'title': s['title'], 'url': s['url']} for x in ev_page for f in x['findings']
                               for s in f['sources']}.values())
            extras = {
                'assumptions': [self.spec(k)['assumption'] for k in combo],
                'howIGotThis': self._how(combo, summ, evs, tier),
                'sources': sources_for(self.year) + ev_sources,
                # additive: how sure, and why
                'confidenceTier': tier['tier'], 'confidenceLabel': tier['label'],
                'confidenceFlags': tier['flags'], 'confidenceReasons': tier['reasons'],
                'evidence': ev_page,
                'mode': 'truth',
                'runId': self.id,
                'validation': validation.get('summary'),
                'cohortEffects': self._cohort_effects(combo, eff),
            }
            applied = [{'key': k, 'label': REGISTRY[k]['label'], 'kind': REGISTRY[k]['kind']} for k in combo]
            out_runs[key] = serialize.result(names=states, summary=summ, base_winner=base_winner, slices_out=sl, text=text,
                                             confidence=conf, applied=applied, extras=extras, key_of=self.key_of)
            tables[key] = self._state_slice_table(fit, world, summ['point'])
        voters = self._voters(eff, runs)
        return {
            'year': self.cfg.election, 'runId': self.id, 'election': election, 'runs': out_runs, 'tables': tables,
            'voters': voters, 'interviews': self._interviews(eff), 'ev': dict(zip(states, self.inp.ev.reindex(states).fillna(0).astype(int).tolist())),
            'historyWinner': {s: self.key_of[int(w)] for s, w in zip(states, base_winner)},
            'words': self._words(used),
        }

    def _words(self, used):
        base = {'no-19th': ['19th', 'nineteenth', 'suffrage fails', 'women can\'t vote', 'no women'],
                'fifteenth': ['15th', 'fifteenth', 'black southern', 'black voters', 'poll tax', 'jim crow'],
                'league': ['league', 'treaty', 'versailles'],
                'everyone': ['everyone', 'all adults', 'universal']}
        extra = scenario.extra_words()
        out = []
        for k in used:
            words = base.get(k, []) + REGISTRY[k].get('words', []) + extra.get(k, [])
            if words:
                out.append({'key': k, 'words': list(dict.fromkeys(w.lower() for w in words))})
        return out

    def _lead(self, combo, fit, base, world, summ):
        if not combo:
            # Winner and electoral votes from the calibrated rerun, not the profile's ev_label (whose order varies).
            won = int(np.argmax(summ['ev_point']))
            return (f'Rerun with nothing changed, {self.year} comes out as it did: {self.cand[won]} wins, '
                    f'{serialize.headline_ev(summ, getattr(self, "key_of", serialize.PARTY_TO_KEY))}.')
        p = summ['point']
        voted_base = (base.adults[p] * base.can[p] * base.t[p]).sum()
        voted = (world.adults[p] * world.can[p] * world.t[p]).sum()
        change = voted - voted_base
        parts = []
        for k in combo:
            if k == 'no-19th':
                parts.append(f'{serialize.fmt_m(-change)} women who voted can\'t, outside the states that already let them.')
            elif k == 'fifteenth':
                parts.append(f'{serialize.fmt_m(change)} more Black Southerners vote, turning out like white Southerners and splitting like Black voters in the North.')
            elif k == 'everyone':
                parts.append(f'{serialize.fmt_m(change)} more adults vote.')
            elif k == 'league':
                def r2(wd):
                    v = (wd.adults[p] * wd.can[p] * wd.t[p])[:, None] * wd.share[p]
                    return v[:, 0].sum() / (v[:, 0].sum() + v[:, 1].sum()) * 100
                shift = r2(world) - r2(base)
                toward = self.cand[1] if shift < 0 else self.cand[0]
                parts.append(f'With the treaty settled, the voters I interviewed lean {abs(shift):.1f} points further toward {toward} '
                             'than the same people did in the world as it was.')
            elif REGISTRY[k].get('generated'):
                parts.append(self._lead_generated(REGISTRY[k], base, world, p, change))
        return ' '.join(parts)

    def _lead_generated(self, spec, base, world, p, change):
        def shares(wd):
            v = (wd.adults[p] * wd.can[p] * wd.t[p])[:, None] * wd.share[p]
            r, d, o = v[:, 0].sum(), v[:, 1].sum(), v[:, 2].sum()
            return r / (r + d) * 100, o / (r + d + o) * 100
        (r2_0, o_0), (r2_1, o_1) = shares(base), shares(world)
        toward = self.cand[1] if r2_1 < r2_0 else self.cand[0]
        if spec.get('withdraws'):
            return (f'With {self.cand[2]} out of the race, candidates outside the two parties take {o_1:.1f}% of the vote, '
                    f'against {o_0:.1f}% in {self.year}, and the two-party split moves {abs(r2_1 - r2_0):.1f} points toward {toward}.')
        if spec['kind'] == 'candidate':
            name = spec['candidate']['name']
            return (f'With {name} on the ballot, candidates outside the two parties take {o_1:.1f}% of the vote, against {o_0:.1f}% '
                    f'in {self.year}, and the two-party split moves {abs(r2_1 - r2_0):.1f} points toward {toward}.')
        if spec['kind'] == 'franchise':
            return f'{serialize.fmt_m(abs(change))} {"more" if change >= 0 else "fewer"} adults vote.'
        if spec['kind'] == 'population':
            d = float((world.adults[p] - base.adults[p]).sum())
            return (f'{serialize.fmt_m(abs(d))} {"more" if d >= 0 else "fewer"} adults live in the country, and those who can vote '
                    f'turn out and choose as their group did in {self.year}.')
        return (f'In this world, the voters I interviewed lean {abs(r2_1 - r2_0):.1f} points further toward {toward} than the same '
                f'people did in {self.year} as it was.')

    def _how(self, combo, summ, evs=None, tier=None):
        lines = []
        for k in combo:
            spec = self.spec(k)
            lines.append(f'What changed: {spec["detail"]}')
            if spec.get('borrowed'):
                lines.append(f'New voters borrow the behaviour of {spec["borrowed"]}.')
            ev = (evs or {}).get(k)
            if ev and ev.get('summary'):
                n, level = len(ev.get('findings', [])), evidence.strength(ev)['level']
                count = f' ({n} finding{"s" if n != 1 else ""}, {level} evidence)' if n else ''
                lines.append(f'What historians found{count}: {ev["summary"]}')
        census = self.prof.get('census_line') or (
            '1920 census voting-age tables' if self.year == 1920 else
            f'{self.prof["base"]} census voting-age tables aged to {self.year}' if self.prof.get('base') else
            census_phrase(self.year))
        lines.append(f'The numbers: the {census} and certified returns; every draw reproduces {self.year} exactly before the change.')
        lines.append(f'How sure: I reran it {summ["draws"]} times with different population and parameter draws.')
        if tier and tier['tier'] in ('low', 'very-low') and combo:
            lines.append(f'{tier["label"]}: ' + ' '.join(tier['reasons'][:3]))
        return lines

    def _cohort_effects(self, combo, eff):
        out = []
        for k in combo:
            e = eff['effects'].get(k)
            if not e or REGISTRY[k]['mode'] != 'agents':
                continue
            for ck, c in e['cohorts'].items():
                out.append({'whatIf': k, 'cohort': ck, 'n': c['n'], 'bias': round(c['bias'], 3), 'weight': round(c['weight'], 3),
                            'exposed': c['exposed'], 'dr': round(c['dr'], 3), 'dt': round(c['dt'], 3)})
        return out

    def _state_slice_table(self, fit, world, p):
        keys = fit.cells.apply(serialize.slice_of, axis=1).to_numpy()
        rows = []
        for (s, sl), idx in fit.cells.assign(sl=keys).groupby(['state', 'sl']).groups.items():
            idx = np.array(list(idx))
            a = world.adults[p, idx]
            n = a.sum()
            if n <= 0:
                continue
            voted = a * world.can[p, idx] * world.t[p, idx]
            by_key = {self.key_of[j]: float((voted * world.share[p, idx, j]).sum() / n) for j in range(3)}
            rows.append({'state': s, 'slice': sl, 'adults': float(n),
                         'barred': float((a * (1 - world.can[p, idx])).sum() / n),
                         'home': float((a * world.can[p, idx] * (1 - world.t[p, idx])).sum() / n),
                         'A': by_key['A'], 'B': by_key['B'], 'O': by_key['O']})
        return rows

    def _voters(self, eff, runs):
        """One person per slice, per what-if combination (single what-ifs and history)."""
        if not (self.dir / 'agents/agents.json').exists():
            return {}
        agents = {a['id']: a for a in json.loads((self.dir / 'agents/agents.json').read_text())}
        co = json.loads((self.dir / 'agents/cohorts.json').read_text())
        cohorts = co['cohorts']
        reqs = {r['id']: r for r in self.requests()}
        ans = self.answers()
        corpus = {c['id']: c for c in self.extras['corpus']}
        slice_of_cohort = {}
        for k, c in cohorts.items():
            row = type('R', (), {'group': c['group'], 'south': c['region'] == 'south', 'sex': c['sex']})
            slice_of_cohort[k] = serialize.slice_of(row)
        slices = {}
        for k, s in slice_of_cohort.items():
            slices.setdefault(s, []).append(k)
        adults = {k: c['adults'] for k, c in cohorts.items()}
        out = {}
        for wk in [''] + list(eff['pairs']):
            answers = {}
            for aid, a in agents.items():
                c_id = f'control|{aid}|{self.bulk}'
                f_id = f'cf:{wk}|{aid}|{self.bulk}' if wk else c_id
                chk = reqs[f_id]['meta'].get('news_check') if f_id in reqs else None
                if chk and f_id in ans and ans[f_id]['data'].get('news_about') != chk['expected']:
                    continue  # misread whom the news was about (p5 check)
                if c_id in ans and f_id in ans:
                    lab = {v: k for k, v in reqs[c_id]['meta']['label_of'].items()}
                    answers[aid] = {'control': paired.normalize(ans[c_id]['data'], lab) | {'raw': ans[c_id]['data']},
                                    'cf': paired.normalize(ans[f_id]['data'], lab) | {'raw': ans[f_id]['data']},
                                    'cf_req': reqs[f_id]}
            picks = quotes.select(slices, agents, answers, adults, self.cfg.seed)
            per = {}
            for p in picks:
                a = p['agent']
                x = answers[a['id']]
                names = {a['label_of'][k]: self.prof['names'][k] for k in a['label_of']}
                if x['cf_req']['meta'].get('candidate'):
                    names[x['cf_req']['meta']['candidate']['label']] = x['cf_req']['meta']['candidate']['name']
                srcs = [corpus[i] for i in x['cf']['raw'].get('sources_used', []) if i in corpus] or \
                       [corpus[i] for i in x['cf_req']['meta']['sources'] if i in corpus]
                key_map = {'R': self.key_of[0], 'D': self.key_of[1], 'O': 'O', 'home': 'home', 'barred': 'barred'}
                per[p['slice']] = {
                    'name': a['name'],
                    'line': f'{a["age"]}, {"a city or town" if a["urban"] else "the countryside"}, {STATE_NAME.get(a["state"], a["state"])}',
                    'quote': quotes.deblind(x['cf']['raw'].get('quote', ''), names),
                    'history': key_map[x['control']['choice']],
                    'now': key_map[x['cf']['choice']],
                    # additive
                    'controlQuote': quotes.deblind(x['control']['raw'].get('quote', ''), names),
                    'cohort': cohorts[a['cohort']]['label'],
                    'cohortAdults': round(cohorts[a['cohort']]['adults']),
                    'weight': round(a['weight']),
                    'contextDate': x['cf_req']['meta']['context_date'],
                    'sources': [{'title': f'{s["newspaper"]}, {s["date"]}', 'url': s['url'], 'date': s['date']} for s in srcs],
                    'model': x['cf_req']['model'], 'promptVersion': x['cf_req']['meta']['prompt_version'],
                    'memorizationExposed': bool(eff.get('nationally_exposed') or a['cohort'] in eff.get('exposed', set())),
                    'namesRestored': True,
                    'unchanged': x['cf']['choice'] == x['control']['choice'],
                    'change': x['cf_req']['meta'].get('change'),
                }
            out[wk] = per
        return out

    def _interviews(self, eff):
        """Every paired interview, per what-if (additive): the question wordings
        once, and each person's two answers (as it was / in the what-if), names
        restored. The page shows it in the robot's opened bubble."""
        if not (self.dir / 'agents/agents.json').exists():
            return {}
        agents = {a['id']: a for a in json.loads((self.dir / 'agents/agents.json').read_text())}
        cohorts = json.loads((self.dir / 'agents/cohorts.json').read_text())['cohorts']
        reqs = {r['id']: r for r in self.requests()}
        ans = self.answers()
        says = {'R': self.cand[0], 'D': self.cand[1], 'O': self.cand[2], 'home': 'stays home', 'barred': 'can’t vote'}

        def one(rid, a, lab):
            d = ans[rid]['data']
            n = paired.normalize(d, lab)
            names = {a['label_of'][k]: self.prof['names'][k] for k in a['label_of']}
            c = reqs[rid]['meta'].get('candidate')
            if c:
                names[c['label']] = c['name']
            choice = c['name'] if c and d.get('choice') == c['label'] and n['choice'] == 'O' else says.get(n['choice'], n['choice'])
            return {'choice': choice, 'pVote': d.get('p_vote'),
                    'quote': quotes.deblind(d.get('quote', ''), names), 'reason': quotes.deblind(d.get('reason', ''), names)}

        out = {'questions': prompts.questions(self.prof['day_phrase']), 'byWhatIf': {}}
        for wk in eff['pairs']:
            rows = []
            for aid, a in agents.items():
                c_id, f_id = f'control|{aid}|{self.bulk}', f'cf:{wk}|{aid}|{self.bulk}'
                if c_id not in ans or f_id not in ans:
                    continue
                lab = {v: k for k, v in reqs[c_id]['meta']['label_of'].items()}
                chk = reqs[f_id]['meta'].get('news_check')
                rows.append({
                    # additive: took the news to be about the other candidate; left out of the counts
                    **({'misread': True} if chk and ans[f_id]['data'].get('news_about') != chk['expected'] else {}),
                    'question': a['paraphrase'], 'name': a['name'], 'cohort': cohorts[a['cohort']]['label'],
                    'line': f'{a["age"]}, {"a city or town" if a["urban"] else "the countryside"}, {STATE_NAME.get(a["state"], a["state"])}',
                    'before': one(c_id, a, lab), 'after': one(f_id, a, lab),
                })
            out['byWhatIf'][wk] = sorted(rows, key=lambda r: (r['question'], r['cohort'], r['name']))
        return out




def census_phrase(year: int) -> str:
    """Which censuses a general year's population comes from (first census 1790; latest 2020)."""
    c = min(max(year - year % 10, 1790), 2020)
    if c == year:
        return f'{year} census counts'
    if c > year:
        return f'{c} census counts carried back to {year}'
    if c == 2020:
        return f'2020 census counts carried forward to {year}'
    return f'{c} and {c + 10} census counts interpolated to {year}'


def sources_for(year: int) -> list[dict]:
    if year == 1920:
        return SOURCES
    if year == 1924:
        return [SOURCES[0], SOURCES[1],
                {'title': f'National Archives, {year} Electoral College results', 'url': f'https://www.archives.gov/electoral-college/{year}'},
                SOURCES[4], SOURCES[5],
                {'title': f'American Presidency Project, {year} party platforms (Republican, Democratic, Progressive)',
                 'url': 'https://www.presidency.ucsb.edu/documents/app-categories/elections-and-transitions/party-platforms'}]
    from . import profiles
    prof = profiles.get(year)
    if prof.get('sources'):
        return prof['sources']  # a profile's own list wins
    census = min(max(year - year % 10, 1790), 2020)
    out = [{'title': f'{census} United States census (population by state, sex, race, nativity and citizenship, via NHGIS)',
            'url': 'https://www.nhgis.org/'}]
    if 1868 <= year <= 2020:
        out.append(SOURCES[1])
    else:
        out.append({'title': 'Dubin, United States Presidential Elections, 1788–1860' if year < 1868 else
                    f'Federal Election Commission, Official {year} Presidential General Election Results',
                    'url': 'https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/'
                    if year > 2020 else 'https://mcfarlandbooks.com/product/united-states-presidential-elections-1788-1860/'})
    out.append({'title': f'National Archives, {year} Electoral College results', 'url': f'https://www.archives.gov/electoral-college/{year}'})
    out.append(SOURCES[4])
    if year < 1920:
        out.append(SOURCES[5])
    if year >= 1840:
        parties = ', '.join(prof.get('full_names', {}).get(k, '') for k in ('R', 'D', 'O') if prof.get('full_names', {}).get(k))
        out.append({'title': f'American Presidency Project, {year} party platforms' + (f' ({parties})' if parties else ''),
                    'url': 'https://www.presidency.ucsb.edu/documents/app-categories/elections-and-transitions/party-platforms'})
    return out


SOURCES = [
    {'title': 'Fourteenth Census of the United States (1920), Vol. II–III: voting age, color, nativity and citizenship', 'url': 'https://www.census.gov/library/publications/1922/dec/vol-02-population.html'},
    {'title': 'Algara & Amlani, county presidential returns 1868–2020 (Harvard Dataverse, CC0)', 'url': 'https://doi.org/10.7910/DVN/DGUMFI'},
    {'title': 'Clerk of the House, Statistics of the Presidential and Congressional Election of November 2, 1920', 'url': 'https://history.house.gov/Institution/Election-Statistics/'},
    {'title': 'National Archives, 1920 Electoral College results', 'url': 'https://www.archives.gov/electoral-college/1920'},
    {'title': 'Gray & Jenkins, state-level franchise data (Harvard Dataverse, CC0)', 'url': 'https://doi.org/10.7910/DVN/QIY9EM'},
    {'title': 'Teele, women\'s suffrage dates (Harvard Dataverse, CC0)', 'url': 'https://doi.org/10.7910/DVN/JZYGRB'},
    {'title': 'Library of Congress, Chronicling America (period newspapers, dated before 2 Nov 1920)', 'url': 'https://chroniclingamerica.loc.gov/'},
]

