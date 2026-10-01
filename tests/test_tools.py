"""Testes da ferramenta de busca e da configuração."""

from __future__ import annotations

import pytest

from agent_crew.config import Settings, get_settings, reset_settings_cache
from agent_crew.tools.search import MockSearch, SearchHit, build_search_tool


async def test_mock_search_respeita_o_limite_de_resultados():
    ferramenta = MockSearch(max_results=2)
    resultados = await ferramenta.search("qualquer coisa")

    assert len(resultados) == 2
    assert all(isinstance(r, SearchHit) for r in resultados)
    assert all(r.url.startswith("http") for r in resultados)


def test_search_hit_formata_como_bullet():
    hit = SearchHit(title="Título", url="https://exemplo.com", snippet="Resumo")
    linha = hit.as_bullet()

    assert "Título" in linha
    assert "https://exemplo.com" in linha
    assert "Resumo" in linha


def test_build_search_tool_devolve_o_mock_por_padrao():
    settings = Settings(search_backend="mock")
    assert isinstance(build_search_tool(settings), MockSearch)


def test_build_search_tool_exige_chave_para_o_tavily():
    settings = Settings(search_backend="tavily", tavily_api_key=None)
    with pytest.raises(RuntimeError, match="TAVILY_API_KEY"):
        build_search_tool(settings)


# =====================================================================
#  Configuração: a validação que roda ANTES de qualquer gasto
# =====================================================================


def test_provider_mock_nao_exige_chave_nenhuma():
    Settings(provider="mock").validate_for_run()  # não deve levantar erro


def test_provider_openai_sem_chave_falha_com_mensagem_util():
    settings = Settings(provider="openai")
    with pytest.raises(RuntimeError) as erro:
        settings.validate_for_run()

    mensagem = str(erro.value)
    assert "OPENAI_API_KEY" in mensagem
    assert "mock" in mensagem, "a mensagem deve sugerir a alternativa sem chave"


def test_settings_podem_ser_sobrescritas_com_model_copy():
    """É assim que o CLI aplica os `--flags` sem sujar a configuração global."""
    original = Settings(provider="mock")
    alterada = original.model_copy(update={"provider": "openai", "model_name": "gpt-4o"})

    assert original.provider == "mock"
    assert alterada.provider == "openai"
    assert alterada.model_name == "gpt-4o"


def test_get_settings_le_as_variaveis_de_ambiente(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENT_CREW_MODEL_NAME", "modelo-vindo-do-ambiente")
    reset_settings_cache()

    try:
        assert get_settings().model_name == "modelo-vindo-do-ambiente"
    finally:
        reset_settings_cache()
