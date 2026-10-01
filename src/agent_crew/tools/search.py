"""Ferramenta de busca na web usada pelo agente pesquisador.

Esse é o conceito de "tool" (ferramenta) em sistemas de agentes: uma função
comum do seu código que o agente pode acionar para buscar informação fora
do próprio "cérebro" dele.

Duas implementações, mesma interface:

  - MockSearch    -> devolve resultados de exemplo. Grátis, offline, estável.
  - TavilySearch  -> busca de verdade na web, via API da Tavily.

Trocar uma pela outra não exige mudar o agente pesquisador. Isso é o
princípio da inversão de dependência: o agente depende da INTERFACE, não
da implementação concreta.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import httpx

from ..config import Settings


@dataclass(frozen=True)
class SearchHit:
    """Um resultado de busca."""

    title: str
    url: str
    snippet: str

    def as_bullet(self) -> str:
        """Formata o resultado como uma linha de texto para o prompt."""
        return f"- {self.title} ({self.url})\n  {self.snippet}"


@runtime_checkable
class SearchTool(Protocol):
    """Contrato de qualquer ferramenta de busca."""

    name: str

    async def search(self, query: str) -> list[SearchHit]:
        """Busca `query` e devolve uma lista de resultados."""
        ...


class MockSearch:
    """Busca falsa: sempre devolve os mesmos resultados de exemplo."""

    name = "mock"

    def __init__(self, max_results: int = 5) -> None:
        self.max_results = max_results

    async def search(self, query: str) -> list[SearchHit]:
        demo = [
            SearchHit(
                title="[SIMULADO] Resultado de exemplo nº 1",
                url="https://exemplo.com/artigo-1",
                snippet=(
                    "Resultado fictício. Ele existe só para mostrar o formato dos dados "
                    "que a ferramenta de busca devolve para o agente."
                ),
            ),
            SearchHit(
                title="[SIMULADO] Resultado de exemplo nº 2",
                url="https://exemplo.com/artigo-2",
                snippet=f"Trecho de exemplo relacionado ao tema pesquisado: {query[:60]}",
            ),
            SearchHit(
                title="[SIMULADO] Resultado de exemplo nº 3",
                url="https://exemplo.com/artigo-3",
                snippet="Mais um resultado de demonstração, sem nenhum acesso à internet.",
            ),
        ]
        return demo[: self.max_results]


class TavilySearch:
    """Busca real na web, usando a API da Tavily.

    Documentação: https://docs.tavily.com
    Precisa de TAVILY_API_KEY no .env (o plano gratuito já basta para estudar).
    """

    name = "tavily"
    endpoint = "https://api.tavily.com/search"

    def __init__(self, api_key: str, max_results: int = 5, timeout: float = 20.0) -> None:
        self.api_key = api_key
        self.max_results = max_results
        self.timeout = timeout

    async def search(self, query: str) -> list[SearchHit]:
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": self.max_results,
            "search_depth": "basic",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.endpoint, json=payload)
            response.raise_for_status()
            data = response.json()

        return [
            SearchHit(
                title=item.get("title") or "(sem título)",
                url=item.get("url") or "",
                snippet=(item.get("content") or "").strip()[:500],
            )
            for item in data.get("results", [])
        ]


def build_search_tool(settings: Settings) -> SearchTool:
    """Cria a ferramenta de busca conforme a configuração."""
    if settings.search_backend == "tavily":
        if not settings.tavily_api_key:
            raise RuntimeError("TAVILY_API_KEY não configurada.")
        return TavilySearch(
            api_key=settings.tavily_api_key.get_secret_value(),
            max_results=settings.search_max_results,
        )
    return MockSearch(max_results=settings.search_max_results)
