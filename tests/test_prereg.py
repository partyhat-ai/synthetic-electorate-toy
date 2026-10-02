"""Benchmark isolation."""
import re
from pathlib import Path

import simharness

PKG = Path(simharness.__file__).resolve().parent


def test_benchmarks_isolated():
    """Only evaluate-stage code may read held-out benchmarks: no other module
    imports benchmarks.py or opens a path under benchmarks/."""
    bad = re.compile(r"import\s+benchmarks|from\s+\.\s+import\s+[^\n]*\bbenchmarks\b|['\"]benchmarks/")
    for f in PKG.glob('*.py'):
        if f.name == 'benchmarks.py':
            continue
        hits = [l.strip() for l in f.read_text().splitlines() if bad.search(l)]
        assert not hits, (f.name, hits)

