from analyzers.structural import analyze_source
from services import scoring
from services.pipeline import analyze
from utils.demo_data import SAMPLES


def fn(code, name):
    return next(f for f in analyze_source(code).functions if f.name == name)


def test_cyclomatic_counts_branches_loops_and_bool_ops():
    f = fn("def f(a, b):\n    if a and b:\n        return 1\n    for i in a:\n        pass\n    return 0\n", "f")
    assert f.complexity == 1 + 1 + 1 + 1  # if, and, for


def test_elif_is_not_extra_nesting():
    code = "def f(x):\n    if x == 1:\n        return 1\n    elif x == 2:\n        return 2\n    elif x == 3:\n        return 3\n    return 0\n"
    f = fn(code, "f")
    assert f.nesting == 1
    assert f.elif_len >= 3


def test_nesting_depth():
    code = "def f(a):\n    for i in a:\n        if i:\n            while i:\n                i -= 1\n"
    assert fn(code, "f").nesting == 3


def test_undefined_name_is_critical():
    r = analyze("def f(x):\n    return x + missing_value\n", with_refactor=False)
    assert any(i["rule"] == "undefined_name" and i["severity"] == "critical" for i in r["issues"])


def test_sql_string_building_is_critical():
    r = analyze("def f(cur, name):\n    cur.execute(\"SELECT * FROM t WHERE n='\" + name + \"'\")\n", with_refactor=False)
    assert any(i["factor"] == "security" and i["severity"] == "critical" for i in r["issues"])


def test_clean_function_scores_high():
    r = analyze('def add(a, b):\n    """Add two numbers."""\n    return a + b\n', with_refactor=False)
    assert r["summary"]["overall_health"] >= 90


def test_critical_finding_caps_health_at_49():
    r = analyze("def f(x):\n    return eval(x)\n", with_refactor=False)
    assert r["functions"][0]["health_score"] <= 49


def test_scores_are_deterministic():
    code = SAMPLES["orders"][1]
    a, b = analyze(code, "o.py", with_refactor=False), analyze(code, "o.py", with_refactor=False)
    assert a["summary"] == b["summary"]


def test_weights_sum():
    assert sum(scoring.WEIGHTS.values()) == 105
    assert set(scoring.WEIGHTS) == set(scoring.FACTOR_KEYS) and len(scoring.FACTOR_KEYS) == 13


def test_reference_sample_scores():
    """Regression guard for the numbers quoted in the project report."""
    o = analyze(SAMPLES["orders"][1], "orders.py")["summary"]
    assert (o["overall_health"], o["findings_total"], o["critical"], o["warning"], o["info"]) == (62, 43, 6, 21, 16)
    h = analyze(SAMPLES["health"][1], "health.py")["summary"]
    assert (h["overall_health"], h["findings_total"]) == (49, 12)
