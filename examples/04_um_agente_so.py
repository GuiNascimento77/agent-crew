"""EXEMPLO 4 — Usar UM agente sozinho, sem o time inteiro.

Como rodar:
    python examples/04_um_agente_so.py

O que observar:
    Um agente não depende do time para funcionar. Ele precisa apenas de um
    CrewContext (configuração + LLM + busca).

    Isso é o que torna o projeto testável: nos testes, chamamos um agente
    isolado e conferimos só o comportamento dele.

    Repare também que passamos settings diferentes para cada agente: um
    respondendo em português e outro em inglês. Prova que a configuração
    realmente chega até a ponta.
"""

import asyncio

from agent_crew.agents import ResearcherAgent
from agent_crew.agents.base import CrewContext
from agent_crew.config import Settings
from agent_crew.llm import MockLLM
from agent_crew.schemas import CrewRequest
from agent_crew.tools.search import MockSearch


async def main() -> None:
    # ------------------------------------------------------------------
    #  1) Um pesquisador isolado, falando inglês
    # ------------------------------------------------------------------
    print("=" * 74)
    print("PESQUISADOR EM INGLÊS")
    print("=" * 74)

    settings_en = Settings(
        provider="mock", search_backend="mock", language="English", max_revisions=1
    )
    contexto_en = CrewContext(settings=settings_en, llm=MockLLM(), search=MockSearch())
    pesquisador = ResearcherAgent(contexto_en)

    # Estado mínimo: o que um pesquisador precisa para trabalhar.
    estado = {"question": "agentic RAG patterns", "audience": "engineers"}

    # act() faz dois passos: busca na ferramenta + chama o LLM.
    mudancas = await pesquisador.act(estado)

    print("\nO que este agente devolveu para o estado:")
    for chave, valor in mudancas.items():
        print(f"    {chave} = {valor}")

    print("\nO system prompt (note as regras gerais no fim):")
    print("-" * 74)
    print(pesquisador.system_prompt())
    print("-" * 74)

    # ------------------------------------------------------------------
    #  2) O mesmo agente, agora em português
    # ------------------------------------------------------------------
    print()
    print("=" * 74)
    print("O MESMO AGENTE, EM PORTUGUÊS")
    print("=" * 74)

    settings_pt = Settings(
        provider="mock", search_backend="mock", language="pt-BR", max_revisions=1
    )
    contexto_pt = CrewContext(settings=settings_pt, llm=MockLLM(), search=MockSearch())
    pesquisador_pt = ResearcherAgent(contexto_pt)

    mudancas = await pesquisador_pt.act(
        {"question": "padrões de RAG com agentes", "audience": "engenheiros"}
    )

    print("\nA saída do agente (a parte estruturada, não a de idioma):")
    brief = mudancas["brief"]
    print(f"    tipo: {type(brief).__name__}")
    print(f"    pergunta registrada: {brief.question}")
    print(f"    achados: {len(brief.findings)}")
    print(f"    perguntas em aberto: {len(brief.open_questions)}")

    # ------------------------------------------------------------------
    #  3) O contrato de dados em ação
    # ------------------------------------------------------------------
    print()
    print("=" * 74)
    print("O CONTRATO DE DADOS")
    print("=" * 74)
    print("\nA saída é um objeto Pydantic, com campos tipados e validados:")
    print(brief.model_dump_json(indent=2))

    print("\n>>> Como é um objeto Python, você pode inspecionar campos direto:")
    for achado in brief.findings:
        print(f"    achado '{achado.title}' tem confiança {achado.confidence}")

    print("\n>>> Nada de 'parsear' texto com expressão regular. É por isso que")
    print(">>> a saída estruturada vale tanto em sistemas de agentes.")

    # Um CrewRequest só para mostrar a validação de entrada funcionando.
    print()
    print("=" * 74)
    print("E A ENTRADA TAMBÉM É VALIDADA")
    print("=" * 74)
    try:
        CrewRequest(question="ok")  # muito curta: min_length=3
        print("não deveria ter passado!")
    except Exception as erro:
        print("Tentamos criar um pedido com pergunta de 2 letras e falhou:")
        print(f"    {type(erro).__name__}")
        print("    (a validação acontece ANTES de chamar qualquer IA — falha rápida)")


if __name__ == "__main__":
    asyncio.run(main())
