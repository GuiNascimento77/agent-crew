# Arquitetura e decisões de projeto

Este documento explica **por que** o código está organizado assim. É a parte
que costuma render boas conversas em entrevista técnica.

---

## O desenho geral

```
┌──────────────────────────────────────────────────────────────────┐
│                        INTERFACES                                │
│   cli.py (Typer + Rich)          api.py (FastAPI)                │
└───────────────────────────┬──────────────────────────────────────┘
                            │  ambas usam a mesma porta de entrada
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                  crew.py  —  FACHADA                             │
│            run_crew()  ·  stream_crew()                          │
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                  graph.py  —  ORQUESTRAÇÃO (LangGraph)           │
│      nós: pesquisador · analista · redator · revisor             │
│      aresta condicional: aprovar → fim | reprovar → reescrever   │
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                  agents/  —  OS AGENTES                          │
│   cada um: papel (instruções) + formato de saída (Pydantic)      │
└──────────┬───────────────────────────────────┬───────────────────┘
           ▼                                   ▼
┌────────────────────────┐        ┌───────────────────────────────┐
│  llm.py  — CÉREBRO      │        │  tools/ — FERRAMENTAS          │
│  PydanticAILLM (real)  │        │  MockSearch · TavilySearch     │
│  MockLLM (dublê)       │        └───────────────────────────────┘
└────────────────────────┘
           ▲
           │
┌────────────────────────┐
│  config.py — Settings  │  (.env, validação, valores padrão)
└────────────────────────┘
```

**A regra:** as setas só apontam para baixo. Nada de baixo conhece nada de
cima. O agente não sabe que existe um CLI; o grafo não sabe que existe uma
API; o LLM não sabe que existe um agente.

---

## Decisão 1 — Saída estruturada, não texto solto

**O problema:** se o pesquisador devolve um texto em prosa, o analista
precisa *interpretar* esse texto. Interpretação é onde entram os erros, e
você nunca sabe se errou o modelo ou o parse.

**A solução:** todo agente devolve um objeto Pydantic.

```python
class Finding(BaseModel):
    title: str
    summary: str
    source: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
```

O Pydantic AI recebe esse tipo como `output_type` e **obriga** o modelo a
responder nesse formato. Se a resposta não validar, ele reenvia a chamada
com o erro de validação. `retries=2` dá duas chances.

Os ganhos:

| Sem estrutura | Com estrutura |
|---------------|---------------|
| `"A IA pode substituir... talvez 30%..."` | `Analysis(key_points=[...], risks=[...])` |
| Impossível validar | `confidence` entre 0 e 1, garantido |
| Próximo agente "interpreta" | Próximo agente *acessa* `analysis.risks` |
| Teste frágil | Teste verifica campos |

---

## Decisão 2 — Uma camada de LLM isolada

```python
class LLM(Protocol):
    async def complete(self, *, system, user, output_type, agent_name) -> T: ...
```

O resto do sistema depende **desse contrato**, não do Pydantic AI nem da
OpenAI. Existem duas implementações:

- `PydanticAILLM` — fala com modelos reais.
- `MockLLM` — dublê determinístico.

O que isso compra:

| Situação | Como fica |
|----------|-----------|
| Alguém clona e testa o projeto | Roda com `mock`, sem chave, em segundos |
| Teste automatizado | 30 testes em 0,5s, de graça, sem "piscar" |
| Desenvolver a orquestração | Você mexe no grafo sem pagar chamadas |
| Trocar de fornecedor | Uma linha no `.env` |
| Usar um modelo local (Ollama) | Uma nova implementação, pronto |

> Esse é o **princípio da inversão de dependência**: depender de abstrações,
> não de implementações concretas. É o mesmo raciocínio que faz você usar
> uma tomada padrão em vez de soldar o fio do aparelho na parede.

---

## Decisão 3 — Fachada (`crew.py`) para o mundo externo

CLI e API **não conhecem** o grafo, o estado nem as classes dos agentes:

```python
resultado = await run_crew(request)                    # resultado final
async for agente, estado in stream_crew(request): ...  # passo a passo
```

Consequências práticas:

- Mudar o grafo não quebra nem o CLI nem a API.
- Os testes de cada camada ficam independentes.
- Quem lê `cli.py` entende a interface sem entender IA.

---

## Decisão 4 — Injeção de dependências via contexto

Os agentes não criam suas próprias conexões:

```python
@dataclass
class CrewContext:
    settings: Settings
    llm: LLM
    search: SearchTool
```

Nada de `OpenAI()` espalhado pelo código. Isso torna o teste trivial:

```python
contexto = CrewContext(settings=..., llm=MockLLM(), search=MockSearch())
```

E é o que permite que o teste do `/crew/run` rode em milissegundos.

---

## Decisão 5 — Freio contra loop infinito

**O risco real:** revisor rigoroso + redator limitado = `while True` eterno.

**A solução:** comparar o contador com o limite **dentro da função de
roteamento**, não no prompt. Prompts pedem; código garante.

```python
if revisions >= max_revisions:
    return END
```

Três testes cobrem exatamente isso em `tests/test_crew.py`:

1. Aprovado → termina.
2. Reprovado com tentativas disponíveis → volta ao redator.
3. Reprovado no limite → termina, com o parecer anexado.

> Regra geral em sistemas com agentes: **toda decisão que pode virar loop
> precisa de um limite de guarda**. Confiar no bom senso do modelo não é
> uma estratégia de engenharia.

---

## Decisão 6 — Testar sem o modelo

Testar sistemas com IA é notoriamente difícil: resultado diferente a cada
execução, custo por chamada, latência alta, dependência de rede. Aqui,
nenhum desses quatro problemas existe nos testes.

O que é testado de verdade:

| Camada | Como | O que garante |
|--------|------|---------------|
| Roteamento | Chamada direta à função | A lógica de decisão é correta |
| Orquestração | Grafo completo com mock | Ordem dos agentes e ciclo de revisão |
| API | `httpx.ASGITransport` | Endpoints, validação, erros, SSE |
| Contratos | Instanciação dos modelos | `confidence` fora de 0–1 é rejeitado |
| Configuração | `model_copy` e env vars | Flags do CLI não sujam o global |

O que **não** é testado (e por que): a *qualidade* do texto gerado por um
modelo real. Isso não se testa com asserção simples — se testa com
**evals**, que está na lista de próximos passos.

---

## Decisão 7 — Configuração explícita e que falha cedo

`Settings.validate_for_run()` roda **antes** de qualquer chamada:

```
╭─ Configuração ─────────────────────────────────╮
│ O provedor 'openai' precisa da variável        │
│ OPENAI_API_KEY.                                │
│ Opções:                                        │
│   1) Coloque a chave no arquivo .env           │
│   2) Ou rode usando o provedor de demonstração:│
│      agent-crew run "sua pergunta" -p mock     │
╰────────────────────────────────────────────────╯
```

> **Princípio: falhe cedo, falhe claro.** Descobrir que falta a chave no
> meio do processamento, com metade do trabalho feito, é péssimo. E a
> mensagem sempre oferece uma saída, não só o problema.

Chaves são `SecretStr`, então não aparecem em `print(settings)` nem em log
acidental. E a API `/providers` devolve apenas **booleanos** ("tem chave ou
não"), nunca o valor — isso tem teste próprio.

---

## Decisão 8 — Assíncrono desde o começo

Tudo é `async`/`await`, do agente até o endpoint.

- O FastAPI atende várias requisições enquanto o modelo responde.
- As chamadas de busca podem rodar em paralelo (próximo passo natural).
- O CLI consome o mesmo motor, sem código duplicado.

---

## O que ficou de fora (de propósito)

Um projeto de portfólio bom é aquele que **termina**. Estas escolhas foram
conscientes, não esquecimento:

| Não fizemos | Por quê | Quando faria sentido |
|-------------|---------|----------------------|
| Banco de dados | Nada aqui precisa persistir | Ao guardar histórico de execuções |
| Docker | Adiciona conceito antes de valor | Ao publicar em produção |
| Autenticação na API | Uso local e demonstração | Ao expor na internet |
| Paralelismo entre agentes | O fluxo é sequencial por natureza | Ao ter pesquisadores independentes |
| Evals automáticos | Exige dados de referência | Ao ter 20+ execuções para comparar |
| Retry inteligente | Já existe o retry do Pydantic AI | Ao lidar com limites de taxa |

Saber **o que não fazer agora** é parte do trabalho. Adicione cada item
quando a dor aparecer, não antes.

---

## Resumo das escolhas

| Decisão | Padrão/princípio | Benefício imediato |
|---------|------------------|--------------------|
| Saída estruturada | Contratos com Pydantic | Dados confiáveis entre etapas |
| Camada de LLM isolada | Inversão de dependência | Roda e testa sem chave |
| Fachada `crew.py` | Facade | Interfaces desacopladas |
| Contexto injetado | Dependency injection | Testes em milissegundos |
| Limite de revisões | Guard clause | Sem loop infinito |
| Mock nos testes | Dublê (test double) | Suíte rápida e determinística |
| Falha antecipada | Fail fast | Erros claros, sem desperdício |
| Tudo assíncrono | Async I/O | Escala em requisições |
