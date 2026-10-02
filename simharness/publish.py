"""The publish stage: every what-if combination → the page's result shape and bundle.

`Run` (pipeline.py) mixes `Publisher` in, so the methods here read the run's
fit, inputs, profile and agent files through `self`.
"""
from __future__ import annotations

import itertools
import json
import pickle

import numpy as np

from . import aggregate, evidence, paired, prompts, quotes, scenario, serialize
from .geo import STATE_NAME
from .whatifs import REGISTRY, apply_effects

CONF = {'franchise': 'high', 'population': 'medium', 'issue': 'low', 'candidate': 'low'}
NAMES = {'R': 'Harding', 'D': 'Cox', 'O': 'another candidate'}
SLICE_SOURCES = {
    'men': '1920 census (Fourteenth Census, voting-age tables), men 21+ outside the eleven Southern states; turnout and choice from the backbone (1916→1920 natural experiment, calibrated to certified returns).',
    'women': '1920 census, women 21+ outside the South; turnout is each state\'s 1920 vote minus the men\'s predicted vote (1916 men\'s turnout × the change in states where women already voted).',
    'south-white': '1920 census, white adults in the eleven former Confederate states (includes a small number of American Indian and Asian adults); calibrated to certified returns.',
    'black-south': '1920 census, Black adults in the eleven former Confederate states; turnout from a Goodman regression of 1916 turnout on Black share across those states; the shortfall against white turnout is counted as exclusion.',
    'immigrants': '1920 census, foreign-born white adults who were aliens or had only declared their intent (first papers).',
}
KIND_ORDER = ['franchise', 'population', 'issue', 'candidate']


class Publisher:
    """The publish stage and the bundle's parts. Needs the attributes and
    helpers `Run` sets up: cfg, inp, extras, year, cand, dir, id, bulk,
    fit(), state_index(), requests() and answers()."""

    def publish(self):
        fit = self.fit()
        states, sidx = self.state_index(fit)
        ev = self.inp.ev.reindex(states).fillna(0).to_numpy()
        base_votes = aggregate.by_state(fit.world, sidx, len(states))
        base = aggregate.outcome(base_votes, ev)
        base_winner = base['winner'][0]
        base_sum = aggregate.summarize(base, base_winner)
        eff_path = self.dir / 'effects.pkl'
        eff = pickle.load(open(eff_path, 'rb')) if eff_path.exists() else {'effects': {}, 'pairs': {}, 'exposed': set(), 'nationally_exposed': False}
        co = json.loads((self.dir / 'agents/cohorts.json').read_text()) if (self.dir / 'agents/cohorts.json').exists() else None
        cell_to = [co['cell_to'][str(i)] for i in range(len(fit.cells))] if co else []

        available = [k for k in self.cfg.what_ifs if REGISTRY[k]['mode'] == 'backbone' or k in eff['effects']]
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
                    else:
                        world = apply_effects(fit, world, cell_to, eff['effects'][k]['cohorts'])
                sv = aggregate.by_state(world, sidx, len(states))
                out = aggregate.outcome(sv, ev)
                summ = aggregate.summarize(out, base_winner)
                key = '+'.join(combo)
                runs[key] = (world, summ, out)
        bundle = self._bundle(fit, states, runs, base_sum, base_winner, eff)
        pub = self.dir / 'published'
        pub.mkdir(exist_ok=True)
        (pub / f'{self.cfg.election}.json').write_text(json.dumps(bundle, indent=1, default=float))
        return {k: {'ev': v[1]['ev_point'], 'drawsWon': v[1]['draws_won']} for k, v in runs.items()}

    def _bundle(self, fit, states, runs, base_sum, base_winner, eff):
        sources_by_slice = SLICE_SOURCES
        base_world = runs[''][0]
        base_point = base_sum['point']
        used = sorted({k for key in runs for k in key.split('+') if k})
        evs = {k: scenario.load_evidence(k) for k in used}
        conf_of = {k: evidence.confidence(REGISTRY[k], evs[k], eff['effects'].get(k, {}).get('agreement'),
                                          eff['effects'].get(k, {}).get('agent_stats'), bool(REGISTRY[k].get('generated')))
                   for k in used}
        election = {
            'slices': serialize.slices(fit, base_world, base_point, sources_by_slice),
            'whatIfs': [{'key': k, 'label': REGISTRY[k]['label'], 'kind': REGISTRY[k]['kind'], 'detail': REGISTRY[k]['detail'],
                         'slices': REGISTRY[k]['slices'], 'assumption': REGISTRY[k]['assumption'],
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
            sl = serialize.slices(fit, world, summ['point'], sources_by_slice)
            lead = ' '.join(single[k] for k in combo) if combo else self._lead([], fit, runs[''][0], world, summ)
            cand = dict(self.cand)
            for k in combo:
                if REGISTRY[k]['kind'] == 'candidate' and REGISTRY[k].get('candidate'):
                    cand[2] = REGISTRY[k]['candidate']['name']
            text = serialize.verdict(lead=lead, names=states, state_names=STATE_NAME, cand=cand, summary=summ,
                                     base_summary=base_sum, base_winner=base_winner)
            if tier['reasons'] and (tier['tier'] == 'very-low' or any(REGISTRY[k].get('generated') for k in combo)):
                text += f' {tier["label"]}. {tier["reasons"][0]}'
            ev_page = [x for x in (evidence.page_evidence(k, evs[k], eff['effects'].get(k, {}).get('agreement')) for k in combo) if x]
            ev_sources = list({s['url']: {'title': s['title'], 'url': s['url']} for x in ev_page for f in x['findings']
                               for s in f['sources']}.values())
            extras = {
                'assumptions': [REGISTRY[k]['assumption'] for k in combo],
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
                                             confidence=conf, applied=applied, extras=extras)
            tables[key] = self._state_slice_table(fit, world, summ['point'])
        voters = self._voters(eff, runs)
        return {
            'year': self.cfg.election, 'runId': self.id, 'election': election, 'runs': out_runs, 'tables': tables,
            'voters': voters, 'interviews': self._interviews(eff), 'ev': dict(zip(states, self.inp.ev.reindex(states).fillna(0).astype(int).tolist())),
            'historyWinner': {s: serialize.PARTY_TO_KEY[int(w)] for s, w in zip(states, base_winner)},
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
            return f'Rerun with nothing changed, 1920 comes out as it did: Harding wins, {serialize.headline_ev(summ)}.'
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
            spec = REGISTRY[k]
            lines.append(f'What changed: {spec["detail"]}')
            if spec.get('borrowed'):
                lines.append(f'New voters borrow the behaviour of {spec["borrowed"]}.')
            ev = (evs or {}).get(k)
            if ev and ev.get('summary'):
                n, level = len(ev.get('findings', [])), evidence.strength(ev)['level']
                count = f' ({n} finding{"s" if n != 1 else ""}, {level} evidence)' if n else ''
                lines.append(f'What historians found{count}: {ev["summary"]}')
        lines.append(f'The numbers: the 1920 census voting-age tables and certified returns; every draw reproduces {self.year} exactly before the change.')
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
            by_key = {serialize.PARTY_TO_KEY[j]: float((voted * world.share[p, idx, j]).sum() / n) for j in range(3)}
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
                names = {a['label_of'][k]: NAMES[k] for k in a['label_of']}
                if x['cf_req']['meta'].get('candidate'):
                    names[x['cf_req']['meta']['candidate']['label']] = x['cf_req']['meta']['candidate']['name']
                srcs = [corpus[i] for i in x['cf']['raw'].get('sources_used', []) if i in corpus] or \
                       [corpus[i] for i in x['cf_req']['meta']['sources'] if i in corpus]
                key_map = {'R': 'A', 'D': 'B', 'O': 'O', 'home': 'home', 'barred': 'barred'}
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
            names = {a['label_of'][k]: NAMES[k] for k in a['label_of']}
            c = reqs[rid]['meta'].get('candidate')
            if c:
                names[c['label']] = c['name']
            choice = c['name'] if c and d.get('choice') == c['label'] and n['choice'] == 'O' else says.get(n['choice'], n['choice'])
            return {'choice': choice, 'pVote': d.get('p_vote'),
                    'quote': quotes.deblind(d.get('quote', ''), names), 'reason': quotes.deblind(d.get('reason', ''), names)}

        out = {'questions': prompts.QUESTIONS, 'byWhatIf': {}}
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




def sources_for(year: int) -> list[dict]:
    return SOURCES


SOURCES = [
    {'title': 'Fourteenth Census of the United States (1920), Vol. II–III: voting age, color, nativity and citizenship', 'url': 'https://www.census.gov/library/publications/1922/dec/vol-02-population.html'},
    {'title': 'Algara & Amlani, county presidential returns 1868–2020 (Harvard Dataverse, CC0)', 'url': 'https://doi.org/10.7910/DVN/DGUMFI'},
    {'title': 'Clerk of the House, Statistics of the Presidential and Congressional Election of November 2, 1920', 'url': 'https://history.house.gov/Institution/Election-Statistics/'},
    {'title': 'National Archives, 1920 Electoral College results', 'url': 'https://www.archives.gov/electoral-college/1920'},
    {'title': 'Gray & Jenkins, state-level franchise data (Harvard Dataverse, CC0)', 'url': 'https://doi.org/10.7910/DVN/QIY9EM'},
    {'title': 'Teele, women\'s suffrage dates (Harvard Dataverse, CC0)', 'url': 'https://doi.org/10.7910/DVN/JZYGRB'},
    {'title': 'Library of Congress, Chronicling America (period newspapers, dated before 2 Nov 1920)', 'url': 'https://chroniclingamerica.loc.gov/'},
]

