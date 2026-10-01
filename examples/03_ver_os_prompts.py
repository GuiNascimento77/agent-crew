"""EXEMPLO 3 — Ver exatamente o que é enviado para a IA (os prompts).

Como rodar:
    python examples/03_ver_os_prompts.py

O que observar:
    Aqui está o "segredo" de um sistema de agentes: no fim das contas, cada
    agente é apenas um TEXTO enviado para um modelo, mais um formato de
    resposta exigido.

    Cada agente monta dois textos:

      1. SYSTEM PROMPT ("quem eu sou") — as regras de comportamento.
         Não muda entre execuções. Vem da propriedade `instructions`.

      2. USER PROMPT ("o que fazer agora") — a tarefa concreta, montada a
         partir do estado atual. Muda a cada execução.

    Se um agente está se comportando mal, é AQUI que você mexe. Não existe
    mágica escondida em outro lugar.
"""

import asyncio

from agent_crew.agents import AnalystAgent, ResearcherAgent, ReviewerAgent, WriterAgent
from agent_crew.agents.base import CrewContext
from agent_crew.config import Settings
from agent_crew.llm import MockLLM
from agent_crew.schemas import Analysis, Draft, ReviewVerdict
from agent_crew.tools.search import MockSearch


def caixa(titulo: str, texto: str) -> None:
    """Imprime um texto delimitado, para ficar fácil de ler."""
    print()
    print("=" * 78)
    print(titulo)
    print("=" * 78)
    print(texto)
    print("=" * 78)


async def main() -> None:
    settings = Settings(provider="mock", search_backend="mock", language="pt-BR")

    # O contexto é o "kit de ferramentas" que os agentes recebem.
    # Nos testes usamos dublês; em produção, o LLM e a busca de verdade.
    contexto = CrewContext(settings=settings, llm=MockLLM(), search=MockSearch())

    pesquisador = ResearcherAgent(contexto)
    analista = AnalystAgent(contexto)
    redator = WriterAgent(contexto)
    revisor = ReviewerAgent(contexto)

    # ------------------------------------------------------------------
    #  PARTE 1 — O system prompt (quem cada um é)
    # ------------------------------------------------------------------
    caixa("SYSTEM PROMPT DO PESQUISADOR", pesquisador.system_prompt())

    print()
    print(">>> Repare: as regras gerais do time são adicionadas automaticamente")
    print(">>> pela classe-base CrewAgent, em agents/base.py. Cada agente só")
    print(">>> escreve as instruções específicas do seu papel.")
    print()
    print(">>> E aqui está o do analista, para comparar — note que as regras")
    print(">>> gerais no fim são IDÊNTICAS, só o papel dele muda:")

    caixa("SYSTEM PROMPT DO ANALISTA", analista.system_prompt())

    # ------------------------------------------------------------------
    #  PARTE 2 — O user prompt muda conforme o estado
    # ------------------------------------------------------------------
    # Simulamos um estado em que já houve pesquisa e análise.
    estado = {
        "question": "Vale a pena usar agentes de IA no meu produto?",
        "audience": "fundadores de startups",
        "max_revisions": 1,
        "revisions": 0,
        "brief": None,
        "analysis": Analysis(
            key_points=["Ponto de exemplo 1", "Ponto de exemplo 2"],
            risks=["Risco de exemplo: custo por execução"],
            recommendation="Comece com um caso de uso bem delimitado.",
        ),
        "draft": Draft(
            title="Rascunho de exemplo",
            markdown="# Rascunho\ntexto de exemplo para o revisor avaliar.",
            word_count=7,
        ),
        "review": ReviewVerdict(
            approved=False,
            score=6,
            issues=["Falta uma seção com exemplos práticos."],
            feedback="Acrescente pelo menos um exemplo concreto.",
        ),
        "timeline": [],
    }

    # O redator monta um prompt diferente porque existe uma revisão pendente.
    caixa("USER PROMPT DO REDATOR (com revisão pendente)", redator.build_prompt(estado))

    print()
    print(">>> Compare com um redator sem revisão pendente. Faça o teste:")
    print(">>> apague o 'review' do dicionário acima e rode de novo.")
    print(">>> É assim que o MESMO agente escreve o primeiro rascunho e a")
    print(">>> reescrita: mudando o que entra no prompt, não o código.")

    # ------------------------------------------------------------------
    #  PARTE 3 — O revisor avalia o texto
    # ------------------------------------------------------------------
    caixa("USER PROMPT DO REVISOR", revisor.build_prompt(estado))

    # ------------------------------------------------------------------
    #  PARTE 4 — A pesquisa usa uma FERRAMENTA antes de chamar o modelo
    # ------------------------------------------------------------------
    print()
    print(">>> Agora o pesquisador: ele é especial porque usa uma ferramenta")
    print(">>> externa (a busca) ANTES de falar com o modelo.")

    resultado_da_busca = await contexto.search.search("agentes de IA em produção")
    print(f">>> A busca devolveu {len(resultado_da_busca)} resultado(s):")
    for hit in resultado_da_busca:
        print(f"      - {hit.title}  ({hit.url})")

    # Damos os resultados ao pesquisador, como o act() faria de verdade.
    pesquisador._hits = resultado_da_busca
    caixa(
        "USER PROMPT DO PESQUISADOR (com os resultados da busca)",
        pesquisador.build_prompt({**estado, "question": "agentes de IA em produção"}),
    )

    print()
    print(">>> Conclusão: um agente = instruções + tarefa montada do estado.")
    print(">>> O modelo é só o motor no fim dessa linha. Todo o resto é código")
    print(">>> que você controla, lê e testa.")


if __name__ == "__main__":
    asyncio.run(main())
