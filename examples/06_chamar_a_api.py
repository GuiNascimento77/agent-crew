"""EXEMPLO 6 — Chamar a API sem subir nenhum servidor.

Como rodar:
    python examples/06_chamar_a_api.py

O que observar:
    Normalmente, testar uma API exige subir um servidor, escolher uma porta,
    e torcer para não dar conflito.

    Aqui usamos um recurso bacana: o ASGITransport do httpx. Ele entrega as
    requisições DIRETO para o app do FastAPI, em memória. Sem porta, sem
    servidor, sem rede.

    É assim que os testes de tests/test_api.py rodam em milissegundos.

    Quando você quiser usar de verdade (com servidor de pé), rode:
        agent-crew serve
    e depois abra http://127.0.0.1:8000/docs no navegador.
"""

import asyncio
import json

import httpx

from agent_crew.api import app


async def main() -> None:
    # O transporte que conversa direto com o app, sem passar pela rede.
    transporte = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transporte, base_url="http://teste") as cliente:
        # ------------------------------------------------------------------
        #  1) GET /health — o serviço está de pé?
        # ------------------------------------------------------------------
        print("=" * 74)
        print("GET /health")
        print("=" * 74)
        resposta = await cliente.get("/health")
        print(f"status HTTP: {resposta.status_code}")
        print(json.dumps(resposta.json(), indent=2, ensure_ascii=False))

        # ------------------------------------------------------------------
        #  2) GET /agents — quem trabalha aqui?
        # ------------------------------------------------------------------
        print()
        print("=" * 74)
        print("GET /agents")
        print("=" * 74)
        resposta = await cliente.get("/agents")
        for agente in resposta.json():
            print(f"  {agente['order']}. {agente['name']:<12} -> {agente['output_schema']}")
            print(f"     {agente['description']}")

        # ------------------------------------------------------------------
        #  3) GET /providers — o que está configurado (sem vazar chaves)
        # ------------------------------------------------------------------
        print()
        print("=" * 74)
        print("GET /providers")
        print("=" * 74)
        resposta = await cliente.get("/providers")
        print(json.dumps(resposta.json(), indent=2, ensure_ascii=False))
        print()
        print(">>> Repare: a API devolve apenas true/false sobre as chaves.")
        print(">>> Ela NUNCA devolve o valor de uma chave de API. Isso é testado.")

        # ------------------------------------------------------------------
        #  4) POST /crew/run — rodar o time
        # ------------------------------------------------------------------
        print()
        print("=" * 74)
        print("POST /crew/run")
        print("=" * 74)
        resposta = await cliente.post(
            "/crew/run",
            json={
                "question": "Como funciona o protocolo MCP?",
                "audience": "desenvolvedores",
                "max_revisions": 1,
            },
        )
        print(f"status HTTP: {resposta.status_code}")
        dados = resposta.json()
        print(f"  reescritas: {dados['revisions']}")
        print(f"  aprovado:   {dados['review']['approved']}")
        print(f"  passos:     {len(dados['timeline'])}")
        print()
        print("  O texto final, em Markdown, começa assim:")
        for linha in dados["draft"]["markdown"].splitlines()[:3]:
            print(f"      {linha}")

        # ------------------------------------------------------------------
        #  5) POST /crew/run com entrada inválida
        # ------------------------------------------------------------------
        print()
        print("=" * 74)
        print("POST /crew/run com entrada inválida (pergunta vazia)")
        print("=" * 74)
        resposta = await cliente.post("/crew/run", json={"question": ""})
        print(f"status HTTP: {resposta.status_code}  (422 = unprocessable entity)")
        print()
        print(">>> O FastAPI validou o JSON antes de executar qualquer coisa.")
        print(">>> Nenhuma chamada de IA foi feita. Erros baratos acontecem cedo.")

        # ------------------------------------------------------------------
        #  6) POST /crew/stream — acompanhar ao vivo (SSE)
        # ------------------------------------------------------------------
        print()
        print("=" * 74)
        print("POST /crew/stream (eventos enviados ao vivo)")
        print("=" * 74)
        async with cliente.stream(
            "POST", "/crew/stream", json={"question": "O que é LangGraph?"}
        ) as resposta:
            corpo = (await resposta.aread()).decode("utf-8")

        for linha in corpo.splitlines():
            if linha.startswith("event: "):
                nome = linha.replace("event: ", "")
                print(f"  evento recebido: {nome}")

        print()
        print(">>> Cada evento chegou assim que aquele agente terminou — não")
        print(">>> no fim de tudo. É isso que permite uma barra de progresso")
        print(">>> de verdade numa interface.")


if __name__ == "__main__":
    asyncio.run(main())
