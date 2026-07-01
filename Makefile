.DEFAULT_GOAL := help
SHELL := /bin/bash

# Utilise le venv s'il existe, sinon le python système.
PY := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)
PIP := $(PY) -m pip

.PHONY: help install check fmt lint type test test-py test-ui demo demo-phase1 doctor serve ui-dev clean

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Crée le venv et installe les dépendances de dev
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

fmt: ## Formate le code (ruff)
	$(PY) -m ruff format src tests scripts
	$(PY) -m ruff check --fix src tests scripts

lint: ## Lint (ruff)
	$(PY) -m ruff check src tests scripts

type: ## Vérification de types (mypy strict)
	$(PY) -m mypy

test-py: ## Tests Python (pytest)
	$(PY) -m pytest

test-ui: ## Tests UI (vitest) — seulement si l'UI est installée
	@if [ -d ui/node_modules ]; then cd ui && npm run test -- --run; \
	else echo "⏭  UI non installée (cd ui && npm install) — tests UI ignorés"; fi

test: test-py test-ui ## Tous les tests

check: lint type test ## Filet de sécurité complet : lint + types + tests

demo-phase1: ## Joue la séquence de réveil ATLAS en mock (aucun credential)
	$(PY) scripts/demo_phase1.py

demo: demo-phase1 ## Alias de demo-phase1

doctor: ## Diagnostique l'environnement (outils présents/absents, mode effectif)
	$(PY) scripts/doctor.py

serve: ## Lance l'API + WebSocket (mode mock par défaut)
	$(PY) -m jarvis serve

ui-dev: ## Lance l'UI dans le navigateur (Vite)
	cd ui && npm run dev

clean: ## Supprime caches et artefacts
	rm -rf .mypy_cache .ruff_cache .pytest_cache **/__pycache__ var/*.db*
