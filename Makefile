.PHONY: setup backend frontend test dataset train docker
setup:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
	cd frontend && npm install
backend:
	cd backend && . .venv/bin/activate && uvicorn main:app --reload --port 8001
frontend:
	cd frontend && npm run dev
test:
	cd backend && . .venv/bin/activate && python -m pytest -q
dataset:   ## clone repos listed in ml/repos.txt and build the labelled dataset
	cd backend && sh ml/fetch_repos.sh && python -m ml.build_dataset
train:
	cd backend && python -m ml.train
docker:
	docker compose up --build
