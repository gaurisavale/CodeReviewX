import ast

from services.pipeline import analyze
from utils.demo_data import SAMPLES


def test_refactor_compiles_and_improves_or_keeps_score():
    r = analyze(SAMPLES["orders"][1], "orders.py")["refactor"]
    assert r["available"] and r["compiles"]
    ast.parse(r["refactored"])
    assert r["after"]["overall_health"] >= r["before"]["overall_health"]
    assert r["after"]["max_complexity"] <= r["before"]["max_complexity"]


def test_refactor_preserves_behaviour_health_sample():
    """Differential test: original and refactored health-risk function agree on a grid of inputs."""
    r = analyze(SAMPLES["health"][1], "health.py")["refactor"]
    assert r["available"]
    ns_a, ns_b = {}, {}
    exec(r["original"], ns_a)
    exec(r["refactored"], ns_b)
    name = next(k for k, v in ns_a.items() if callable(v) and not k.startswith("_"))
    import inspect
    n = len(inspect.signature(ns_a[name]).parameters)
    import itertools
    vals = [0, 1, 20, 30, 45, 70, 95, 130, 200]
    for args in itertools.islice(itertools.product(vals, repeat=n), 400):
        try:
            a = ns_a[name](*args)
        except Exception as e:
            a = type(e)
        try:
            b = ns_b[name](*args)
        except Exception as e:
            b = type(e)
        assert a == b, (args, a, b)
