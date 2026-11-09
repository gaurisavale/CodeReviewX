# CodeReviewX

**Explainable code-health reviewer for Python.** It measures a codebase with a deterministic AST analyzer, ranks which functions are most likely to need a bug fix using a model trained on real open-source history, explains every number, and can apply measured, behaviour-preserving refactorings.

```
MEASURE (AST analyzer)  ->  RANK (trained model)  ->  EXPLAIN (rules or LLM)  ->  VISUALIZE  ->  REFACTOR (re-measured)
```

Symbiosis Institute of Technology, Nagpur. Project-based learning (PBL) project.

## What is in the box

| Layer | What it does | Where |
| --- | --- | --- |
| Analyzer | Parses with Python `ast`; cyclomatic and cognitive complexity, nesting, length, parameters, call graph, 13 quality factors, scope-aware undefined-name detection, AST-fingerprint duplication | `backend/analyzers/` |
| Scoring | Factor scores, function health (critical findings cap it at 49), file health, grades, optional data-calibrated weights | `backend/services/scoring.py` |
| ML model | Logistic regression on 147,097 functions from 11 repositories, labelled from bug-fix commits (SZZ-style). Evaluated leave-one-repository-out. Predictions decompose into per-feature contributions | `backend/ml/` |
| Refactor engine | Constant hoisting, guard clauses, extract-method with data-flow analysis; re-analysed for before and after scores | `backend/services/refactor.py` |
| Interpretation | Rule-based explainer by default; optional Claude call, validated and never allowed to invent metrics | `backend/services/llm.py` |
| API | FastAPI, SQLAlchemy persistence, project history, ZIP and GitHub repository scans, OpenAPI docs at `/docs` | `backend/main.py`, `backend/routers/` |
| Dashboard | Next.js, heat map, call graph, explanation sidebar, findings, code viewer, refactor diff, repo scan, model card, history, projects | `frontend/` |

It runs with no API key. The key only upgrades the wording of explanations.

## The ML model, honestly

* **Data.** 11 Python libraries (flask, click, jinja, werkzeug, requests, httpx, rich, tqdm, scrapy, celery, attrs). For each bug-fix commit (found by message heuristics) the parent version of every changed non-test file is analysed. A function is labelled defective if the fix deleted or changed one of its lines. 147,097 function samples, 5,736 defective (3.9%).
* **Evaluation.** Leave-one-repository-out: each repo is held out in turn, so no project leaks into its own test set.

| Model | AUC (mean of 11 folds) | Recall in riskiest 20% |
| --- | --- | --- |
| Base rate | 0.500 | 19% |
| Lines of code only | 0.714 | 48% |
| Cyclomatic complexity only | 0.675 | 45% |
| Rule-based health score (no learning) | 0.690 | 46% |
| Logistic regression, 13 factor scores | 0.697 | 47% |
| **Logistic regression, all features (shipped)** | **0.722** | **49%** |
| Gradient boosting, all features | 0.731 | 51% |

* Defect prediction is a hard problem. A modest gain over a strong size baseline is the realistic result, and it is reported as such. The shipped model is the logistic regression because every prediction can be explained exactly.
* Limitations: labels are heuristic and noisy; libraries only; the dashboard probability means "chance a later fix touches this function, among files a fix touched", not an absolute bug probability. Scanning a repo that is in the training set (for example click) is not a fair test.
* The 13 hand-set factor weights were also re-estimated from data (`ml/artifacts/learned_weights.json`). Turn them on with `CODEREVIEWX_USE_LEARNED_WEIGHTS=true`.

Rebuild everything from scratch:

```bash
cd backend
sh ml/fetch_repos.sh          # shallow clones, about 250 MB
python -m ml.build_dataset    # labelled dataset, a few minutes
python -m ml.train            # metrics, model, figures in ml/artifacts/
```

## Run it

```bash
# backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn main:app --reload --port 8001      # http://localhost:8001/docs

# frontend (second terminal)
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8001/api" > .env.local
npm run dev                                # http://localhost:3000
```

Or everything at once: `docker compose up --build`. Shortcuts are in the `Makefile`.

## API

| Method and path | Purpose |
| --- | --- |
| `POST /api/analyze` | Analyse one file; returns scores, findings, per-function defect risk, graph, explanation, refactor |
| `POST /api/analyze/zip` | Analyse every `.py` file in an uploaded ZIP (never extracted to disk) |
| `POST /api/analyze/github` | Shallow-clone a public GitHub repo and analyse it |
| `GET /api/history`, `GET /api/history/{id}` | Stored runs; file runs re-open deterministically |
| `GET/POST/DELETE /api/projects` | Projects with health trend over time |
| `GET /api/model` | Model card: data, protocol, comparison, coefficients, caveats |
| `GET /api/health`, `/api/samples`, `/api/demo` | Status and bundled samples |

Settings come from `CODEREVIEWX_*` environment variables (see `backend/.env.example`): database URL (SQLite by default, Postgres works), CORS origins, upload and clone limits, log level.

## Engineering

* 26 automated tests (`cd backend && python -m pytest`): analyzer rules, scoring invariants, regression guard for the reference scores, refactor differential tests (original and refactored code must agree on a grid of inputs), ML feature and prediction checks, and API tests including ZIP handling and project history.
* GitHub Actions workflow runs backend tests, the TypeScript check and the production build.
* Input safety: size limits, zip-bomb guard, no extraction to disk, GitHub URL allow-list, clone timeout, non-root Docker user.
* Request logging with request ids and timing headers.

## Known limits

Python only, one file's functions at a time (repo scans analyse files independently, so cross-file calls are not linked). Refactoring covers module-level functions and `ast.unparse` drops comments in changed functions. Findings that need judgement, such as SQL built from strings or an undefined name, are never auto-fixed.
