.PHONY: help install dev test lint fmt cov serve collect index eval clean

help:
	@echo "install  - install runtime dependencies"
	@echo "dev      - install dev + runtime dependencies (editable)"
	@echo "test     - run the test suite"
	@echo "lint     - ruff check"
	@echo "fmt      - ruff format"
	@echo "cov      - test suite with coverage report"
	@echo "serve    - run the API + web interface on :8000"
	@echo "collect  - fetch the corpus (respects the source registry)"
	@echo "index    - build the retrieval index"
	@echo "eval     - replay the evaluation set and print the figures"

install:
	pip install -r requirements.txt

dev:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check src tests

fmt:
	ruff format src tests

cov:
	pytest --cov=src/pharmeazor --cov-report=term-missing

serve:
	uvicorn pharmeazor.api.main:app --reload --port 8000

collect:
	python scripts/collect.py

index:
	python scripts/build_index.py

eval:
	python scripts/run_eval.py

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov build dist
