"""EXEMPLO 2 — Ver o estado mudando, agente por agente.

Como rodar:
    python examples/02_ver_o_estado.py

O que observar:
    Este é o exemplo mais importante para entender a arquitetura.

    O "estado" (CrewState) é um dicionário que passa de agente em agente.
    Cada agente LÊ o que precisa e devolve APENAS as chaves que ele mudou.

    Repare que:
      - depois do pesquisador, a chave "brief" aparece;
      - depois do analista, aparece "analysis";
      - o redator aparece DUAS vezes (a segunda é a reescrita);
      - e a "timeline" só cresce — ela nunca é apagada. Isso acontece porque
        ela usa um "reducer" (operator.add): os valores são SOMADOS em vez de
        substituídos.
"""

import asyncio

from agent_crew.config import Settings
from agent_crew.crew import initial_state, stream_crew
from agent_crew.schemas import CrewRequest


def resumir(valor: object, limite: int = 72) -> str:
    """Transforma qualquer valor em uma linha curta e legível."""
    if valor is None:
        return "(vazio)"
    if isinstance(valor, list):
        return f"lista com {len(valor)} item(ns)"
    if hasattr(valor, "model_dump"):  # é um objeto Pydantic
        return f"<{type(valor).__name__}>"
    texto = str(valor).replace("\n", " ")
    return texto[:limite] + ("..." if len(texto) > limite else "")


async def main() -> None:
    settings = Settings(provider="mock", search_backend="mock", max_revisions=1)
    request = CrewRequest(question="O que é o protocolo MCP?", audience="iniciantes")

    # O estado inicial: só a pergunta, o público e os campos vazios.
    estado_anterior = initial_state(request, settings)
    print("ESTADO INICIAL:")
    for chave, valor in estado_anterior.items():
        print(f"    {chave} = {resumir(valor)}")

    # stream_crew devolve (nome_do_agente, estado_acumulado) a cada etapa.
    # Detalhe de Python: geradores assíncronos não aceitam `enumerate`,
    # então contamos o passo na mão.
    numero = 0
    async for agente, estado in stream_crew(request, settings=settings):
        numero += 1
        print()
        print("-" * 74)
        print(f"PASSO {numero}: {agente.upper()}")
        print("-" * 74)

        # Descobrimos o que MUDOU comparando com o snapshot anterior.
        for chave, valor in estado.items():
            if estado_anterior.get(chave) != valor:
                marca = "NOVO " if chave not in estado_anterior else "mudou"
                print(f"    [{marca}] {chave} = {resumir(valor)}")

        estado_anterior = dict(estado)

    print()
    print("=" * 74)
    print("FIM. Observe acima como cada agente contribuiu com uma parte do estado")
    print("e como a timeline foi sendo acumulada, nunca substituída.")
    print("=" * 74)


if __name__ == "__main__":
    asyncio.run(main())
