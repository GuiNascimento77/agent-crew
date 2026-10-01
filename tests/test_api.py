"""Testes da API HTTP.

Usamos `ASGITransport`: ele conversa direto com o app FastAPI, sem abrir
porta nem subir servidor. É rápido e não depende de rede — o jeito certo
de testar APIs em Python moderno.
"""

from __future__ import annotations

import json

import httpx
import pytest

from agent_crew.api import app
from agent_crew.config import reset_settings_cache


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def test_health(client: httpx.AsyncClient):
    resposta = await client.get("/health")
    assert resposta.status_code == 200

    dados = resposta.json()
    assert dados["status"] == "ok"
    assert dados["provider"] == "mock"


async def test_agents_lista_os_quatro_na_ordem(client: httpx.AsyncClient):
    resposta = await client.get("/agents")
    assert resposta.status_code == 200

    agentes = resposta.json()
    assert [a["name"] for a in agentes] == ["pesquisador", "analista", "redator", "revisor"]
    assert [a["order"] for a in agentes] == [1, 2, 3, 4]


async def test_providers_nao_vaza_nenhuma_chave(client: httpx.AsyncClient):
    resposta = await client.get("/providers")
    assert resposta.status_code == 200

    dados = resposta.json()
    assert dados["current"] == "mock"
    assert dados["available"]["mock"] is True
    assert dados["available"]["openai"] is False  # nenhuma chave no ambiente de teste

    corpo = resposta.text.lower()
    assert "sk-" not in corpo, "a API nunca deve devolver chaves de API"


async def test_crew_run_roda_o_time_e_devolve_o_pacote_completo(client: httpx.AsyncClient):
    resposta = await client.post(
        "/crew/run",
        json={"question": "O que é o protocolo MCP?", "audience": "iniciantes"},
    )
    assert resposta.status_code == 200

    dados = resposta.json()
    assert dados["brief"] is not None
    assert dados["analysis"] is not None
    assert dados["draft"] is not None
    assert dados["review"] is not None
    assert dados["review"]["approved"] is True
    assert dados["revisions"] == 1


async def test_crew_run_valida_a_entrada(client: httpx.AsyncClient):
    """Pergunta vazia deve ser rejeitada pelo Pydantic antes de gastar tokens."""
    resposta = await client.post("/crew/run", json={"question": ""})
    assert resposta.status_code == 422


async def test_crew_run_devolve_erro_claro_quando_falta_a_chave(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("AGENT_CREW_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    reset_settings_cache()
    try:
        resposta = await client.post("/crew/run", json={"question": "Qualquer tema"})
        assert resposta.status_code == 400
        assert "OPENAI_API_KEY" in resposta.json()["detail"]
    finally:
        reset_settings_cache()


async def test_crew_stream_emite_um_evento_por_agente(client: httpx.AsyncClient):
    async with client.stream(
        "POST", "/crew/stream", json={"question": "O que é LangGraph?"}
    ) as resposta:
        assert resposta.status_code == 200
        corpo = (await resposta.aread()).decode("utf-8")

    eventos = [linha for linha in corpo.splitlines() if linha.startswith("event: ")]
    nomes = [linha.replace("event: ", "") for linha in eventos]

    assert nomes[:4] == ["pesquisador", "analista", "redator", "revisor"]
    assert nomes[-1] == "done"

    # O último evento traz o resultado completo.
    ultimo = [linha for linha in corpo.splitlines() if linha.startswith("data: ")][-1]
    resultado = json.loads(ultimo.replace("data: ", ""))
    assert resultado["draft"]["markdown"]
