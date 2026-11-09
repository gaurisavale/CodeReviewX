import io
import zipfile

from utils.demo_data import SAMPLES


def test_health(client):
    j = client.get("/api/health").json()
    assert j["status"] == "ok" and "version" in j


def test_analyze_returns_scores_and_defect_risk(client):
    r = client.post("/api/analyze", json={"code": SAMPLES["orders"][1], "filename": "orders.py"})
    assert r.status_code == 200
    j = r.json()
    assert j["summary"]["overall_health"] == 62
    assert len(j["factors"]) == 13
    assert "history_id" in j
    assert all("defect_risk" in f for f in j["functions"])
    assert j["explanation"]["source"] in ("claude", "fallback", "rule-based") or j["explanation"]["source"]


def test_syntax_error_is_422_with_line(client):
    r = client.post("/api/analyze", json={"code": "def f(:\n    pass\n"})
    assert r.status_code == 422 and r.json()["detail"]["line"] == 1


def test_empty_code_is_422(client):
    assert client.post("/api/analyze", json={"code": "   "}).status_code == 422


def test_history_roundtrip(client):
    j = client.post("/api/analyze", json={"code": SAMPLES["health"][1], "filename": "h.py"}).json()
    again = client.get(f"/api/history/{j['history_id']}").json()
    assert again["summary"]["overall_health"] == j["summary"]["overall_health"]
    assert any(x["id"] == j["history_id"] for x in client.get("/api/history").json())


def test_project_lifecycle_and_trend(client):
    p = client.post("/api/projects", json={"name": "trend-demo"}).json()
    assert client.post("/api/projects", json={"name": "trend-demo"}).status_code == 409
    client.post("/api/analyze", json={"code": SAMPLES["health"][1], "filename": "h.py", "project_id": p["id"]})
    client.post("/api/analyze", json={"code": "def add(a, b):\n    return a + b\n", "filename": "h.py", "project_id": p["id"]})
    got = client.get(f"/api/projects/{p['id']}").json()
    assert got["runs"] == 2 and len(got["trend"]) == 2
    assert client.delete(f"/api/projects/{p['id']}").status_code == 204


def test_zip_analysis_aggregates_and_reports_bad_files(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("pkg/orders.py", SAMPLES["orders"][1])
        z.writestr("pkg/health.py", SAMPLES["health"][1])
        z.writestr("pkg/broken.py", "def (")
        z.writestr("venv/lib/skip.py", "x = 1")
        z.writestr("README.md", "# hi")
    r = client.post("/api/analyze/zip", files={"file": ("p.zip", buf.getvalue())})
    assert r.status_code == 200
    j = r.json()
    assert j["project"]["files"] == 2 and len(j["errors"]) == 1
    assert j["project"]["riskiest_functions"]


def test_zip_rejects_non_zip(client):
    assert client.post("/api/analyze/zip", files={"file": ("x.zip", b"not a zip")}).status_code == 422


def test_github_url_is_validated(client):
    r = client.post("/api/analyze/github", json={"url": "file:///etc/passwd"})
    assert r.status_code == 422


def test_model_card(client):
    r = client.get("/api/model")
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        assert r.json()["comparison"] and r.json()["coefficients"]
