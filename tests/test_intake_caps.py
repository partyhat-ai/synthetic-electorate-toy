"""The intake's dollar caps (intake.py, Money)."""
import json
import time

import pytest

from simharness import intake, llm


def _ledger(tmp_path, rows):
    f = tmp_path / 'spend.jsonl'
    f.write_text(''.join(json.dumps(r) + '\n' for r in rows) + 'not json\n')
    return f


def test_left_for_is_the_smaller_remainder(tmp_path):
    today = time.strftime('%Y-%m-%d', time.gmtime())
    f = _ledger(tmp_path, [
        {'day': today, 'dollars': 12.5, 'who': 'ana'},
        {'day': today, 'dollars': 4.0, 'who': 'ben'},
        {'day': '2000-01-01', 'dollars': 30.0, 'who': 'ana'},  # another day: all-time only
        {'day': today, 'dollars': 99.0, 'who': None},            # no key: neither cap
        {'day': today, 'dollars': 99.0},
    ])
    assert llm.spent(ledger=f) == (46.5, {'ana': 12.5, 'ben': 4.0})
    assert intake.left_for('ana', f, key_cap=100, total_cap=150) == pytest.approx(87.5)   # the key's day binds
    assert intake.left_for('ben', f, key_cap=100, total_cap=60) == pytest.approx(13.5)    # the all-time total binds
    assert intake.left_for('ana', f, key_cap=10, total_cap=150) == 0.0
    assert intake.left_for(None, f, key_cap=100, total_cap=150) == 0.0


def test_defaults_are_100_a_key_a_day_and_150_in_all():
    assert (intake.KEY_DAILY_USD, intake.TOTAL_USD) == (100.0, 150.0)


def test_budget_stops_at_its_ceiling():
    b = intake.Budget(ceiling=1.0)
    b.add(0.6, 'compile', record=False)
    with pytest.raises(SystemExit, match='budget'):
        b.add(0.5, 'research', record=False)
    assert intake.Budget().ceiling is None
