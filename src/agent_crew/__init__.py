"""agent-crew — time de agentes de IA orquestrado com LangGraph.

Os quatro agentes do time:

    pesquisador -> analista -> redator -> revisor
                                             |
                          (reprovado) --------+---> volta pro redator
                          (aprovado)  -------------> fim

Tudo é configurável por variáveis de ambiente (veja o arquivo .env.example).
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
