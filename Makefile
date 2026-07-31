.PHONY: setup format lint typecheck test verify-assets check build clean

setup:
	uv sync --all-groups
	uv run pre-commit install

format:
	uv run ruff check --fix src tests
	uv run ruff format src tests

lint:
	uv run ruff format --check src tests
	uv run ruff check src tests

typecheck:
	uv run mypy

test:
	uv run pytest

verify-assets:
	uv run suanming assets --verify

check: lint typecheck test verify-assets

build: check
	uv build

clean:
	rm -rf build dist htmlcov .coverage coverage.xml .mypy_cache .pytest_cache .ruff_cache
