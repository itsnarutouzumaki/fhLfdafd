.PHONY: test api frontend-test frontend-build verify-elexon

test:
	pytest

api:
	uvicorn app.main:app --reload --app-dir backend --port 8000

frontend-test:
	cd frontend && npm test

frontend-build:
	cd frontend && npm run build

verify-elexon:
	python scripts/verify_elexon.py
