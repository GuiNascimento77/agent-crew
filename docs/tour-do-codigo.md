# Tour pelo código: por onde ler e o que observar

O projeto tem ~1.200 linhas de código. Isso é **pouco** — cabe em uma tarde
de leitura calma. Este guia diz em que ordem ler e o que reparar em cada
arquivo.

> **Antes de começar:** rode os exemplos. Ler código é metade do trabalho;
> ver acontecer é a outra metade.
>
> ```bash
> python examples/01_rodar_o_time.py
> python examples/02_ver_o_estado.py
> ```
> Se eles rodam, seu ambiente está pronto.

---

## O caminho de um clique

Quando você digita `agent-crew run "minha pergunta"`, isto acontece:

```
1. terminal
   └─▶ cli.py :: run()                    lê os --flags e monta a configuração
        └─▶ cli.py :: _apply_overrides()  aplica os flags sobre o .env
        └─▶ cli.py :: _run_and_report()   cria o CrewRequest e mostra o progresso
             └─▶ crew.py :: stream_crew()   ← a fachada
                  └─▶ graph.py :: build_graph()   monta nós e arestas
                  └─▶ graph.astream()             roda os nós, um a um
                       ├─▶ agents/researcher.act()  → llm.complete() + busca
                       ├─▶ agents/analyst.act()     → llm.complete()
                       ├─▶ agents/writer.act()      → llm.complete()
                       ├─▶ agents/reviewer.act()    → llm.complete()
                       └─▶ graph.py :: _route_after_review()  ← a decisão
                            ├── END  → acabou
                            └── WRITER → volta ao redator (reescreve)
```

Guarde este desenho. Todo o resto do guia é detalhar uma caixinha dele.

---

## Ordem de leitura sugerida

| Ordem | Arquivo | Linhas | Dificuldade |
|:---:|---|:---:|:---:|
| 1 | `src/agent_crew/__init__.py` | 17 | ⭐ |
| 2 | `src/agent_crew/schemas.py` | 127 | ⭐ |
| 3 | `src/agent_crew/state.py` | 42 | ⭐ |
| 4 | `src/agent_crew/config.py` | 111 | ⭐⭐ |
| 5 | `src/agent_crew/agents/base.py` | 160 | ⭐⭐⭐ |
| 6 | `src/agent_crew/agents/researcher.py` | 84 | ⭐⭐ |
| 7 | `src/agent_crew/graph.py` | 118 | ⭐⭐⭐ |
| 8 | `src/agent_crew/crew.py` | 134 | ⭐⭐ |
| 9 | `src/agent_crew/llm.py` | 288 | ⭐⭐⭐⭐⭐ |
| 10 | `src/agent_crew/cli.py` | 361 | ⭐⭐ |
| 11 | `src/agent_crew/api.py` | 213 | ⭐⭐ |
| 12 | `tests/test_crew.py` | 113 | ⭐⭐⭐ |

**Leia `llm.py` por último.** É o arquivo mais "chato" (configuração de
fornecedor, detalhes de API externa) e o que você menos precisa entender no
começo. Os outros sete agentes do time não sabem o que tem dentro dele — e
esse é justamente o ponto.

---

## 1. `src/agent_crew/__init__.py` — o mapa

```python
"""agent-crew — time de agentes de IA orquestrado com LangGraph.

    pesquisador -> analista -> redator -> revisor
                                             |
                          (reprovado) --------+---> volta pro redator
                          (aprovado)  -------------> fim
"""
```

**O que observar:** este arquivo não faz quase nada — e isso é ótimo. A
docstring desenha o sistema inteiro em 8 linhas. Quando alguém novo entra no
projeto, começa aqui.

**Regra que vale para todo o projeto:** se você não consegue explicar um
arquivo em 5 linhas no topo dele, provavelmente o arquivo faz coisas demais.

---

## 2. `schemas.py` — os contratos

Aqui estão os "formulários" que cada agente é obrigado a preencher.

```python
class Finding(BaseModel):
    title: str = Field(description="Título curto e direto do achado")
    summary: str = Field(description="2 a 4 frases explicando o achado")
    source: str = Field(description="De onde veio: URL, documento ou 'conhecimento do modelo'")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0,
                              description="O quanto essa informação é confiável (0 a 1)")
```

**O que observar:**

1. **`Field(description=...)` não é enfeite.** Essas descrições são enviadas
   ao modelo como parte do formato exigido. Elas são, literalmente, parte do
   prompt. Escrever bem aqui melhora o resultado.
2. **`ge=0.0, le=1.0`** garante que a confiança fica entre 0 e 1. Se o modelo
   devolver `1.5`, o Pydantic rejeita e a chamada é repetida.
3. **`default_factory=list`** em vez de `= []`. Parece detalhe, mas
   `default_factory` cria uma lista nova a cada instância. Usar `= []` faria
   todas as instâncias compartilharem a mesma lista — um bug clássico.

Os quatro contratos principais:

| Classe | Quem produz | Contém |
|--------|-------------|--------|
| `ResearchBrief` | Pesquisador | lista de `Finding` + perguntas em aberto |
| `Analysis` | Analista | pontos-chave, riscos, recomendação |
| `Draft` | Redator | título, markdown, contagem de palavras |
| `ReviewVerdict` | Revisor | aprovado (bool), nota 0–10, problemas, feedback |

No fim do arquivo ficam `CrewRequest` (o que você pede) e `CrewResult` (o
que você recebe).

---

## 3. `state.py` — o documento compartilhado

42 linhas. Este é, provavelmente, o arquivo mais importante para entender a
arquitetura — e o menor deles.

```python
class CrewState(TypedDict, total=False):
    question: str
    audience: str
    max_revisions: int
    revisions: int
    brief: ResearchBrief | None
    analysis: Analysis | None
    draft: Draft | None
    review: ReviewVerdict | None
    timeline: Annotated[list[str], operator.add]
```

**O que observar:**

**a) `total=False`** — nem todas as chaves existem o tempo todo. O estado vai
sendo preenchido conforme o trabalho avança.

**b) `Annotated[list[str], operator.add]`** — essa é a linha mais
interessante do projeto. O `operator.add` é um **reducer**: quando um agente
devolve `{"timeline": ["algo"]}`, o LangGraph **soma** à lista existente em
vez de substituir.

Sem ele, cada agente apagaria o histórico do anterior. Com ele, a timeline
cresce sozinha e nenhum agente precisa ler o histórico inteiro para
acrescentar uma linha.

> **Veja acontecendo:** `python examples/02_ver_o_estado.py` — a timeline
> passa de 1 item para 2, 3, 4... enquanto as outras chaves são substituídas.

---

## 4. `config.py` — configuração que falha cedo

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENT_CREW_", env_file=".env")
    provider: ProviderName = "mock"
    model_name: str = "gpt-4o-mini"
    ...
```

**O que observar:**

**a) O prefixo `AGENT_CREW_`** faz com que `AGENT_CREW_PROVIDER` no ambiente
vire `settings.provider`. Sem colisão com outras variáveis do sistema.

**b) `SecretStr`** esconde o valor da chave. `print(settings)` mostra
`SecretStr('**********')` em vez da chave. Você precisa chamar
`.get_secret_value()` explicitamente — o que torna vazamento acidental
difícil.

**c) `validate_for_run()`** roda **antes** de qualquer chamada ao modelo:

```python
def validate_for_run(self) -> None:
    if self.provider in ("openai", "anthropic") and not self.api_key:
        var = "OPENAI_API_KEY" if self.provider == "openai" else "ANTHROPIC_API_KEY"
        raise RuntimeError(
            f"O provedor '{self.provider}' precisa da variável {var}.\n"
            f"Opções:\n"
            f"  1) Coloque a chave no arquivo .env  ({var}=sk-...)\n"
            f"  2) Ou rode sem chave nenhuma usando o provedor de demonstração:\n"
            f'     agent-crew run "sua pergunta" --provider mock'
        )
```

Esse é o princípio **fail fast, fail clear**: falhe o mais cedo possível e
diga o que fazer. Descobrir que falta a chave depois de gastar 3 chamadas de
IA é ruim; a mensagem aqui te dá a saída pronta.

---

## 5. `agents/base.py` — a classe-base dos agentes

O arquivo que define **o que é um agente** neste projeto.

```python
class CrewAgent(ABC):
    name: str = "agente"
    description: str = ""
    output_type: type[BaseModel] = BaseModel

    def __init__(self, context: CrewContext) -> None:
        self.context = context
```

Um agente tem três coisas: **nome**, **descrição** e **formato de saída**.

**O que observar:**

**a) `CrewContext` — injeção de dependência:**

```python
@dataclass
class CrewContext:
    settings: Settings
    llm: LLM
    search: SearchTool
```

Os agentes **não criam** suas próprias conexões. Recebem um "kit de
ferramentas" pronto. É por isso que os testes passam um `MockLLM` e tudo roda
em milissegundos.

**b) `system_prompt()` junta duas coisas:**

```python
def system_prompt(self) -> str:
    return (
        f"{self.instructions.strip()}\n\n"
        "Regras gerais do time:\n"
        f"- Responda sempre em {idioma}.\n"
        "- Seja direto e específico. Nada de enchimento.\n"
        "- Nunca invente fontes, números ou citações.\n"
        "- Se faltar informação, diga o que falta em vez de supor."
    )
```

Cada agente escreve só as instruções do **seu papel** (`instructions`). As
regras do time são adicionadas automaticamente aqui. Se amanhã você quiser
que todo o time responda em francês, muda um lugar só.

**c) `act()` é o "esqueleto" que não muda:**

```python
async def act(self, state: CrewState) -> dict[str, Any]:
    output = await self.context.llm.complete(       # 1. fala com o modelo
        system=self.system_prompt(),
        user=self.build_prompt(state),
        output_type=self.output_type,
        agent_name=self.name,
    )
    update = self._apply(output, state)             # 2. diz onde guardar
    update.setdefault("timeline", []).append(self.log_line(output))  # 3. registra
    return update
```

Perceba: o `act()` é igual para todos. O que muda entre agentes é só o
`build_prompt()` (o que pedir) e o `_apply()` (onde guardar). **Esse é o
padrão Template Method** — a estrutura fica na base, os detalhes ficam nas
subclasses.

**d) `build_prompt` é síncrono, mas o pesquisador precisa buscar na web.**
Veja como ele resolve isso no próximo arquivo.

---

## 6. `agents/researcher.py` — um agente concreto

O menor agente do time e o único que usa ferramenta externa.

```python
class ResearcherAgent(CrewAgent):
    name = "pesquisador"
    output_type = ResearchBrief

    async def act(self, state: CrewState) -> dict[str, Any]:
        """Primeiro busca na web, depois sintetiza o dossiê."""
        question = state["question"]
        self._hits = await self.context.search.search(question)   # 1. ferramenta
        return await super().act(state)                           # 2. delega à base
```

**O que observar:**

**a) Ele sobrescreve `act()` para acrescentar um passo**, e depois chama
`super().act(state)` para o comportamento padrão. Não duplica nada.

**b) As fontes vêm da ferramenta, não da memória do modelo.** No prompt:

```python
return (
    f"Tema a investigar: {question}\n"
    f"Público leitor: {audience}\n\n"
    "Resultados da busca:\n"
    f"{resultados}\n\n"
    "Monte o dossiê de pesquisa sobre o tema acima."
)
```

E nas instruções: *"Nunca invente URLs, artigos ou números. Se não tem a
fonte, diminua o confidence e diga isso."* Duas camadas de proteção contra
referência inventada.

**c) O `_apply` tem uma linha:**

```python
def _apply(self, output: ResearchBrief, state: CrewState) -> dict[str, Any]:
    return {"brief": output}
```

Isso diz ao LangGraph: "a chave `brief` do estado agora é este valor".

> **Veja os prompts exatos:** `python examples/03_ver_os_prompts.py`

---

## 7. `graph.py` — o coração do projeto

118 linhas que definem o **comportamento** do sistema. O resto é
infraestrutura em volta disso.

### Montando os nós

```python
def make_node(agent_name: str):
    async def node(state: CrewState) -> dict[str, Any]:
        return await run_agent(state, agent_name=agent_name)
    node.__name__ = f"no_{agent_name}"
    return node

graph = StateGraph(CrewState)
for agent_name in AGENT_SEQUENCE:
    graph.add_node(agent_name, make_node(agent_name))
```

**O que observar:** cada nó é uma função `(estado) → mudanças no estado`.
Só isso. Não existe interface para implementar, nem classe especial. Um nó é
uma função assíncrona.

**Por que a função `make_node`?** Porque em Python, se você escrever um
`for` criando funções, todas acabam apontando para o último valor da
variável. A função de fábrica "congela" o nome do agente dentro do `node`.
Esse é um detalhe clássico de Python que vale conhecer (o "late binding
closure").

### As arestas normais

```python
graph.add_edge(START, RESEARCHER)
graph.add_edge(RESEARCHER, ANALYST)
graph.add_edge(ANALYST, WRITER)
graph.add_edge(WRITER, REVIEWER)
```

Uma linha reta. O fluxo principal não tem surpresa.

### A aresta condicional — a decisão do sistema

```python
graph.add_conditional_edges(
    REVIEWER,
    _route_after_review,
    {WRITER: WRITER, END: END},
)
```

E a função que decide:

```python
def _route_after_review(state: CrewState) -> str:
    review = state.get("review")
    revisions = state.get("revisions", 0)
    max_revisions = state.get("max_revisions", 0)

    if review is not None and review.approved:
        return END                          # 1. aprovado → acabou

    if revisions >= max_revisions:
        return END                          # 2. limite → entrega assim mesmo

    return WRITER                           # 3. reprovado → reescreve
```

**O que observar:** o comportamento adaptativo do sistema inteiro são
**8 linhas**. E o caso 2 é a trava contra loop infinito — a decisão mais
importante de todas.

**Por que testar essa função é tão valioso?** Porque ela é o cérebro do
fluxo, é uma função pura (mesma entrada = mesma saída), e dá para testar sem
rodar nada. Três testes cobrem 100% dela.

> **Veja a decisão acontecer:** `python examples/05_a_decisao_do_fluxo.py`

---

## 8. `crew.py` — a fachada

O arquivo que o CLI e a API usam. Eles **não conhecem** o grafo, os agentes
nem o estado.

```python
async def run_crew(request, *, settings=None, llm=None, search=None) -> CrewResult:
    context = CrewContext(
        settings=settings,
        llm=llm or build_llm(settings),
        search=search or build_search_tool(settings),
    )
    graph = build_graph(context)
    final_state = await graph.ainvoke(initial_state(request, settings))
    return result_from_state(final_state, request)
```

**O que observar:**

**a) Duas funções, dois usos:**

| Função | Devolve | Usada por |
|--------|---------|-----------|
| `run_crew()` | Resultado final completo | API `/crew/run` |
| `stream_crew()` | `(agente, estado)` a cada etapa | CLI e API `/crew/stream` |

**b) `llm or build_llm(settings)`** — se alguém passou um LLM, usa ele; senão
constrói o normal. É isso que permite os testes injetarem o `MockLLM` sem
tocar na lógica.

**c) `_merge()` existe porque `stream_crew` precisa acumular o estado.**
O `astream()` devolve só o que cada nó mudou. Para o CLI poder mostrar o
progresso, somamos as mudanças — respeitando o reducer da `timeline`.

---

## 9. `llm.py` — a camada de LLM

O arquivo mais longo e, para quem está começando, o menos importante de
entender a fundo. Leia por cima.

O que importa é o **contrato**:

```python
@runtime_checkable
class LLM(Protocol):
    async def complete(self, *, system, user, output_type, agent_name) -> T: ...
```

Qualquer objeto com esse método pode ser o "cérebro" do time. Existem duas
implementações:

| Classe | O que faz | Quando é usada |
|--------|-----------|----------------|
| `PydanticAILLM` | Fala com OpenAI/Anthropic de verdade | Em produção |
| `MockLLM` | Devolve conteúdo simulado, offline | Testes e modo demo |

E uma fábrica decide:

```python
def build_llm(settings: Settings) -> LLM:
    if settings.provider == "mock":
        return MockLLM()
    return PydanticAILLM(settings)
```

**O que observar:** é essa função que faz o projeto rodar sem chave de API,
testar de graça, e trocar de fornecedor com uma linha no `.env`. Tudo isso
cabe em 3 linhas.

O `MockLLM` tem um detalhe divertido: o primeiro parecer do revisor é sempre
uma **reprovação**, para que você veja o ciclo de revisão acontecendo.

---

## 10. `cli.py` — a interface de terminal

Typer (argumentos) + Rich (saída bonita). Não tem nada de IA aqui — e isso é
bom. Se você entende de CLI, entende este arquivo; não precisa entender de
agentes.

**O que observar:**

```python
def _apply_overrides(*, provider=None, model=None, ...) -> Settings:
    settings = get_settings()
    overrides = {}
    if provider:
        overrides["provider"] = provider
    ...
    return settings.model_copy(update=overrides) if overrides else settings
```

`model_copy(update=...)` cria uma **cópia** com os campos trocados em vez de
alterar o objeto original. Assim os `--flags` valem só para aquela execução e
não sujam a configuração global. Fazer isso "na mão" (alterando o objeto
compartilhado) criaria bugs difíceis de achar.

---

## 11. `api.py` — a interface HTTP

Mesma história: se você conhece FastAPI, você conhece este arquivo.

Os endpoints, em ordem de leitura:

| Rota | O que mostra |
|------|--------------|
| `GET /health` | Que o serviço está no ar |
| `GET /agents` | Que o FastAPI deriva tudo de `build_agents()` |
| `GET /providers` | Como **não** vazar uma chave (só booleanos) |
| `POST /crew/run` | A chamada de 3 linhas a `run_crew()` |
| `POST /crew/stream` | Como transformar `stream_crew()` em eventos SSE |

**O que observar:** o endpoint principal são três linhas:

```python
@app.post("/crew/run", response_model=CrewResult, tags=["crew"])
async def crew_run(request: CrewRequest) -> CrewResult:
    try:
        return await run_crew(request)
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
```

`response_model=CrewResult` faz o FastAPI gerar a documentação completa
sozinho. Abra `/docs` e veja: você ganhou uma interface interativa de graça,
por ter tipado o retorno.

---

## 12. `tests/test_crew.py` — provas, não decoração

Teste não é burocracia: é a única forma de mudar o código sem medo.

```python
def test_roteamento_termina_quando_o_limite_de_revisoes_e_atingido():
    """Sem esta trava, um revisor exigente criaria um loop infinito."""
    estado = {"review": ReviewVerdict(approved=False, score=4),
              "revisions": 2, "max_revisions": 2}
    assert _route_after_review(estado) == END
```

**O que observar:**

**a) O teste mais valioso é o mais chato de escrever.** Testar o freio contra
loop infinito é literalmente 3 linhas — e protege contra o pior bug possível
do sistema.

**b) `async def test_...` sem `@pytest.mark.asyncio`?** Funciona porque o
`pyproject.toml` tem `asyncio_mode = "auto"`.

**c) Nenhum teste precisa de internet, chave ou dinheiro.** Por causa do
`MockLLM`. É disso que estamos falando quando dizemos "arquitetura
testável".

---

## Os cinco conceitos que você aprendeu sem perceber

Se você leu até aqui, já viu na prática:

| Conceito | Onde está no projeto |
|----------|----------------------|
| **Injeção de dependência** | `CrewContext` passado para cada agente |
| **Inversão de dependência** | `LLM` como Protocol; o agente não sabe qual modelo |
| **Template Method** | `CrewAgent.act()` chama `build_prompt()` e `_apply()` das subclasses |
| **Facade** | `run_crew()` esconde grafo, estado e agentes |
| **Fail fast** | `validate_for_run()` e a validação do Pydantic |

Não precisa decorar os nomes. O importante é reconhecer o padrão quando ele
aparecer de novo — e ele aparece em todo projeto sério.

---

## Próximo passo

Agora que você entendeu, **mexa**. Vá para
[`docs/exercicios.md`](exercicios.md): são 10 exercícios em ordem crescente
de dificuldade, do "mude um texto" até "crie um agente novo".

A melhor forma de consolidar é quebrar e consertar.
