"""Held-out benchmark isolation.

Only Run.verify and Run.evaluate (pipeline.py) may reach simharness/benchmarks.py
or the cache's benchmarks/ folder. The check parses every module under
simharness/ and scripts/ (not a text grep), so an import in any spelling, an
attribute path, a dynamic import, a path built from parts, or a listing of the
cache root is caught; config and profile JSON is scanned for benchmark paths.
"""
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {('simharness/pipeline.py', 'Run', 'verify'), ('simharness/pipeline.py', 'Run', 'evaluate')}
# A benchmark module or path component: simharness.benchmarks, .benchmarks, benchmarks/, \benchmarks.
NAMED = re.compile(r'(^|[/\\.])benchmarks($|[/\\.])|corder_wolbrecht', re.I)
DYNAMIC = {'import_module', '__import__', 'run_module', 'run_path', 'spec_from_file_location', 'SourceFileLoader'}
LISTING = {'glob', 'rglob', 'iterdir', 'walk', 'listdir', 'scandir'}


def _docstrings(tree: ast.AST) -> set[int]:
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                out.add(id(first.value))
    return out


def _is_cache_root(node: ast.AST) -> bool:
    """CACHE itself, or str(CACHE) / os.fspath(CACHE): the cache root, not a named folder under it."""
    if isinstance(node, ast.Name):
        return node.id == 'CACHE'
    if isinstance(node, ast.Call) and len(node.args) == 1:
        f = node.func
        name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ''
        return name in ('str', 'fspath', 'Path') and _is_cache_root(node.args[0])
    return False


def violations(source: str, rel: str) -> list[str]:
    """Every way `source` (the file at repo path `rel`) reaches the held-out benchmarks outside ALLOWED."""
    tree = ast.parse(source, rel)
    docs = _docstrings(tree)
    out: list[str] = []

    def visit(node: ast.AST, scope: tuple[str, ...]) -> None:
        allowed = any((rel, *scope[i:i + 2]) in ALLOWED for i in range(len(scope)))
        where = f'{rel}:{getattr(node, "lineno", "?")}'
        if not allowed:
            if isinstance(node, ast.Import):
                out.extend(f'{where} import {a.name}' for a in node.names if NAMED.search(a.name))
            elif isinstance(node, ast.ImportFrom):
                mod = ('.' * node.level) + (node.module or '')
                if NAMED.search(mod) or any(a.name == 'benchmarks' for a in node.names):
                    out.append(f'{where} from {mod} import {", ".join(a.name for a in node.names)}')
            elif isinstance(node, ast.Name) and node.id == 'benchmarks':
                out.append(f'{where} name benchmarks')
            elif isinstance(node, ast.Attribute) and node.attr == 'benchmarks':
                out.append(f'{where} attribute .benchmarks')
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
                if NAMED.search(node.value) or node.value.strip('/\\').lower() == 'benchmarks':
                    out.append(f'{where} string {node.value!r}')
            elif isinstance(node, ast.Call):
                f = node.func
                name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ''
                if name in DYNAMIC:
                    out.append(f'{where} dynamic import {name}(): the module it loads can\'t be checked')
                if name in LISTING and (any(_is_cache_root(a) for a in node.args)
                                        or (isinstance(f, ast.Attribute) and _is_cache_root(f.value))):
                    out.append(f'{where} {name}() over the cache root, which holds benchmarks/')
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            scope = (*scope, node.name)
        for child in ast.iter_child_nodes(node):
            visit(child, scope)

    visit(tree, ())
    return out


def _sources() -> list[Path]:
    files = [*ROOT.glob('simharness/**/*.py'), *ROOT.glob('scripts/**/*.py')]
    return sorted(f for f in files if f.name != 'benchmarks.py' or f.parent.name != 'simharness')


def test_benchmarks_isolated():
    """No module or script outside Run.verify and Run.evaluate reaches the held-out benchmarks."""
    found = [v for f in _sources() for v in violations(f.read_text(), f.relative_to(ROOT).as_posix())]
    assert not found, '\n'.join(found)


def test_allowed_stages_do_read_the_benchmarks():
    """The allowance is used, so a renamed stage can't leave it pointing at nothing."""
    src = (ROOT / 'simharness/pipeline.py').read_text()
    unscoped = violations(src, 'simharness/pipeline.py:unscoped')
    assert any('from . import benchmarks' in v for v in unscoped), unscoped


def test_configs_and_profiles_name_no_benchmark_path():
    """A data path in a config or profile is read by data.py, so none may point into benchmarks/."""
    def strings(x):
        if isinstance(x, str):
            yield x
        elif isinstance(x, dict):
            for k, v in x.items():
                yield k
                yield from strings(v)
        elif isinstance(x, list):
            for v in x:
                yield from strings(v)
    hits = [f'{f.relative_to(ROOT)}: {s!r}' for f in sorted([*ROOT.glob('configs/*.json'), *ROOT.glob('profiles/*.json')])
            for s in strings(json.loads(f.read_text())) if NAMED.search(s)]
    assert not hits, '\n'.join(hits)


BYPASSES = {
    'import benchmarks': 'import simharness.benchmarks',
    'import as': 'import simharness.benchmarks as b',
    'from package': 'from simharness import benchmarks',
    'from relative': 'from . import benchmarks',
    'from submodule': 'from .benchmarks import corder_wolbrecht',
    'from absolute submodule': 'from simharness.benchmarks import natural_experiment as n',
    'attribute path': 'import simharness\nx = simharness.benchmarks.corder_wolbrecht()',
    'importlib': 'import importlib\nm = importlib.import_module("simharness." + "bench" + "marks")',
    'dunder import': 'm = __import__(name)',
    'path parts': 'from .config import CACHE\nf = CACHE / "benchmarks" / "x.csv"',
    'path string': 'f = CACHE / "benchmarks/x.csv"',
    'file stem': 'f = CACHE / folder / "corder_wolbrecht_turnout_by_sex.csv"',
    'f-string': 'f = f"{CACHE}/benchmarks/{name}"',
    'cache listing': 'files = list(CACHE.rglob("*.csv"))',
    'os listing': 'import os\nfor d, _, fs in os.walk(str(CACHE)): pass',
    'nested in a function': 'def fit():\n    from . import benchmarks\n    return benchmarks',
    'other method of Run': 'class Run:\n    def backbone(self):\n        from . import benchmarks',
}


def test_checker_catches_every_known_bypass():
    missed = [k for k, src in BYPASSES.items() if not violations(src, 'simharness/backbone.py')]
    assert not missed, missed


def test_checker_allows_only_the_validation_stages():
    src = 'class Run:\n    def verify(self):\n        from . import benchmarks\n        return benchmarks.corder_wolbrecht_any_year()\n'
    assert violations(src, 'simharness/pipeline.py') == []
    assert violations(src, 'simharness/publish.py')
    assert violations(src.replace('class Run', 'class Other'), 'simharness/pipeline.py')
    # Mentioning the benchmark in a docstring or comment is fine.
    assert violations('"""Scored against benchmarks/ later."""\n# benchmarks/\nx = 1\n', 'simharness/x.py') == []
