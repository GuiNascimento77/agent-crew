"""API HTTP do time de agentes (FastAPI).

Rodar:

    agent-crew serve
    # ou
    uvicorn agent_crew.api:app --reload

Depois abra http://127.0.0.1:8000/docs — o FastAPI gera uma página de
documentação interativa sozinho, onde você pode testar cada endpoint
clicando. Isso já é meio portfólio por si só.

Endpoints:

    GET  /health          -> o serviço está de pé?
    GET  /agents          -> quem são os agentes do time
    GET  /providers       -> provedores disponíveis e o que está configurado
    POST /crew/run        -> roda o time e devolve o resultado completo
    POST /crew/stream     -> roda o time transmitindo o progresso ao vivo (SSE)
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import __version__
from .agents.base import CrewContext
from .config import ProviderName, get_settings
from .crew import result_from_state, run_crew, stream_crew
from .graph import AGENT_SEQUENCE, build_agents
from .llm import MockLLM
from .schemas import CrewRequest, CrewResult
from .tools.search import MockSearch

app = FastAPI(
    title="agent-crew API",
    version=__version__,
    summary="Time de agentes de IA: pesquisa, análise, redação e revisão.",
    description=(
        "Um time de quatro agentes que se organiza para investigar um tema e "
        "entregar um texto revisado.\n\n"
        "Orquestração feita com **LangGraph**; saídas estruturadas garantidas "
        "pelo **Pydantic AI**."
    ),
)


# =====================================================================
#  Modelos de resposta só da API (os de entrada vêm de schemas.py)
# =====================================================================


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    provider: ProviderName
    model_name: str


class AgentInfo(BaseModel):
    order: int
    name: str
    description: str
    output_schema: str


class ProvidersResponse(BaseModel):
    current: ProviderName
    search_backend: str
    model_name: str
    temperature: float
    max_revisions: int
    available: dict[str, bool] = Field(
        description="Quais provedores estão prontos para uso (chave presente ou não exigida)."
    )


# =====================================================================
#  Endpoints de leitura
# =====================================================================


@app.get("/health", response_model=HealthResponse, tags=["sistema"])
async def health() -> HealthResponse:
    """Verificação simples de que o serviço está no ar."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=__version__,
        provider=settings.provider,
        model_name=settings.model_name,
    )


@app.get("/agents", response_model=list[AgentInfo], tags=["sistema"])
async def list_agents() -> list[AgentInfo]:
    """Lista os agentes, na ordem em que trabalham."""
    settings = get_settings()
    context = CrewContext(settings=settings, llm=MockLLM(), search=MockSearch())
    crew = build_agents(context)
    return [
        AgentInfo(
            order=index,
            name=name,
            description=crew[name].description,
            output_schema=crew[name].output_type.__name__,
        )
        for index, name in enumerate(AGENT_SEQUENCE, start=1)
    ]


@app.get("/providers", response_model=ProvidersResponse, tags=["sistema"])
async def list_providers() -> ProvidersResponse:
    """Diz o que está configurado e o que falta, sem expor nenhuma chave."""
    settings = get_settings()
    return ProvidersResponse(
        current=settings.provider,
        search_backend=settings.search_backend,
        model_name=settings.model_name,
        temperature=settings.temperature,
        max_revisions=settings.max_revisions,
        available={
            "mock": True,
            "openai": settings.openai_api_key is not None,
            "anthropic": settings.anthropic_api_key is not None,
            "tavily_search": settings.tavily_api_key is not None,
        },
    )


# =====================================================================
#  Rodar o time
# =====================================================================


@app.post("/crew/run", response_model=CrewResult, tags=["crew"])
async def crew_run(request: CrewRequest) -> CrewResult:
    """Roda o time inteiro e devolve tudo: dossiê, análise, texto e parecer.

    Este é o endpoint principal. Ele só responde quando o fluxo termina.

    Exemplo de corpo da requisição:

    ```json
    {
      "question": "Como funciona o protocolo Model Context Protocol (MCP)?",
      "audience": "desenvolvedores iniciantes",
      "max_revisions": 1
    }
    ```
    """
    try:
        return await run_crew(request)
    except RuntimeError as error:
        # Erro de configuração (chave faltando) é culpa do cliente: 400.
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/crew/stream", tags=["crew"])
async def crew_stream(request: CrewRequest) -> StreamingResponse:
    """Roda o time transmitindo cada etapa assim que ela termina (SSE).

    Útil para interfaces que mostram o progresso em tempo real. Cada evento
    é uma linha no formato `event: <nome>\\ndata: <json>\\n\\n`.

    Teste rápido no terminal:

    ```bash
    curl -N -X POST http://127.0.0.1:8000/crew/stream \\
      -H 'Content-Type: application/json' \\
      -d '{"question":"O que é LangGraph?"}'
    ```
    """

    async def event_stream() -> AsyncIterator[str]:
        state: dict = {}
        try:
            async for agent_name, snapshot in stream_crew(request):
                state = dict(snapshot)
                payload = {
                    "agent": agent_name,
                    "timeline": state.get("timeline", []),
                }
                yield f"event: {agent_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except RuntimeError as error:
            yield f"event: error\ndata: {json.dumps({'detail': str(error)})}\n\n"
            return

        # O último evento traz o resultado consolidado, igual ao de /crew/run.
        final = result_from_state(state, request)
        dados = json.dumps(final.model_dump(mode="json"), ensure_ascii=False)
        yield f"event: done\ndata: {dados}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# =====================================================================
#  Execução direta: `python -m agent_crew.api`
# =====================================================================

if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
