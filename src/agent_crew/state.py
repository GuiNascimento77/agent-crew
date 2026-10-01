"""O "estado compartilhado" do time — o documento que passa de mão em mão.

No LangGraph, cada agente (nó do grafo) recebe este dicionário e devolve
APENAS as chaves que ele mudou. O LangGraph junta tudo no estado global.

Repare no `timeline`: ele usa um "reducer" (`operator.add`). Isso quer dizer
que quando um agente devolve `{"timeline": ["algo"]}`, a lista é SOMADA à
lista que já existia, em vez de substituí-la. É assim que construímos o
histórico do que aconteceu sem cada agente precisar ler o histórico inteiro.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from .schemas import Analysis, Draft, ResearchBrief, ReviewVerdict


class CrewState(TypedDict, total=False):
    """Estado que circula pelo grafo.

    `total=False` significa que nem todas as chaves precisam existir o tempo
    todo — o estado vai sendo preenchido conforme o trabalho avança.
    """

    # --- Entrada -------------------------------------------------------
    question: str
    audience: str
    max_revisions: int

    # --- Controle do ciclo de revisão ----------------------------------
    revisions: int

    # --- Artefatos produzidos por cada agente --------------------------
    brief: ResearchBrief | None
    analysis: Analysis | None
    draft: Draft | None
    review: ReviewVerdict | None

    # --- Histórico legível do que aconteceu ----------------------------
    timeline: Annotated[list[str], operator.add]
