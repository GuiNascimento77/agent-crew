# Como funciona, passo a passo

Este documento abre o capô. Se você quer entender **exatamente** o que
acontece quando você roda `agent-crew run "..."`, é aqui.

---

## O caminho de uma execução

Imagine o pedido:

```bash
agent-crew run "A IA vai substituir programadores?" --audience "gestores de tecnologia"
```

O que acontece, na ordem:

```
1. O CLI lê o .env e monta a configuração
2. O CLI cria o "estado inicial" com a pergunta e o público
3. O grafo começa a rodar pelo nó "pesquisador"
4. Cada nó lê o estado, chama o LLM e devolve só o que mudou
5. O revisor decide: termina ou volta para o redator?
6. O CLI junta tudo e imprime o resultado
```

Agora o detalhe de cada etapa.

---

## Passo 0 — Configuração e estado inicial

Antes de qualquer agente trabalhar, dois objetos são criados.

**`Settings`** (`config.py`) — de onde vem tudo que é configurável:
provedor, modelo, temperatura, limite de revisões. Vem do arquivo `.env`.

**`CrewState`** (`state.py`) — o "documento compartilhado" que passa de
agente em agente:

```python
{
    "question": "A IA vai substituir programadores?",
    "audience": "gestores de tecnologia",
    "max_revisions": 1,
    "revisions": 0,
    "brief": None,       # preenchido pelo pesquisador
    "analysis": None,    # preenchido pelo analista
    "draft": None,       # preenchido pelo redator
    "review": None,      # preenchido pelo revisor
    "timeline": [],      # histórico do que aconteceu
}
```

> **Por que um estado único em vez de variáveis soltas?**
> Porque qualquer agente pode ser inspecionado, testado e até retomado.
> Você consegue salvar o estado no meio do caminho e continuar depois — é
> assim que se implementa "pausar e retomar" em sistemas com agentes.

---

## Passo 1 — PESQUISADOR

**O que ele faz:** busca na web e monta um dossiê.

```python
async def act(self, state):
    self._hits = await self.context.search.search(state["question"])  # 1
    return await super().act(state)                                   # 2
```

1. Chama a **ferramenta** de busca — uma função comum do projeto, não uma
   capacidade do modelo.
2. Manda o resultado para o LLM sintetizar em um `ResearchBrief`.

**O prompt, em essência:**

```
Tema a investigar: A IA vai substituir programadores?
Público leitor: gestores de tecnologia

Resultados da busca:
- [SIMULADO] Resultado de exemplo nº 1 (https://exemplo.com/artigo-1)
  Trecho...

Monte o dossiê de pesquisa sobre o tema acima.
```

E as instruções de sistema dizem, entre outras coisas:

> "- Nunca invente URLs, artigos ou números. Se não tem a fonte, diminua o
> confidence e diga isso."

**A saída:**

```python
ResearchBrief(
    question="A IA vai substituir programadores?",
    findings=[
        Finding(title="...", summary="...", source="https://...", confidence=0.8),
        ...
    ],
    open_questions=["O que falta investigar?"],
)
```

> **Ponto-chave:** as fontes vêm da **ferramenta**, não da memória do
> modelo. Isso reduz drasticamente a alucinação de referências — o problema
> mais chato de sistemas que "pesquisam" sozinhos.

---

## Passo 2 — ANALISTA

**O que ele faz:** transforma dossiê em entendimento.

Ele não busca nada e não escreve o texto final. Só recebe o `ResearchBrief`
e devolve um `Analysis`:

```python
Analysis(
    key_points=["...", "..."],
    risks=["Dado desatualizado sobre X", "Fonte sem data"],
    recommendation="Investir em formação, não em substituição.",
    confidence=0.7,
)
```

**As instruções dele incluem:**

> "- Dê mais peso aos achados com confidence alta.
>  - Aponte explicitamente o que é FRACO no dossiê [...]
>  - Se um achado não sustenta uma conclusão, diga isso."

> **Por que separar pesquisador e analista?**
> Porque são competências que se atrapalham. O pesquisador é cobrado por
> **amplitude** (trazer bastante material); o analista é cobrado por
> **profundidade** (achar o que importa e o que não se sustenta). Um único
> agente fazendo as duas coisas tende a fazer as duas mal — e fica
> impossível saber qual das duas falhou quando o resultado sai ruim.

---

## Passo 3 — REDATOR

**O que ele faz:** escreve o texto final em Markdown.

Este agente é chamado **mais de uma vez** quando a revisão está ligada.

Na primeira chamada, o prompt traz só a análise:

```
Tema: ...
Público leitor: gestores de tecnologia

Análise a ser transformada em texto:
Pontos-chave:
- ...
Recomendação: ...

Escreva a primeira versão do texto.
```

Na segunda (após reprovação), ele recebe também as correções:

```
Esta é a revisão nº 1.
Correções exigidas pelo revisor:
Nota anterior: 6/10
[MISSING] Acrescente pelo menos um exemplo concreto.
Problemas:
- Falta uma seção de exemplos práticos.

Reescreva o texto corrigindo os pontos acima.
```

E aqui está a parte esperta — o redator conta as reescritas:

```python
def _apply(self, output, state):
    pending_review = state.get("review")
    is_rewrite = bool(pending_review and not pending_review.approved)
    revisions = state.get("revisions", 0) + (1 if is_rewrite else 0)
    return {"draft": output, "revisions": revisions, "review": None}
```

Note o `"review": None`: a revisão antiga é **limpa** do estado, porque já
foi respondida. Isso evita que uma correção velha seja aplicada duas vezes.

---

## Passo 4 — REVISOR (o porteiro)

**O que ele faz:** julga e decide o destino do fluxo.

Ele recebe a análise **e** o texto, e devolve:

```python
ReviewVerdict(
    approved=False,
    score=6,
    issues=["Falta uma seção de exemplos práticos."],
    feedback="Acrescente pelo menos um exemplo concreto.",
)
```

**Cinco critérios, todos com o mesmo peso:** clareza, fidelidade (o texto
só afirma o que está na análise?), estrutura, honestidade (as incertezas
estão explicitadas?) e adequação ao público.

**A regra de decisão dele:**

> "`approved` = True somente se a nota for 8 ou mais E não houver problema
> de fidelidade. Informação inventada é reprovação imediata."

---

## Passo 5 — A decisão que controla tudo

Depois do revisor, o LangGraph chama uma função de **roteamento**. É a única
bifurcação do sistema:

```python
def _route_after_review(state):
    review = state.get("review")
    revisions = state.get("revisions", 0)
    max_revisions = state.get("max_revisions", 0)

    if review is not None and review.approved:
        return END              # 1. aprovado -> acabou

    if revisions >= max_revisions:
        return END              # 2. limite atingido -> entrega assim mesmo

    return WRITER               # 3. reprovado e há tentativas -> reescreve
```

Visualizando com `max_revisions = 1`:

```
pesquisador → analista → redator → revisor ──(reprovado)──┐
                                     ▲                     │
                                     └─────────────────────┘
                                       redator → revisor ──(aprovado)──▶ fim
```

**O caso 2 é o mais importante.** Imagine: o revisor é exigente, o redator
não consegue melhorar mais, e ninguém colocou um limite. O resultado é um
programa travado para sempre, queimando tokens — o clássico loop infinito
de sistemas com agentes. É por isso que existe o `max_revisions`, e é por
isso que ele tem um teste dedicado.

> Quando o limite é atingido sem aprovação, o resultado final vem com o
> parecer anexado. **Entregar um texto imperfeito e honesto ("não passou na
> revisão, veja o que ficou pendente") é melhor que travar ou mentir que
> deu certo.**

---

## O que acontece quando você usa um LLM de verdade

Trocando `AGENT_CREW_PROVIDER=mock` por `openai` ou `anthropic`, uma única
coisa muda: a chamada ao modelo.

## Por que a orquestração fica intacta?

Por causa de uma linha em `llm.py`:

```python
def build_llm(settings):
    if settings.provider == "mock":
        return MockLLM()
    return PydanticAILLM(settings)
```

Os agentes nunca souberam qual era. Eles recebem um `CrewContext` com um
objeto que cumpre o contrato `LLM` (tem o método `complete`) e pronto.

Isso é **inversão de dependência** — o princípio de projeto por trás de
todo o resto. É ele que permite:

- rodar sem chave de API;
- testar sem gastar dinheiro;
- trocar de fornecedor sem reescrever nada;
- desenvolver a orquestração sem chamar o modelo.

---

## Resumo em uma tabela

| Agente | Lê do estado | Escreve no estado | Saída estruturada | Usa ferramenta? |
|--------|--------------|-------------------|-------------------|-----------------|
| Pesquisador | `question`, `audience` | `brief` | `ResearchBrief` | ✅ busca |
| Analista | `brief` | `analysis` | `Analysis` | ❌ |
| Redator | `analysis`, `review`, `revisions` | `draft`, `revisions`, `review` | `Draft` | ❌ |
| Revisor | `draft`, `analysis` | `review` | `ReviewVerdict` | ❌ |

Uma linha por agente, uma responsabilidade por linha. É o mapa inteiro do
sistema.
