.PHONY: help install dev migrate makemigrations shell test lint format check run superuser clean

help:
	@echo "SmartyTask v2 — make targets:"
	@echo ""
	@echo "  install       Install all deps via uv"
	@echo "  dev           Run dev server on :8000"
	@echo "  migrate       Apply DB migrations"
	@echo "  makemigrations  Generate new migrations"
	@echo "  superuser     Create a Django superuser"
	@echo "  shell         Django shell_plus (or shell)"
	@echo "  test          Run pytest"
	@echo "  lint          Run ruff check"
	@echo "  format        Run ruff format"
	@echo "  check         Run Django system checks"
	@echo "  clean         Remove caches"

install:
	uv sync --extra dev

dev:
	uv run python manage.py runserver 0.0.0.0:8000

migrate:
	uv run python manage.py migrate

makemigrations:
	uv run python manage.py makemigrations

superuser:
	uv run python manage.py createsuperuser

shell:
	uv run python manage.py shell

test:
	uv run pytest

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

check:
	uv run python manage.py check --deploy

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	find . -type d -name .ruff_cache -prune -exec rm -rf {} +
	find . -type d -name .mypy_cache -prune -exec rm -rf {} +
