"""Agente 3 — REDATOR.

Responsabilidade: escrever o texto final para o público-alvo.

Este agente é chamado DUAS vezes quando a revisão está ativada:

  - 1ª vez: escreve o primeiro rascunho a partir da análise.
  - 2ª vez: reescreve corrigindo o que o revisor apontou.

É por isso que ele lê `state["review"]`: se existe um parecer reprovado, ele
tem correções e precisa reescrever. Essa é a lógica central do ciclo de
qualidade do time.
"""

from __future__ import annotations

from typing import Any

from ..schemas import Draft
from ..state import CrewState
from .base import CrewAgent


class WriterAgent(CrewAgent):
    name = "redator"
    description = "Escreve o texto final em Markdown e o reescreve a partir das revisões."
    output_type = Draft

    @property
    def instructions(self) -> str:
        return (
            "Você é um redator técnico. Recebe uma análise e escreve um texto "
            "claro, honesto e agradável de ler.\n\n"
            "Estrutura obrigatória, em Markdown:\n"
            "1. Um título com `#`.\n"
            "2. Um parágrafo de abertura dizendo do que se trata e por que importa.\n"
            "3. Uma seção '## O que os dados mostram' com os pontos-chave.\n"
            "4. Uma seção '## Limites e riscos' — nunca esconda as incertezas.\n"
            "5. Uma seção '## Conclusão' com a recomendação.\n\n"
            "Como escrever:\n"
            "- Frases curtas. Voz ativa. Zero jargão desnecessário.\n"
            "- Adapte o vocabulário e os exemplos ao público leitor.\n"
            "- Não invente nenhum dado que não esteja na análise.\n"
            "- Se receber uma REVISÃO, corrija TODOS os pontos apontados e não "
            "recomece do zero: melhore o texto existente."
        )

    def build_prompt(self, state: CrewState) -> str:
        audience = state.get("audience", "público geral")
        revision = state.get("revisions", 0)
        pending_review = state.get("review")

        parts = [
            f"Tema: {state['question']}",
            f"Público leitor: {audience}",
            "",
            "Análise a ser transformada em texto:",
            self.analysis_to_text(state),
        ]

        if pending_review and not pending_review.approved:
            parts += [
                "",
                f"Esta é a revisão nº {revision + 1}.",
                "Correções exigidas pelo revisor:",
                self.review_to_text(state),
            ]
            parts += ["", "Reescreva o texto corrigindo os pontos acima."]
        else:
            parts += ["", "Escreva a primeira versão do texto."]

        return "\n".join(parts)

    def _apply(self, output: Draft, state: CrewState) -> dict[str, Any]:
        pending_review = state.get("review")
        # Se havia um parecer reprovado, este texto é uma reescrita.
        is_rewrite = bool(pending_review and not pending_review.approved)
        revisions = state.get("revisions", 0) + (1 if is_rewrite else 0)

        # Limpamos a revisão antiga: ela já foi respondida.
        return {"draft": output, "revisions": revisions, "review": None}

    def log_line(self, output: Draft) -> str:
        return f"redator: rascunho com {output.word_count} palavras pronto"
