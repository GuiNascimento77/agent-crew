"""A orquestração: o grafo que decide quem trabalha e em que ordem.

Aqui está o coração do projeto. Usamos o LangGraph, que modela o fluxo como
um GRAFO:

    nós    = os agentes (e o trabalho que cada um faz)
    arestas = "depois de X, vá para Y"
    estado  = o documento compartilhado que passa entre eles

O nosso grafo:

    [início] -> pesquisador -> analista -> redator -> revisor
                                                       |
                        aprovado -> [fim]               |
                        reprovado e ainda há tentativas -> volta ao redator

Se você desenhar isso num papel, vai ver por que um grafo é melhor que uma
sequência de `if`s: o "volta para o redator" é uma aresta comum, e a condição
é uma função pequena e testável.

Por que não fazer um único prompt gigante pedindo tudo de uma vez?
Porque assim cada etapa tem um foco, um formato de saída próprio, e você
consegue ver exatamente onde o time acertou ou errou.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .agents import AnalystAgent, ResearcherAgent, ReviewerAgent, WriterAgent
from .agents.base import CrewAgent, CrewContext
from .state import CrewState

# Nome dos nós. Usar constantes evita erro de digitação em strings soltas.
RESEARCHER = "pesquisador"
ANALYST = "analista"
WRITER = "redator"
REVIEWER = "revisor"

#: Ordem em que os agentes aparecem (usada na documentação e no CLI).
AGENT_SEQUENCE: tuple[str, ...] = (RESEARCHER, ANALYST, WRITER, REVIEWER)


def build_agents(context: CrewContext) -> dict[str, CrewAgent]:
    """Cria uma instância de cada agente, já com o contexto injetado."""
    agents: list[CrewAgent] = [
        ResearcherAgent(context),
        AnalystAgent(context),
        WriterAgent(context),
        ReviewerAgent(context),
    ]
    return {agent.name: agent for agent in agents}


def _route_after_review(state: CrewState) -> str:
    """Decide o próximo passo depois do revisor. É a única decisão do fluxo.

    Três casos possíveis:
      1. O texto foi aprovado            -> termina.
      2. Não foi aprovado, mas já usamos
         todas as revisões permitidas    -> termina mesmo assim (evita loop infinito).
      3. Não foi aprovado e ainda há
         revisões disponíveis            -> volta para o redator.
    """
    review = state.get("review")
    revisions = state.get("revisions", 0)
    max_revisions = state.get("max_revisions", 0)

    if review is not None and review.approved:
        return END

    if revisions >= max_revisions:
        return END

    return WRITER


def build_graph(context: CrewContext) -> CompiledStateGraph:
    """Monta e compila o grafo do time.

    Devolve um grafo pronto para rodar com `.ainvoke(state)` (uma vez, com o
    resultado final) ou `.astream(state)` (acompanhando etapa por etapa).
    """
    agents = build_agents(context)

    # Cada nó é só "chame o agente e devolva o que ele mudou no estado".
    async def run_agent(state: CrewState, *, agent_name: str) -> dict[str, Any]:
        return await agents[agent_name].act(state)

    def make_node(agent_name: str):
        async def node(state: CrewState) -> dict[str, Any]:
            return await run_agent(state, agent_name=agent_name)

        node.__name__ = f"no_{agent_name}"
        return node

    graph = StateGraph(CrewState)

    for agent_name in AGENT_SEQUENCE:
        graph.add_node(agent_name, make_node(agent_name))

    # Fluxo principal: uma linha reta do começo até o revisor.
    graph.add_edge(START, RESEARCHER)
    graph.add_edge(RESEARCHER, ANALYST)
    graph.add_edge(ANALYST, WRITER)
    graph.add_edge(WRITER, REVIEWER)

    # A única bifurcação: o revisor decide se termina ou devolve ao redator.
    graph.add_conditional_edges(
        REVIEWER,
        _route_after_review,
        {WRITER: WRITER, END: END},
    )

    return graph.compile()
