"""What-ifs and their evidence: source tiers, grounding, blending and confidence (evidence.py)."""
import numpy as np

from simharness.evidence import blend, combine_tiers, confidence, ground, tier_of


def test_source_tiers():
    assert tier_of('https://www.jstor.org/stable/1') == 'A'
    assert tier_of('https://history.house.gov/x') == 'A'
    assert tier_of('https://www.britannica.com/event/x') == 'B'
    assert tier_of('https://en.wikipedia.org/wiki/X') == 'C'
    assert tier_of('https://example.com/x') == 'C'


def test_ground_drops_unreturned_sources():
    notes = {'sources': [{'id': 'S1', 'url': 'https://www.jstor.org/x', 'title': 't', 'tier': 'A', 'cited': []}]}
    pop = {'sex': 'any', 'group': 'any', 'region': 'any'}
    f = {'claim': 'c', 'population': pop, 'situation': '', 'when': '', 'match': 'same-event', 'limits': '',
         'direction': 'toward-R', 'effects': [{'measure': 'r2', 'pp': 3.0, 'pm': 1.0}]}
    ev = ground({'findings': [f | {'source_ids': ['S9']}, f | {'source_ids': ['S1']}]}, notes)
    assert ev['dropped_ungrounded'] == 1 and len(ev['findings']) == 1
    assert ev['findings'][0]['grade'] == 1.0 and ev['findings'][0]['effects'][0]['pp'] == 3.0


def test_confidence_tiers():
    fantasy = {'kind': 'candidate', 'mode': 'agents', 'plausibility': 'fantastical', 'candidate': None}
    assert confidence(fantasy, None, None, None, True)['tier'] == 'very-low'
    franchise = {'kind': 'franchise', 'mode': 'backbone', 'plausibility': 'documented'}
    shaky = {'n': 2, 'spans_zero': True, 'paraphrase_flip': True}
    assert confidence(franchise, None, None, shaky, False)['tier'] == 'high'  # cross-check interviews move nothing
    both = combine_tiers([confidence(franchise, None, None, None, False), confidence(fantasy, None, None, None, True)])
    assert both['tier'] == 'very-low'


def test_blend_weak_evidence_barely_moves():
    d = np.full(200, 0.3) + np.linspace(-0.05, 0.05, 200)
    out = blend({'draws': {'dt': d.copy(), 'dr': d.copy(), 'do': d.copy()}}, {'dr': (2.0, 5.0, 1)})
    assert abs(out['draws']['dr'].mean() - 0.3) < 0.01 and out['evidence_blend']['dr']['evidence_weight'] < 0.01


def test_misread_forces_very_low():
    """When half or more of the people interviewed took the news to be about the
    other candidate, the tier is very-low whatever it started at; fewer misreads
    only flag it (and over a quarter costs one step)."""
    spec = {'kind': 'franchise', 'mode': 'agents', 'plausibility': 'documented'}
    steady = {'n': 40, 'spans_zero': False, 'paraphrase_flip': False, 'exposed': False}
    assert confidence(spec, None, None, steady | {'checked': 40, 'misread': 0}, False)['tier'] == 'high'
    for wrong in (20, 31, 40):
        c = confidence(spec, None, None, steady | {'checked': 40, 'misread': wrong}, False)
        assert c['tier'] == 'very-low', (wrong, c)
        assert 'misread-change' in c['flags']
    c = confidence(spec, None, None, steady | {'checked': 40, 'misread': 4}, False)
    assert c['tier'] == 'high' and 'misread-change' in c['flags']
    assert confidence(spec, None, None, steady | {'checked': 40, 'misread': 12}, False)['tier'] == 'medium'
    # A combination is as sure as its least sure what-if.
    assert combine_tiers([confidence(spec, None, None, steady | {'checked': 4, 'misread': 2}, False),
                          confidence(spec, None, None, steady, False)])['tier'] == 'very-low'
