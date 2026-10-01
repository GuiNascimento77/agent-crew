"""EXEMPLO 1 — Rodar o time inteiro (a forma mais simples possível).

Como rodar:
    python examples/01_rodar_o_time.py

O que observar:
    - Nós nunca mencionamos "grafo", "nó" ou "estado". Só chamamos run_crew()
      e recebemos um resultado pronto. Essa simplicidade é de propósito:
      é o padrão "fachada" (facade) em ação.
    - O parâmetro settings é opcional. Aqui passamos um Settings montado à
      mão só para garantir o modo demonstração, sem depender do seu .env.
    - Repare no resultado.revisions: é 1. Isso significa que o revisor
      devolveu o texto uma vez antes de aprovar.
"""

import asyncio

from agent_crew.config import Settings
from agent_crew.crew import run_crew
from agent_crew.schemas import CrewRequest


async def main() -> None:
    # 1) Configuração: provedor "mock" = não chama IA de verdade, não gasta
    #    nada, não precisa de internet nem de chave de API.
    settings = Settings(provider="mock", search_backend="mock", max_revisions=1)

    # 2) O pedido. Pense nisso como o formulário que você entrega ao time.
    request = CrewRequest(
        question="Como funcionam agentes de IA que usam ferramentas?",
        audience="desenvolvedores iniciantes",
    )

    # 3) Rodar. "await" significa: espere essa tarefa assíncrona terminar.
    #    Não precisa entender async a fundo agora — só saiba que chamadas de
    #    rede (como falar com um LLM) são lentas, e o await libera o programa
    #    para fazer outras coisas enquanto espera.
    resultado = await run_crew(request, settings=settings)

    # 4) Mostrar o que voltou. Cada campo é um objeto Pydantic, não texto solto.
    print("=" * 70)
    print("DOSSÊ DE PESQUISA (do pesquisador)")
    print("=" * 70)
    assert resultado.brief is not None
    for achado in resultado.brief.findings:
        print(f"  • {achado.title}")
        print(f"    confiança: {achado.confidence:.0%}  |  fonte: {achado.source}")

    print()
    print("=" * 70)
    print("ANÁLISE (do analista)")
    print("=" * 70)
    assert resultado.analysis is not None
    for ponto in resultado.analysis.key_points:
        print(f"  • {ponto}")
    print(f"  → recomendação: {resultado.analysis.recommendation}")

    print()
    print("=" * 70)
    print("PARECER (do revisor)")
    print("=" * 70)
    assert resultado.review is not None
    print(f"  aprovado: {resultado.review.approved}")
    print(f"  nota: {resultado.review.score}/10")
    print(f"  reescritas: {resultado.revisions}")

    print()
    print("=" * 70)
    print("LINHA DO TEMPO (o que aconteceu, na ordem)")
    print("=" * 70)
    for i, linha in enumerate(resultado.timeline, start=1):
        print(f"  {i}. {linha}")

    print()
    print("=" * 70)
    print("TEXTO FINAL")
    print("=" * 70)
    print(resultado.markdown)


if __name__ == "__main__":
    asyncio.run(main())
