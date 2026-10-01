"""A classe-base de todo agente do time.

Um "agente", aqui, é uma coisa bem mais simples do que parece:

  1. um PAPEL (as instruções de comportamento);
  2. um FORMATO DE SAÍDA (o que ele deve produzir, em Pydantic);
  3. uma TAREFA (como ele lê o estado atual e monta o pedido pro modelo).

Quem faz a mágica de conversar com o LLM é a camada `llm.py`. O agente só
descreve "quem eu sou" e "o que eu preciso agora".
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from ..config import Settings
from ..llm import LLM
from ..state import CrewState
from ..tools.search import SearchTool


@dataclass
class CrewContext:
    """As dependências que todos os agentes compartilham.

    Em vez de cada agente criar sua própria conexão com o modelo, passamos
    este "kit de ferramentas" pronto. Isso deixa os testes fáceis: nos testes
    entregamos um CrewContext com MockLLM e MockSearch.
    """

    settings: Settings
    llm: LLM
    search: SearchTool


class CrewAgent(ABC):
    """Base para os quatro agentes.

    Subclasses precisam definir: `name`, `description`, `output_type` e
    `instructions`. Só o `act()` costuma precisar ser reescrito.
    """

    #: Nome curto, usado em logs, na timeline e como nome do Agent do Pydantic AI.
    name: str = "agente"
    #: Uma frase explicando o papel (aparece no `agent-crew agents`).
    description: str = ""
    #: O modelo Pydantic que este agente devolve.
    output_type: type[BaseModel] = BaseModel

    def __init__(self, context: CrewContext) -> None:
        self.context = context

    # ------------------------------------------------------------------
    #  Instruções (o "system prompt" — as regras do cargo)
    # ------------------------------------------------------------------

    @property
    def instructions(self) -> str:
        """Regras de comportamento. Subclasses devem reescrever isto."""
        raise NotImplementedError

    def system_prompt(self) -> str:
        """Instruções + regras gerais que valem para todo o time."""
        idioma = self.context.settings.language
        return (
            f"{self.instructions.strip()}\n\n"
            "Regras gerais do time:\n"
            f"- Responda sempre em {idioma}.\n"
            "- Seja direto e específico. Nada de enchimento.\n"
            "- Nunca invente fontes, números ou citações.\n"
            "- Se faltar informação, diga o que falta em vez de supor."
        )

    # ------------------------------------------------------------------
    #  O que cada agente faz
    # ------------------------------------------------------------------

    @abstractmethod
    def build_prompt(self, state: CrewState) -> str:
        """Monta o texto que vai para o modelo, a partir do estado atual."""
        raise NotImplementedError

    async def act(self, state: CrewState) -> dict[str, Any]:
        """Executa o agente e devolve só as chaves do estado que ele mudou.

        Subclasses normalmente não precisam reescrever este método: bastam
        `build_prompt` e o método `_apply` (que diz onde guardar o resultado).
        """
        output = await self.context.llm.complete(
            system=self.system_prompt(),
            user=self.build_prompt(state),
            output_type=self.output_type,
            agent_name=self.name,
        )
        update = self._apply(output, state)
        update.setdefault("timeline", []).append(self.log_line(output))
        return update

    @abstractmethod
    def _apply(self, output: Any, state: CrewState) -> dict[str, Any]:
        """Traduz a saída do modelo em mudanças no estado."""
        raise NotImplementedError

    def log_line(self, output: Any) -> str:
        """Uma linha curta para a timeline (aparece no CLI e na API)."""
        return f"{self.name} concluiu a etapa"

    # ------------------------------------------------------------------
    #  Utilidades para as subclasses
    # ------------------------------------------------------------------

    @staticmethod
    def brief_to_text(state: CrewState) -> str:
        """Converte o dossiê de pesquisa em texto legível para o prompt."""
        brief = state.get("brief")
        if not brief:
            return "(nada pesquisado ainda)"

        lines = [f"Pergunta: {brief.question}", "", "Achados:"]
        for finding in brief.findings:
            lines.append(
                f"- {finding.title} (confiança {finding.confidence:.0%}, "
                f"fonte: {finding.source})\n  {finding.summary}"
            )
        if brief.open_questions:
            lines.append("")
            lines.append("Em aberto:")
            lines.extend(f"- {q}" for q in brief.open_questions)
        return "\n".join(lines)

    @staticmethod
    def analysis_to_text(state: CrewState) -> str:
        """Converte a análise em texto legível para o prompt."""
        analysis = state.get("analysis")
        if not analysis:
            return "(nada analisado ainda)"

        lines = ["Pontos-chave:"]
        lines.extend(f"- {p}" for p in analysis.key_points)
        if analysis.risks:
            lines.append("Riscos e lacunas:")
            lines.extend(f"- {r}" for r in analysis.risks)
        lines.append(f"Recomendação: {analysis.recommendation}")
        return "\n".join(lines)

    @staticmethod
    def review_to_text(state: CrewState) -> str:
        """Converte o parecer do revisor em texto legível para o prompt."""
        review = state.get("review")
        if not review or review.approved:
            return "(sem correções pendentes)"

        lines = [f"Nota anterior: {review.score}/10", review.feedback, "Problemas:"]
        lines.extend(f"- {i}" for i in review.issues)
        return "\n".join(lines)
