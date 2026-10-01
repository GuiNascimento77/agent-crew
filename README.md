<div align="center">

# agent-crew

**Um time de agentes de IA que pesquisa, analisa, escreve e revisa — sozinho.**

Quatro agentes com papéis diferentes trabalham em sequência, com um ciclo de
revisão de qualidade, para transformar uma pergunta em um texto revisado e
com fontes.

[![tests](https://github.com/SEU-USUARIO/agent-crew/actions/workflows/ci.yml/badge.svg)](https://github.com/SEU-USUARIO/agent-crew/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

`LangGraph` · `Pydantic AI` · `FastAPI` · `Typer` · `Rich`

</div>

---

## Sumário

- [O que é isso](#o-que-é-isso)
- [Como funciona](#como-funciona)
- [Rodando em 3 minutos (sem chave de API)](#rodando-em-3-minutos-sem-chave-de-api)
- [Entendendo o código](#entendendo-o-código)
- [Usando um LLM de verdade](#usando-um-llm-de-verdade)
- [Usando a API HTTP](#usando-a-api-http)
- [Comandos do CLI](#comandos-do-cli)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Decisões de projeto (por que assim e não assado)](#decisões-de-projeto)
- [Testes](#testes)
- [Próximos passos](#próximos-passos)
- [Documentação extra](#documentação-extra)

---

## O que é isso?

A maioria dos exemplos de "agentes de IA" é um prompt gigante que pede tudo
de uma vez. Este projeto faz o contrário: divide o trabalho entre **quatro
agentes especializados**, cada um com um papel, um formato de saída e uma
responsabilidade clara.

| # | Agente | O que faz | Devolve |
|---|--------|-----------|---------|
| 1 | **Pesquisador** | Busca informação na web e monta um dossiê com fontes e nível de confiança | `ResearchBrief` |
| 2 | **Analista** | Encontra pontos-chave, riscos e a recomendação central | `Analysis` |
| 3 | **Redator** | Escreve o texto final para o público-alvo (e o reescreve quando preciso) | `Draft` |
| 4 | **Revisor** | Dá nota, aponta problemas e decide: aprovar ou devolver para reescrita | `ReviewVerdict` |

O resultado final é um **texto em Markdown**, acompanhado do dossiê de
pesquisa, da análise, do parecer do revisor e de uma linha do tempo de tudo
o que aconteceu.

> **Diferencial do projeto:** qualquer pessoa clona o repositório e roda em
> segundos, **sem chave de API e sem internet**, usando o provedor `mock`.
> Assim você (ou quem avalia seu portfólio) vê o sistema funcionando antes
> de decidir pagar por um modelo de verdade.

---

## Como funciona

```
                  ┌──────────────────────────────────────────┐
                  │              ESTADO (CrewState)          │
                  │  pergunta · dossiê · análise · texto ·   │
                  │  parecer · contador de revisões          │
                  └──────────────────────────────────────────┘
                                     ▲ │
                     cada agente lê  │ │  e devolve só o que mudou
                                     │ ▼
   ┌──────────────┐   ┌───────────┐   ┌──────────┐   ┌───────────┐
   │ PESQUISADOR  │──▶│ ANALISTA  │──▶│ REDATOR  │──▶│ REVISOR   │
   │ busca + monta│   │ critica + │   │ escreve  │   │ avalia +  │
   │ dossiê       │   │ recomenda │   │ o texto  │   │ decide    │
   └──────────────┘   └───────────┘   └──────────┘   └─────┬─────┘
                                            ▲             │
                                            │  reprovado  │
                                            └─────────────┘
                                                  aprovado ──▶ fim
```

O fluxo é um **grafo de estados** (`src/agent_crew/graph.py`). Cada agente é
um nó; cada seta é uma aresta. A única decisão do sistema é a do revisor:

| Situação | O que acontece |
|----------|----------------|
| Texto aprovado | O fluxo termina |
| Reprovado, ainda há tentativas | Volta para o redator reescrever |
| Reprovado, limite atingido | Termina de qualquer forma, com o parecer anexado |

Esse terceiro caso é a trava contra o **loop infinito** — um dos erros mais
comuns em sistemas com agentes.

👉 Explicação detalhada: [`docs/como-funciona.md`](docs/como-funciona.md)
👉 Decisões técnicas: [`docs/arquitetura.md`](docs/arquitetura.md)

---

## Rodando em 3 minutos (sem chave de API)

Requisitos: **Python 3.11 ou superior** e `git`.

```bash
# 1. Clone o repositório
git clone https://github.com/SEU-USUARIO/agent-crew.git
cd agent-crew

# 2. Crie e ative um ambiente virtual (isola as bibliotecas do projeto)
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Instale o projeto e as dependências de desenvolvimento
pip install -e ".[dev]"

# 4. Rode sem nenhuma configuração (provedor de demonstração)
agent-crew run "Como funciona o protocolo Model Context Protocol (MCP)?"
```

Você vai ver algo assim:

```
╭─ agent-crew ──────────────────────────────────────────────╮
│ Como funciona o protocolo Model Context Protocol (MCP)?   │
│ provider=mock · modelo=gpt-4o-mini · público=público geral │
╰───────────────────────────────────────────────────────────╯

[1/4] Pesquisador
      pesquisador: 2 achados levantados a partir de 3 resultados de busca

[2/4] Analista
      analista: 2 pontos-chave e 1 riscos identificados

[3/4] Redator
      redator: rascunho com 62 palavras pronto

[4/4] Revisor
      revisor: REPROVADO com nota 6/10

[1/4] Redator          ← o revisor devolveu o texto!
      ...

╭─ Parecer do revisor ──────────────────────────────────────╮
│ Nota: 9/10 · Status: APROVADO · Reescritas: 1              │
╰───────────────────────────────────────────────────────────╯
```

O conteúdo em modo `mock` é **claramente marcado como simulado**. Ele serve
para você provar que a orquestração funciona, não para gerar texto de verdade.

---

## Entendendo o código

Este projeto foi escrito para ser **lido**, não só executado. Existem três
caminhos, do mais prático ao mais profundo:

**1. Rodar os exemplos** — seis scripts curtos, cada um isolando uma parte:

```bash
make examples          # roda todos de uma vez
python examples/02_ver_o_estado.py    # veja o estado mudando, agente por agente
python examples/03_ver_os_prompts.py  # veja o texto exato enviado para a IA
```

**2. Ler o tour guiado** — [`docs/tour-do-codigo.md`](docs/tour-do-codigo.md)
diz em que ordem ler cada arquivo e o que observar nele, incluindo os
conceitos de arquitetura que aparecem no caminho (injeção de dependência,
fachada, template method).

**3. Praticar** — [`docs/exercicios.md`](docs/exercicios.md) tem 10
exercícios em ordem crescente: de "mude uma palavra no prompt" até "crie um
agente novo e mude a topologia do grafo".

O caminho de uma execução, para orientar a leitura:

```
agent-crew run "..."
  └─ cli.py :: run()              lê a configuração
     └─ crew.py :: stream_crew()  a fachada
        └─ graph.py :: build_graph() + astream()
           ├─ agents/researcher.py  → busca + LLM
           ├─ agents/analyst.py     → LLM
           ├─ agents/writer.py      → LLM
           ├─ agents/reviewer.py    → LLM
           └─ graph.py :: _route_after_review()   ← a única decisão
                ├── END     → acabou
                └── WRITER  → reescreve
```

O "comportamento adaptativo" do sistema inteiro são **8 linhas** em
`graph.py`. Todo o resto é infraestrutura em volta disso.

---

## Usando um LLM de verdade

1. Copie o arquivo de exemplo de configuração:

```bash
cp .env.example .env
```

2. Abra o `.env` e escolha seu provedor:

```ini
AGENT_CREW_PROVIDER=openai      # ou: anthropic
AGENT_CREW_MODEL_NAME=gpt-4o-mini
OPENAI_API_KEY=sk-...           # sua chave
```

3. Rode:

```bash
agent-crew run "Panorama da energia solar no Brasil em 2026" --audience "investidores"
```

Para saber o que está configurado (sem expor nenhuma chave):

```bash
agent-crew providers
```

### Busca na web de verdade (opcional)

Por padrão o pesquisador usa uma busca simulada. Para buscar de verdade,
crie uma conta gratuita na [Tavily](https://tavily.com), pegue a chave e:

```ini
AGENT_CREW_SEARCH_BACKEND=tavily
TAVILY_API_KEY=tvly-...
```

> **Nota sobre custo:** com `provider=openai` ou `anthropic`, cada execução
> faz de 5 a 6 chamadas ao modelo. Comece com `-r 0` (sem revisão) para
> gastar menos enquanto testa.

---

## Usando a API HTTP

```bash
agent-crew serve
# ou: uvicorn agent_crew.api:app --reload
```

Abra **http://127.0.0.1:8000/docs** — o FastAPI gera uma página interativa
onde você testa tudo clicando, sem escrever código.

| Método | Rota | Para que serve |
|--------|------|----------------|
| `GET` | `/health` | Ver se o serviço está no ar |
| `GET` | `/agents` | Listar os agentes e seus papéis |
| `GET` | `/providers` | Ver o que está configurado (nunca expõe chaves) |
| `POST` | `/crew/run` | Rodar o time e receber o pacote completo |
| `POST` | `/crew/stream` | Rodar o time recebendo o progresso ao vivo (SSE) |

Exemplo com `curl`:

```bash
curl -X POST http://127.0.0.1:8000/crew/run \
  -H 'Content-Type: application/json' \
  -d '{
        "question": "O que é o protocolo MCP?",
        "audience": "desenvolvedores iniciantes",
        "max_revisions": 1
      }'
```

Resposta (resumida):

```json
{
  "question": "O que é o protocolo MCP?",
  "audience": "desenvolvedores iniciantes",
  "revisions": 1,
  "brief":   { "question": "...", "findings": [ { "title": "...", "source": "...", "confidence": 0.6 } ] },
  "analysis":{ "key_points": ["..."], "risks": ["..."], "recommendation": "..." },
  "draft":   { "title": "...", "markdown": "# ...", "word_count": 320 },
  "review":  { "approved": true, "score": 9, "issues": [], "feedback": "..." },
  "timeline":["pesquisador: 2 achados levantados", "..."]
}
```

Acompanhar o progresso em tempo real:

```bash
curl -N -X POST http://127.0.0.1:8000/crew/stream \
  -H 'Content-Type: application/json' \
  -d '{"question":"O que é LangGraph?"}'
```

---

## Comandos do CLI

```bash
agent-crew --help                   # ajuda geral
agent-crew run "sua pergunta"       # roda o time
agent-crew run "tema" -a "médicos"  # define o público-alvo
agent-crew run "tema" -r 2          # permite até 2 reescritas
agent-crew run "tema" -p openai     # usa a OpenAI nesta execução
agent-crew run "tema" -o texto.md   # salva o texto final em arquivo
agent-crew run "tema" --json r.json # salva a execução completa em JSON
agent-crew agents                   # lista os agentes do time
agent-crew providers                # mostra o que está configurado
agent-crew serve                    # sobe a API HTTP
agent-crew version                  # versão do projeto e das bibliotecas
```

Os `--flags` valem **só para aquela execução**; o `.env` continua sendo o
padrão.

---

## Estrutura do projeto

```
agent-crew/
├── src/agent_crew/
│   ├── config.py        # configuração (lê o .env) e validação
│   ├── schemas.py       # os "contratos" de dados (Pydantic) de cada agente
│   ├── state.py         # o estado compartilhado que circula no grafo
│   ├── llm.py           # camada de LLM: Pydantic AI (real) + MockLLM (dublê)
│   ├── agents/          # os quatro agentes
│   │   ├── base.py      #   classe-base comum
│   │   ├── researcher.py#   pesquisador
│   │   ├── analyst.py   #   analista
│   │   ├── writer.py    #   redator
│   │   └── reviewer.py  #   revisor
│   ├── tools/search.py  # ferramenta de busca (mock + Tavily real)
│   ├── graph.py         # monta o grafo (nós, arestas, roteamento)
│   ├── crew.py          # fachada "fácil": run_crew() / stream_crew()
│   ├── cli.py           # interface de linha de comando (Typer + Rich)
│   └── api.py           # API HTTP (FastAPI)
├── tests/               # testes automatizados (rodam 100% offline)
├── examples/            # 6 scripts executáveis para aprender o código
├── docs/                # documentação explicativa
├── .env.example         # modelo de configuração (copie para .env)
└── pyproject.toml       # dependências e metadados do pacote
```

**Regra de ouro da organização:** cada arquivo tem uma responsabilidade só.
Trocar de provedor de LLM não mexe nos agentes. Mudar o fluxo não mexe nos
prompts. É assim que o projeto continua fácil de mexer depois.

---

## Decisões de projeto

Algumas escolhas que valem explicação — porque a parte difícil de um sistema
de agentes não é chamar o modelo, é organizar o código em volta dele.

**1. Saída estruturada em vez de texto solto.**
Cada agente devolve um objeto Pydantic (`ResearchBrief`, `Analysis`,
`Draft`, `ReviewVerdict`). O Pydantic AI obriga o modelo a responder nesse
formato e repete a chamada se vier errado. O agente seguinte recebe dados
limpos, não um bloco de texto para interpretar.

**2. Uma camada de LLM isolada (`llm.py`).**
Aplicando inversão de dependência, o resto do sistema não sabe qual modelo
está atrás. Isso permite trocar de provedor com uma linha do `.env` e testar
tudo offline com o `MockLLM`.

**3. Um arquivo `crew.py` como fachada.**
O CLI e a API não conhecem o grafo, o estado nem os agentes. Eles só chamam
`run_crew()` ou `stream_crew()`. Se amanhã o grafo virar outra coisa, nada
fora dele precisa mudar.

**4. Trava contra loop infinito.**
Um revisor rigoroso e um redator que não melhora = programa travado em
`while True`. O contador `revisions` comparado com `max_revisions` resolve
isso, e está coberto por teste.

**5. Determinismo nos testes.**
Como existe um `MockLLM`, o CI roda os testes em segundos, de graça e sem
resultado "piscando". Testar sistemas com IA é difícil justamente quando
você não consegue isolar o modelo — aqui você consegue.

---

## Testes

```bash
pytest                                   # roda tudo
pytest -v                                # detalhado
pytest --cov=agent_crew                  # com cobertura (pip install pytest-cov)
pytest tests/test_crew.py::test_roteamento_termina_quando_o_limite_de_revisoes_e_atingido -v
```

Os testes são divididos em três grupos:

| Arquivo | O que garante |
|---------|---------------|
| `tests/test_crew.py` | A **orquestração**: ordem dos agentes, ciclo de revisão, freio de segurança |
| `tests/test_api.py`  | A **API**: endpoints, validação de entrada, erros de configuração, streaming |
| `tests/test_llm.py` e `tests/test_tools.py` | A **camada de LLM** e a ferramenta de busca |

Nenhum teste precisa de internet, chave de API ou dinheiro.

---

## Próximos passos

Sugestões de evolução — boas ideias para commits futuros e para conversar em
entrevista:

- [ ] **Observabilidade** — integrar LangSmith ou Langfuse para ver cada chamada com custo e latência
- [ ] **Avaliação automática (evals)** — um conjunto de perguntas com critérios, medindo a qualidade a cada mudança
- [ ] **Memória persistente** — um `checkpointer` do LangGraph para pausar e retomar execuções longas
- [ ] **Aprovação humana** — pausar depois da análise esperando um "ok" antes de escrever (`interrupt`)
- [ ] **Paralelismo** — rodar dois pesquisadores em paralelo sobre ângulos diferentes do tema
- [ ] **Mais ferramentas** — leitura de PDF, consulta a banco, execução de código
- [ ] **Custos** — registrar tokens de entrada/saída por execução (a classe `LLMUsage` já está preparada)
- [ ] **Contêiner** — um `Dockerfile` para subir a API em qualquer lugar

---

## Documentação extra

| Arquivo | Conteúdo |
|---------|----------|
| [`examples/`](examples/) | **Comece aqui se é sua primeira vez.** 6 scripts para ver o sistema funcionando |
| [`docs/tour-do-codigo.md`](docs/tour-do-codigo.md) | Leitura guiada: em que ordem ler cada arquivo e o que observar |
| [`docs/exercicios.md`](docs/exercicios.md) | 10 exercícios práticos, do mais simples ao desafio aberto |
| [`docs/como-funciona.md`](docs/como-funciona.md) | O passo a passo do fluxo, com os prompts explicados |
| [`docs/arquitetura.md`](docs/arquitetura.md) | As decisões técnicas e os padrões usados, em detalhe |
| [`docs/git-e-github.md`](docs/git-e-github.md) | **Guia para quem está começando**: do zero ao repositório publicado |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Como contribuir, rodar e testar |

---

## Licença

MIT — use, estude, modifique e publique à vontade. Veja [LICENSE](LICENSE).
