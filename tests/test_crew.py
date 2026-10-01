"""Testes do fluxo completo e do roteamento do grafo.

Estes são os testes mais valiosos do projeto: eles provam que a ORQUESTRAÇÃO
está certa — quem trabalha, em que ordem, e quando o ciclo de revisão para.
"""

from __future__ import annotations

from langgraph.graph import END

from agent_crew.config import Settings
from agent_crew.crew import run_crew, stream_crew
from agent_crew.graph import (
    AGENT_SEQUENCE,
    WRITER,
    _route_after_review,
)
from agent_crew.schemas import CrewRequest, ReviewVerdict


def _settings(max_revisions: int = 1) -> Settings:
    return Settings(
        provider="mock", search_backend="mock", max_revisions=max_revisions, language="pt-BR"
    )


# =====================================================================
#  Roteamento: a decisão que controla o ciclo de revisão
# =====================================================================


def test_roteamento_termina_quando_aprovado():
    estado = {"review": ReviewVerdict(approved=True, score=9), "revisions": 0, "max_revisions": 3}
    assert _route_after_review(estado) == END


def test_roteamento_devolve_ao_redator_quando_reprovado_e_ainda_ha_tentativas():
    estado = {"review": ReviewVerdict(approved=False, score=5), "revisions": 0, "max_revisions": 2}
    assert _route_after_review(estado) == WRITER


def test_roteamento_termina_quando_o_limite_de_revisoes_e_atingido():
    """Sem esta trava, um revisor exigente criaria um loop infinito."""
    estado = {"review": ReviewVerdict(approved=False, score=4), "revisions": 2, "max_revisions": 2}
    assert _route_after_review(estado) == END


# =====================================================================
#  Fluxo completo
# =====================================================================


async def test_fluxo_completo_produz_todos_os_artefatos():
    request = CrewRequest(question="Como o LangGraph funciona?", audience="iniciantes")
    resultado = await run_crew(request, settings=_settings())

    assert resultado.brief is not None and resultado.brief.findings
    assert resultado.analysis is not None and resultado.analysis.key_points
    assert resultado.draft is not None and resultado.draft.markdown
    assert resultado.review is not None


async def test_fluxo_completo_passa_pelos_quatro_agentes_na_ordem():
    request = CrewRequest(question="Como o LangGraph funciona?")
    vistos = [nome async for nome, _ in stream_crew(request, settings=_settings())]

    # O ciclo esperado: cada agente uma vez, e o par redator/revisor repetido.
    assert vistos[:4] == list(AGENT_SEQUENCE)
    assert vistos == ["pesquisador", "analista", "redator", "revisor", "redator", "revisor"]


async def test_revisor_reprova_na_primeira_versao_e_aprova_na_segunda():
    request = CrewRequest(question="Qualquer tema", max_revisions=1)
    resultado = await run_crew(request, settings=_settings())

    assert resultado.revisions == 1, "deveria ter havido exatamente uma reescrita"
    assert resultado.review is not None
    assert resultado.review.approved is True


async def test_sem_revisoes_permitidas_o_fluxo_termina_na_primeira_reprovacao():
    """Sem nenhuma reescrita permitida, o time entrega o texto mesmo reprovado."""
    request = CrewRequest(question="Qualquer tema")  # 0 = usa o padrão da configuração
    resultado = await run_crew(request, settings=_settings(max_revisions=0))

    assert resultado.revisions == 0
    assert resultado.review is not None
    assert resultado.review.approved is False
    assert resultado.draft is not None, "o texto deve ser entregue mesmo reprovado"


async def test_pedido_sem_revisoes_usa_o_padrao_da_configuracao():
    """`max_revisions=0` no pedido significa 'use o padrão do .env'."""
    request = CrewRequest(question="Qualquer tema")  # sem informar max_revisions
    resultado = await run_crew(request, settings=_settings(max_revisions=1))

    assert resultado.revisions == 1


async def test_timeline_conta_a_historia_do_que_aconteceu():
    request = CrewRequest(question="Qualquer tema")
    resultado = await run_crew(request, settings=_settings())

    texto = " | ".join(resultado.timeline)
    assert "pesquisador" in texto
    assert "revisor" in texto
    assert len(resultado.timeline) == 6, "uma linha por nó executado"


async def test_audiencia_chega_ate_o_resultado():
    request = CrewRequest(question="Qualquer tema", audience="engenheiros de dados")
    resultado = await run_crew(request, settings=_settings())
    assert resultado.audience == "engenheiros de dados"
