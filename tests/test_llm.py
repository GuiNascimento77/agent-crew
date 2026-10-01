"""Testes da camada de LLM (o "cérebro" do time)."""

from __future__ import annotations

from agent_crew.config import Settings
from agent_crew.llm import MockLLM, build_llm
from agent_crew.schemas import Draft, ResearchBrief, ReviewVerdict


async def test_mock_llm_devolve_o_tipo_pedido():
    llm = MockLLM()

    brief = await llm.complete(
        system="regras",
        user="Início do pedido\nmais linhas",
        output_type=ResearchBrief,
        agent_name="pesquisador",
    )
    assert isinstance(brief, ResearchBrief)
    assert brief.findings, "o dossiê simulado deveria trazer achados"

    draft = await llm.complete(
        system="regras", user="Início do pedido", output_type=Draft, agent_name="redator"
    )
    assert isinstance(draft, Draft)
    assert draft.markdown.startswith("#")


async def test_mock_llm_reprova_na_primeira_revisao_e_aprova_depois():
    """É assim que o modo demo exibe o ciclo de reescrita."""
    llm = MockLLM(critical_reviewer=True)
    pedido = {"system": "r", "user": "texto", "agent_name": "revisor"}

    primeira = await llm.complete(output_type=ReviewVerdict, **pedido)
    segunda = await llm.complete(output_type=ReviewVerdict, **pedido)

    assert primeira.approved is False
    assert primeira.issues, "uma reprovação precisa dizer o que está errado"
    assert segunda.approved is True


async def test_mock_llm_sem_criticidade_aprova_de_primeira():
    llm = MockLLM(critical_reviewer=False)
    parecer = await llm.complete(
        system="r", user="texto", output_type=ReviewVerdict, agent_name="revisor"
    )
    assert parecer.approved is True


async def test_mock_llm_ecoa_a_primeira_linha_da_tarefa():
    """O conteúdo simulado carrega o início do prompt, provando que o estado
    chegou até a camada de LLM (e não que ele "pensou" em algo)."""
    llm = MockLLM()
    brief = await llm.complete(
        system="r",
        user="Tema: energia solar no Brasil\nresto do prompt",
        output_type=ResearchBrief,
        agent_name="pesquisador",
    )
    assert brief.question == "energia solar no Brasil"


def test_build_llm_escolhe_o_mock_no_modo_demo():
    settings = Settings(provider="mock", search_backend="mock")
    assert isinstance(build_llm(settings), MockLLM)
