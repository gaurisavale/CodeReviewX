import pytest

from ml.features import FEATURES, extract_module
from ml.model import get_model

pytestmark = pytest.mark.skipif(get_model() is None, reason="model artifacts not trained")


def test_feature_vector_is_complete_and_numeric():
    f = extract_module("def f(a, b):\n    if a:\n        return b\n    return 0\n")[0]["features"]
    assert set(f) == set(FEATURES)
    assert all(isinstance(v, (int, float)) for v in f.values())


def test_prediction_is_probability_with_drivers():
    m = get_model()
    f = extract_module("def f(a):\n    for i in a:\n        if i:\n            while i:\n                i -= 1\n")[0]["features"]
    p = m.predict(f)
    assert 0.0 <= p["probability"] <= 1.0 and p["band"] in ("low", "medium", "high")
    assert p["drivers"] and all({"name", "effect", "direction"} <= set(d) for d in p["drivers"])


def test_riskier_code_gets_higher_probability():
    m = get_model()
    small = extract_module('def add(a, b):\n    """Add."""\n    return a + b\n')[0]["features"]
    big_src = "def g(a, b, c, d, e, f):\n" + "".join(f"    if a == {i}:\n        for x in b:\n            if x:\n                c += {i}\n" for i in range(6)) + "    return c\n"
    big = extract_module(big_src)[0]["features"]
    assert m.predict(big)["probability"] > m.predict(small)["probability"]


def test_model_card_reports_held_out_auc():
    c = get_model().card()
    assert c["protocol"] == "leave-one-repository-out" and 0.6 < c["auc"] < 1.0
