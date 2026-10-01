# Exemplos executáveis

Seis scripts curtos para **ver o sistema funcionando** em vez de só ler o
código. Cada um isola uma parte do projeto.

Todos rodam no modo demonstração: **sem internet, sem chave de API e sem
custo**. Nenhum deles precisa de configuração.

## Pré-requisito

O pacote precisa estar instalado (na raiz do projeto):

```bash
pip install -e ".[dev]"
```

## Rodando

```bash
python examples/01_rodar_o_time.py
python examples/02_ver_o_estado.py
# ... e assim por diante
```

| # | Arquivo | O que ensina | Conceito |
|:-:|---------|--------------|----------|
| 1 | `01_rodar_o_time.py` | Como usar o time inteiro em 3 linhas | Fachada (Facade) |
| 2 | `02_ver_o_estado.py` | **O mais importante.** Como o estado muda a cada agente | Estado compartilhado, reducers |
| 3 | `03_ver_os_prompts.py` | O que exatamente é enviado para a IA | Engenharia de prompt |
| 4 | `04_um_agente_so.py` | Usar um agente isolado, sem o time | Injeção de dependência |
| 5 | `05_a_decisao_do_fluxo.py` | A função que decide o fluxo (e a trava de segurança) | Roteamento condicional |
| 6 | `06_chamar_a_api.py` | Chamar a API sem subir servidor | Testes de API em memória |

## Sugestão de ordem

Se você quer entender o projeto:

```
01  →  visão geral: o time todo funcionando
02  →  como o estado se transforma (leia este com calma)
03  →  onde mora o comportamento de cada agente
05  →  a decisão que controla o fluxo
04  →  como testar um agente isolado
06  →  a mesma coisa, mas por HTTP
```

## Depois de rodar

Vá para [`docs/tour-do-codigo.md`](../docs/tour-do-codigo.md) para a leitura
guiada do código, e depois para
[`docs/exercicios.md`](../docs/exercicios.md) para praticar.

## Quer ver de verdade?

Com uma chave de API no `.env`, os mesmos fluxos passam a gerar conteúdo
real. Troque o `Settings(provider="mock")` por `provider="openai"` em
qualquer exemplo — é literalmente uma linha.
