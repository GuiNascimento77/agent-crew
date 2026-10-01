"""Configuração compartilhada dos testes.

A ideia central: TODOS os testes rodam no modo "mock". Isso significa:

  - nenhuma chamada à internet;
  - nenhum custo;
  - nenhuma chave de API necessária;
  - resultado previsível (o mesmo teste dá o mesmo resultado sempre).

É esse desenho que permite ter testes de um sistema de IA no CI sem pagar
nada e sem ficar "piscando" (resultado diferente a cada execução).
"""

from __future__ import annotations

import pytest

from agent_crew.config import Settings, reset_settings_cache


@pytest.fixture(autouse=True)
def _mock_environment(monkeypatch: pytest.MonkeyPatch):
    """Força o modo mock no ambiente, ignorando o que estiver no seu .env."""
    monkeypatch.setenv("AGENT_CREW_PROVIDER", "mock")
    monkeypatch.setenv("AGENT_CREW_SEARCH_BACKEND", "mock")
    monkeypatch.setenv("AGENT_CREW_MAX_REVISIONS", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    reset_settings_cache()
    yield
    reset_settings_cache()


@pytest.fixture
def settings() -> Settings:
    """Configuração pronta para testes (provedor mock)."""
    return Settings(
        provider="mock",
        search_backend="mock",
        max_revisions=1,
        model_name="modelo-de-teste",
    )
