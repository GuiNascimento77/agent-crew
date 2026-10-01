"""A fachada do time: a forma mais simples de usar tudo isso.

Se você só quer rodar o time e receber o resultado, use `run_crew`.
Se quiser acompanhar etapa por etapa (como o CLI faz), use `stream_crew`.

Este módulo é a "porta de entrada" do projeto — é ele que o CLI e a API
usam. Ninguém de fora precisa saber que existe um grafo, um estado ou
quatro classes de agente.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from .config import Settings, get_settings
from .graph import AGENT_SEQUENCE, build_graph
from .llm import LLM, build_llm
from .schemas import CrewRequest, CrewResult
from .state import CrewState
from .tools.search import SearchTool, build_search_tool


def initial_state(request: CrewRequest, settings: Settings) -> CrewState:
    """Monta o estado inicial a partir do pedido do usuário."""
    # `max_revisions=0` no pedido significa "use o padrão do .env".
    max_revisions = request.max_revisions if request.max_revisions > 0 else settings.max_revisions

    return CrewState(
        question=request.question,
        audience=request.audience,
        max_revisions=max_revisions,
        revisions=0,
        brief=None,
        analysis=None,
        draft=None,
        review=None,
        timeline=[],
    )


async def stream_crew(
    request: CrewRequest,
    *,
    settings: Settings | None = None,
    llm: LLM | None = None,
    search: SearchTool | None = None,
) -> AsyncIterator[tuple[str, CrewState]]:
    """Roda o time e vai entregando o estado a cada etapa concluída.

    Cada item produzido é um par `(nome_do_agente, estado_completo_até_aqui)`.
    É isso que permite ao CLI mostrar o progresso agente por agente, e à API
    transmitir o avanço em tempo real (SSE).

    Os parâmetros `settings`, `llm` e `search` existem para os testes
    conseguirem injetar dublês. Em uso normal, não passe nada.
    """
    # Import aqui dentro para evitar import circular (base -> context -> ...).
    from .agents.base import CrewContext

    settings = settings or get_settings()
    settings.validate_for_run()

    context = CrewContext(
        settings=settings,
        llm=llm or build_llm(settings),
        search=search or build_search_tool(settings),
    )

    graph = build_graph(context)
    state: CrewState = initial_state(request, settings)

    # stream_mode="updates" devolve, a cada passo, só o que AQUELE nó mudou.
    # Aqui nós mesmos somamos cada mudança para manter um estado acumulado.
    async for chunk in graph.astream(state, stream_mode="updates"):
        for agent_name, update in chunk.items():
            if agent_name not in AGENT_SEQUENCE:
                continue
            state = _merge(state, update)
            yield agent_name, state


def _merge(state: CrewState, update: dict[str, Any]) -> CrewState:
    """Soma uma atualização parcial ao estado acumulado (client-side).

    Precisa respeitar o reducer da `timeline` (o mesmo `operator.add` que o
    LangGraph usa), senão o histórico seria sobrescrito a cada passo.
    """
    merged: dict[str, Any] = dict(state)
    for key, value in update.items():
        if key == "timeline":
            merged["timeline"] = list(merged.get("timeline") or []) + list(value)
        else:
            merged[key] = value
    return merged  # type: ignore[return-value]


async def run_crew(
    request: CrewRequest,
    *,
    settings: Settings | None = None,
    llm: LLM | None = None,
    search: SearchTool | None = None,
) -> CrewResult:
    """Roda o time inteiro e devolve o resultado final consolidado."""
    from .agents.base import CrewContext

    settings = settings or get_settings()
    settings.validate_for_run()

    context = CrewContext(
        settings=settings,
        llm=llm or build_llm(settings),
        search=search or build_search_tool(settings),
    )

    graph = build_graph(context)
    final_state: dict[str, Any] = await graph.ainvoke(initial_state(request, settings))

    return result_from_state(final_state, request)


def result_from_state(state: dict[str, Any], request: CrewRequest) -> CrewResult:
    """Empacota o estado final no objeto de resposta que o CLI/API devolvem."""
    return CrewResult(
        question=state.get("question", request.question),
        audience=state.get("audience", request.audience),
        revisions=state.get("revisions", 0),
        brief=state.get("brief"),
        analysis=state.get("analysis"),
        draft=state.get("draft"),
        review=state.get("review"),
        timeline=state.get("timeline", []),
    )
