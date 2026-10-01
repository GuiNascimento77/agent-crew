# Atalhos para as tarefas do dia a dia.
# Usar: `make` ou `make <alvo>`. Ver todos os alvos: `make help`.

.DEFAULT_GOAL := help

PYTHON ?= python3
VENV   ?= .venv
BIN    := $(VENV)/bin

.PHONY: help install dev test test-verbose lint format check run serve clean

help: ## Mostra esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Instala o projeto (sem dependências de desenvolvimento)
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install -e .

dev: ## Instala o projeto com as ferramentas de desenvolvimento
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install -e ".[dev]"

test: ## Roda os testes
	$(BIN)/pytest -q

test-verbose: ## Roda os testes mostrando cada um
	$(BIN)/pytest -v

lint: ## Verifica o estilo do código (precisa de ruff instalado)
	$(BIN)/ruff check src tests || echo "ruff não instalado: pip install ruff"

format: ## Formata o código automaticamente
	$(BIN)/ruff format src tests || echo "ruff não instalado: pip install ruff"

check: test ## Testes + estilo (use isto antes de commitar)
	$(BIN)/ruff check src tests
	$(BIN)/ruff format --check src tests

run: ## Executa o time no modo demonstração
	$(BIN)/agent-crew run "Como funcionam agentes de IA em 2026?"

serve: ## Sobe a API HTTP
	$(BIN)/agent-crew serve

clean: ## Remove caches e artefatos de build
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
