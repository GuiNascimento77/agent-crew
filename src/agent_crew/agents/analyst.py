"""Agente 2 — ANALISTA.

Responsabilidade: transformar o dossiê em entendimento.

Ele não busca nada e não escreve o texto final. Ele lê o dossiê do
pesquisador, encontra os pontos que realmente importam, aponta riscos e
lacunas, e entrega uma recomendação.

Esse é o valor de separar papéis: o pesquisador é cobrado por AMPLITUDE
(trazer bastante material), e o analista é cobrado por PROFUNDIDADE
(encontrar o que é essencial e o que não se sustenta). Um único agente
fazendo as duas coisas tende a fazer as duas mal.
"""

from __future__ import annotations

from typing import Any

from ..schemas import Analysis
from ..state import CrewState
from .base import CrewAgent


class AnalystAgent(CrewAgent):
    name = "analista"
    description = "Encontra os pontos-chave, riscos e a recomendação central."
    output_type = Analysis

    @property
    def instructions(self) -> str:
        return (
            "Você é um analista crítico. Recebe um dossiê de pesquisa e precisa "
            "extrair o que realmente importa.\n\n"
            "Como trabalhar:\n"
            "- Dê mais peso aos achados com confidence alta.\n"
            "- Aponte explicitamente o que é FRACO no dossiê: fonte duvidosa, "
            "dado desatualizado, conclusão apressada, contradição entre achados.\n"
            "- Se um achado não sustenta uma conclusão, diga isso.\n"
            "- De 3 a 6 pontos-chave, objetivos e verificáveis.\n"
            "- A recomendação deve caber em UMA frase acionável.\n"
            "- Seu `confidence` é sobre a SUA análise, não sobre o tema."
        )

    def build_prompt(self, state: CrewState) -> str:
        return (
            f"Tema: {state['question']}\n"
            f"Público leitor: {state.get('audience', 'público geral')}\n\n"
            "Dossiê de pesquisa:\n"
            f"{self.brief_to_text(state)}\n\n"
            "Analise o dossiê acima e produza a análise."
        )

    def _apply(self, output: Analysis, state: CrewState) -> dict[str, Any]:
        return {"analysis": output}

    def log_line(self, output: Analysis) -> str:
        return (
            f"analista: {len(output.key_points)} pontos-chave e "
            f"{len(output.risks)} riscos identificados"
        )
