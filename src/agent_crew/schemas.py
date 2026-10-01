"""Os "contratos" de dados do time.

Cada agente devolve um objeto Pydantic bem definido em vez de texto solto.
Isso é o pulo do gato de um sistema multiagente confiável:

  - O Pydantic AI obriga o modelo a responder no formato exato.
  - O próximo agente recebe dados estruturados, não um monte de texto.
  - Se o modelo errar o formato, o Pydantic AI pede a correção sozinho.

Pense nesses modelos como os formulários que cada funcionário preenche.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# =====================================================================
#  1) O que o PESQUISADOR devolve
# =====================================================================


class Finding(BaseModel):
    """Um único achado de pesquisa."""

    title: str = Field(description="Título curto e direto do achado")
    summary: str = Field(description="2 a 4 frases explicando o achado")
    source: str = Field(description="De onde veio: URL, documento ou 'conhecimento do modelo'")
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="O quanto essa informação é confiável (0 a 1)"
    )


class ResearchBrief(BaseModel):
    """Dossiê de pesquisa entregue ao analista."""

    question: str = Field(description="A pergunta original, reformulada com clareza")
    findings: list[Finding] = Field(default_factory=list, description="Os achados encontrados")
    open_questions: list[str] = Field(
        default_factory=list, description="O que ficou em aberto / ainda precisa ser investigado"
    )


# =====================================================================
#  2) O que o ANALISTA devolve
# =====================================================================


class Analysis(BaseModel):
    """Análise crítica do dossiê de pesquisa."""

    key_points: list[str] = Field(default_factory=list, description="Os pontos-chave, em bullets")
    risks: list[str] = Field(
        default_factory=list, description="Riscos, lacunas e contra-argumentos"
    )
    recommendation: str = Field(description="Recomendação central em uma frase")
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confiança na análise (0 a 1)"
    )


# =====================================================================
#  3) O que o REDATOR devolve
# =====================================================================


class Draft(BaseModel):
    """Texto entregável, já pronto para o leitor final."""

    title: str = Field(description="Título do texto")
    markdown: str = Field(description="O texto completo, formatado em Markdown")
    word_count: int = Field(default=0, ge=0, description="Quantidade aproximada de palavras")


# =====================================================================
#  4) O que o REVISOR devolve
# =====================================================================


class ReviewVerdict(BaseModel):
    """Parecer do revisor — é ele quem decide se o fluxo continua ou para."""

    approved: bool = Field(description="True se o texto está pronto para publicar")
    score: int = Field(default=0, ge=0, le=10, description="Nota de 0 a 10")
    issues: list[str] = Field(default_factory=list, description="Problemas encontrados")
    feedback: str = Field(default="", description="Orientação concreta para o redator melhorar")


# =====================================================================
#  Entrada e saída do fluxo inteiro
# =====================================================================


class CrewRequest(BaseModel):
    """O que o cliente (API ou CLI) pede."""

    question: str = Field(min_length=3, description="O que o time deve investigar e produzir")
    audience: str = Field(default="público geral", description="Para quem o texto final é escrito")
    max_revisions: int = Field(
        default=0,
        ge=0,
        le=5,
        description="Máximo de devoluções do revisor. 0 = usar o padrão do .env.",
    )


class CrewResult(BaseModel):
    """O resultado final, com todas as etapas visíveis."""

    question: str
    audience: str
    revisions: int = Field(default=0, description="Quantas vezes o texto voltou para reescrita")
    brief: ResearchBrief | None = None
    analysis: Analysis | None = None
    draft: Draft | None = None
    review: ReviewVerdict | None = None
    timeline: list[str] = Field(default_factory=list, description="Linha do tempo do que aconteceu")

    @property
    def markdown(self) -> str:
        """O texto final em Markdown (usado pelo CLI e pela API)."""
        return self.draft.markdown if self.draft else ""


# Nome do agente, para usar em logs e na linha do tempo.
AgentName = Literal["pesquisador", "analista", "redator", "revisor"]
