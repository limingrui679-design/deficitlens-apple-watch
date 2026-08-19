PYTHON ?= python3

.PHONY: install lint typecheck test coverage demo verify build

install:
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

typecheck:
	$(PYTHON) -m mypy src scripts

test:
	$(PYTHON) -m pytest

coverage:
	$(PYTHON) -m pytest --cov=deficitlens --cov-report=term-missing --cov-report=html

demo:
	$(PYTHON) -m deficitlens demo --output artifacts/demo

verify:
	$(PYTHON) scripts/verify_release.py
	$(PYTHON) scripts/score_project.py

build:
	$(PYTHON) -m build
