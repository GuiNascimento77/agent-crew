"""Agente 1 — PESQUISADOR.

Responsabilidade: levantar informação confiável sobre a pergunta.

É o único agente do time que usa uma ferramenta externa (a busca na web).
Ele busca, lê os resultados e devolve um dossiê estruturado (`ResearchBrief`).

Repare em dois detalhes de projeto:

  1. As FONTES vêm da ferramenta, não da memória do modelo. Isso reduz
     muito a chance de o modelo "inventar" referências (alucinação).
  2. Cada achado carrega um `confidence`. O analista vai usar isso depois
     para ponderar o que é sólido e o que é frágil.
"""

from __future__ import annotations

from typing import Any

from ..schemas import ResearchBrief
from ..state import CrewState
from ..tools.search import SearchHit
from .base import CrewAgent, CrewContext


class ResearcherAgent(CrewAgent):
    name = "pesquisador"
    description = "Busca informação e monta um dossiê com fontes e nível de confiança."
    output_type = ResearchBrief

    def __init__(self, context: CrewContext) -> None:
        super().__init__(context)
        # Guarda os resultados da busca para montar o prompt e o log.
        self._hits: list[SearchHit] = []

    @property
    def instructions(self) -> str:
        return (
            "Você é um pesquisador sênior. Sua função é levantar o que se sabe "
            "sobre um tema e organizar isso em um dossiê confiável.\n\n"
            "Como trabalhar:\n"
            "- Use os RESULTADOS DA BUSCA fornecidos como base principal.\n"
            "- Acrescente conhecimento próprio apenas quando for sólido e estável.\n"
            "- Ao usar conhecimento próprio, escreva exatamente "
            "'conhecimento do modelo' no campo source.\n"
            "- Nunca invente URLs, artigos ou números. Se não tem a fonte, "
            "diminua o confidence e diga isso.\n"
            "- 3 a 5 achados bem explicados valem mais que 15 superficiais.\n"
            "- Termine com as perguntas que continuam em aberto."
        )

    async def act(self, state: CrewState) -> dict[str, Any]:
        """Primeiro busca na web, depois sintetiza o dossiê."""
        question = state["question"]
        self._hits = await self.context.search.search(question)
        return await super().act(state)

    def build_prompt(self, state: CrewState) -> str:
        question = state["question"]
        audience = state.get("audience", "público geral")

        if self._hits:
            resultados = "\n".join(hit.as_bullet() for hit in self._hits)
        else:
            resultados = (
                "(a busca não retornou resultados — use conhecimento próprio e baixa confiança)"
            )

        return (
            f"Tema a investigar: {question}\n"
            f"Público leitor: {audience}\n\n"
            "Resultados da busca:\n"
            f"{resultados}\n\n"
            "Monte o dossiê de pesquisa sobre o tema acima."
        )

    def _apply(self, output: ResearchBrief, state: CrewState) -> dict[str, Any]:
        return {"brief": output}

    def log_line(self, output: ResearchBrief) -> str:
        return (
            f"pesquisador: {len(output.findings)} achados levantados "
            f"a partir de {len(self._hits)} resultados de busca"
        )
