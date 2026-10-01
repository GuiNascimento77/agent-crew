"""EXEMPLO 5 — A decisão que controla todo o fluxo (e a trava de segurança).

Como rodar:
    python examples/05_a_decisao_do_fluxo.py

O que observar:
    Todo o "comportamento inteligente" do grafo está em UMA função de 8
    linhas: _route_after_review().

    Ela recebe o estado depois do revisor e responde só uma pergunta:
    "para onde vamos agora?"

    Existem três respostas possíveis, e a terceira é a mais importante:
    o freio contra loop infinito.

    Vamos chamar essa função diretamente, com vários estados diferentes.
    É exatamente isso que os testes automatizados fazem — testar a decisão
    sem precisar rodar o time inteiro.
"""

from langgraph.graph import END

from agent_crew.crew import run_crew
from agent_crew.graph import WRITER, _route_after_review
from agent_crew.schemas import CrewRequest, ReviewVerdict

# Pequeno utilitário só para deixar a saída legível.
NOMES = {END: "FIM", WRITER: "redator (reescrever)"}


def testar(descricao: str, estado: dict) -> None:
    destino = _route_after_review(estado)
    print(f"  {descricao}")
    print(
        f"     estado: aprovado={estado['review'].approved}  "
        f"reescritas={estado['revisions']}  limite={estado['max_revisions']}"
    )
    print(f"     decisão: -> {NOMES[destino]}")
    print()


def main() -> None:
    print("=" * 74)
    print("A FUNÇÃO DE ROTEAMENTO, TESTADA COM VÁRIOS ESTADOS")
    print("=" * 74)
    print()

    testar(
        "1) O texto foi aprovado",
        {"review": ReviewVerdict(approved=True, score=9), "revisions": 0, "max_revisions": 3},
    )

    testar(
        "2) Reprovado, e ainda sobram tentativas",
        {"review": ReviewVerdict(approved=False, score=5), "revisions": 0, "max_revisions": 2},
    )

    testar(
        "3) Reprovado no limite de tentativas (a trava de segurança)",
        {"review": ReviewVerdict(approved=False, score=4), "revisions": 2, "max_revisions": 2},
    )

    print(">>> No caso 3 o fluxo TERMINA mesmo sem aprovação.")
    print(">>> Sem essa trava, um revisor exigente + um redator que não melhora")
    print(">>> = programa rodando para sempre, queimando tokens. É um dos erros")
    print(">>> mais comuns em sistemas com agentes, e aqui ele tem teste próprio.")
    print()

    # ------------------------------------------------------------------
    #  Vendo a trava funcionar de verdade
    # ------------------------------------------------------------------
    print("=" * 74)
    print("A TRAVA FUNCIONANDO NO FLUXO COMPLETO")
    print("=" * 74)
    print()

    import asyncio

    from agent_crew.config import Settings

    # Com max_revisions=0, o revisor reprova e NÃO PODE devolver o texto.
    settings = Settings(provider="mock", search_backend="mock", max_revisions=0)
    resultado = asyncio.run(run_crew(CrewRequest(question="Qualquer tema"), settings=settings))

    print(f"  reescritas: {resultado.revisions}  (nenhuma, porque o limite era 0)")
    assert resultado.review is not None
    print(f"  aprovado: {resultado.review.approved}")
    print(f"  passos executados: {len(resultado.timeline)}  (4: um por agente)")
    print()
    print("  Linha do tempo:")
    for linha in resultado.timeline:
        print(f"      • {linha}")
    print()
    print(">>> O texto foi entregue MESMO sem aprovação, com o parecer junto.")
    print(">>> Entregar algo imperfeito e honesto é melhor que travar o programa")
    print(">>> ou fingir que deu tudo certo.")


if __name__ == "__main__":
    main()
