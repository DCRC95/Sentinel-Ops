PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
VENV_UVICORN := $(VENV)/bin/uvicorn
VENV_STREAMLIT := $(VENV)/bin/streamlit
VENV_PYTEST := $(VENV)/bin/pytest
VENV_RUFF := $(VENV)/bin/ruff
VENV_BLACK := $(VENV)/bin/black

.PHONY: install dev-api dev-ui seed test lint format init-db migrate stress

install:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -e ".[dev]"

dev-api:
	$(VENV_UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

dev-ui:
	$(VENV_STREAMLIT) run dashboard/app.py

seed:
	PYTHONPATH="$(CURDIR)" $(VENV_PYTHON) scripts/seed_demo.py --reset

test:
	$(VENV_PYTEST) -q

lint:
	$(VENV_RUFF) check .
	$(VENV_BLACK) --check .

format:
	$(VENV_BLACK) .
	$(VENV_RUFF) check --fix .

init-db:
	PYTHONPATH="$(CURDIR)" $(VENV_PYTHON) -m alembic upgrade head

migrate:
	PYTHONPATH="$(CURDIR)" $(VENV_PYTHON) -m alembic upgrade head

stress:
	PYTHONPATH="$(CURDIR)" $(VENV_PYTHON) scripts/simulate_failure.py
