"""Agente 4 — REVISOR (o porteiro do time).

Responsabilidade: julgar se o texto está pronto para publicar.

Ele é o agente mais poderoso do fluxo, porque a decisão dele muda o
CAMINHO do grafo:

    approved = True   ->  o fluxo termina
    approved = False  ->  o texto volta para o redator

Duas salvaguardas importantes estão no grafo (não aqui):

  1. O revisor nunca pode devolver o texto mais vezes que `max_revisions`.
     Sem isso, um revisor muito exigente criaria um loop infinito.
  2. Se o limite é atingido e o texto ainda não foi aprovado, o fluxo
     termina de qualquer forma — com o parecer anexado ao resultado. É
     melhor entregar um texto imperfeito e honesto do que travar.

Ser severo é bom, mas ser IMPOSSÍVEL de agradar é um bug.
"""

from __future__ import annotations

from typing import Any

from ..schemas import ReviewVerdict
from ..state import CrewState
from .base import CrewAgent


class ReviewerAgent(CrewAgent):
    name = "revisor"
    description = "Avalia o texto, dá nota e decide se aprova ou devolve para reescrita."
    output_type = ReviewVerdict

    @property
    def instructions(self) -> str:
        return (
            "Você é um revisor rigoroso e justo. Avalia textos antes da publicação.\n\n"
            "Critérios de avaliação (todos têm o mesmo peso):\n"
            "1. CLAREZA: dá para entender na primeira leitura?\n"
            "2. FIDELIDADE: o texto só afirma o que está na análise? Nada inventado?\n"
            "3. ESTRUTURA: tem título, abertura, dados, limites e conclusão?\n"
            "4. HONESTIDADE: as incertezas estão explicitadas?\n"
            "5. ADEQUAÇÃO: a linguagem serve ao público leitor?\n\n"
            "Como decidir:\n"
            "- `approved` = True somente se a nota for 8 ou mais E não houver "
            "problema de fidelidade.\n"
            "- Informação inventada é reprovação imediata, sem discussão.\n"
            "- Se reprovar, o `feedback` precisa ser CONCRETO: diga o que "
            "trocar, em qual seção, e por quê. 'Está ruim' não ajuda ninguém.\n"
            "- Não reprove por preferência pessoal de estilo."
        )

    def build_prompt(self, state: CrewState) -> str:
        draft = state.get("draft")
        texto = draft.markdown if draft else "(nenhum texto recebido)"

        return (
            f"Tema original: {state['question']}\n"
            f"Público leitor: {state.get('audience', 'público geral')}\n"
            f"Esta é a versão nº {state.get('revisions', 0) + 1}.\n\n"
            "Análise de referência (a fonte da verdade):\n"
            f"{self.analysis_to_text(state)}\n\n"
            "Texto a ser avaliado:\n"
            "----- INÍCIO DO TEXTO -----\n"
            f"{texto}\n"
            "----- FIM DO TEXTO -----\n\n"
            "Avalie o texto acima."
        )

    def _apply(self, output: ReviewVerdict, state: CrewState) -> dict[str, Any]:
        return {"review": output}

    def log_line(self, output: ReviewVerdict) -> str:
        veredito = "APROVADO" if output.approved else "REPROVADO"
        return f"revisor: {veredito} com nota {output.score}/10"
