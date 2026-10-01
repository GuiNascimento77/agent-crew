# Como contribuir

Vale tanto para quem quer colaborar quanto para você mesmo daqui a três
meses, quando esquecer como o projeto funciona.

---

## Preparando o ambiente

```bash
git clone https://github.com/GuiNascimento77/agent-crew.git
cd agent-crew

python3 -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

O `-e` é de *editable*: as mudanças no código passam a valer na hora, sem
reinstalar. O `[dev]` traz pytest e as ferramentas de teste.

Confira que está tudo no lugar:

```bash
pytest -q
```

Devem passar **30 testes**. Se passaram, seu ambiente está pronto.

---

## O ciclo de trabalho

1. **Crie uma branch** com nome descritivo:

```bash
git checkout -b feat/paralelizar-pesquisadores
```

2. **Escreva o teste primeiro** (ou pelo menos junto). Isso não é dogma, é
   prática: escrever o teste antes te obriga a decidir o que "pronto"
   significa.

3. **Implemente.**

4. **Rode tudo:**

```bash
make check      # testes + verificação de estilo
```

5. **Comite** com Conventional Commits:

```bash
git add .
git commit -m "feat(researcher): roda duas buscas em paralelo"
```

6. **Envie e abra um Pull Request.**

---

## Convenções do projeto

**Mensagens de commit** seguem [Conventional Commits](https://www.conventionalcommits.org/pt-br/):

```
feat(escopo):     nova funcionalidade
fix(escopo):      correção de bug
docs:             documentação
test:             testes
refactor:         mudança sem alterar comportamento
chore:            manutenção (dependências, configuração)
```

**Código Python:**

- Nomes de variáveis, funções e textos em **português** (é um projeto de
  portfólio em português — a clareza para quem lê vale mais).
- Palavras-chave da linguagem e nomes de bibliotecas em inglês, obviamente.
- Docstrings explicando **o porquê**, não o óbvio.
- Type hints em tudo. Eles são a documentação que o editor realmente lê.

**Estrutura:** cada arquivo tem uma responsabilidade. Antes de criar um
arquivo novo, pergunte: "isso já não pertence a algum arquivo que existe?"

---

## Onde colocar cada tipo de mudança

| Você quer... | Mexa em... |
|--------------|-----------|
| Melhorar o comportamento de um agente | `src/agent_crew/agents/<agente>.py` (as instruções) |
| Mudar o que um agente devolve | `src/agent_crew/schemas.py` |
| Mudar a ordem ou as condições do fluxo | `src/agent_crew/graph.py` |
| Adicionar um novo agente | `schemas.py` + `agents/` + `graph.py` |
| Adicionar uma ferramenta nova | `src/agent_crew/tools/` |
| Adicionar um provedor de LLM | `src/agent_crew/llm.py` |
| Novo endpoint | `src/agent_crew/api.py` |
| Nova opção do CLI | `src/agent_crew/cli.py` |
| Uma configuração nova | `src/agent_crew/config.py` + `.env.example` |

**Testes:** toda mudança de comportamento merece um teste. Toda correção de
bug **precisa** de um teste que falharia antes da correção — é a única
maneira de garantir que o bug não volta.

---

## Checklist antes de abrir um Pull Request

- [ ] `pytest -q` passa (30+ testes)
- [ ] Adicionei testes para o que mudei
- [ ] Atualizei o README se a mudança for visível para quem usa
- [ ] Atualizei o `.env.example` se adicionei configuração
- [ ] Nenhum `.env`, chave ou segredo entrou no commit
- [ ] Escrevi commits pequenos e com mensagens claras

Confira o ponto dos segredos:

```bash
git status --short | grep -i "\.env"
# deve aparecer apenas ".env.example"
```

---

## Adicionando um agente novo (exemplo completo)

Suponha que você quer um **"fact-checker"** entre o redator e o revisor.

**1. O contrato** (`schemas.py`):

```python
class FactCheck(BaseModel):
    checked_claims: list[str] = Field(default_factory=list)
    unsupported: list[str] = Field(default_factory=list)
    verdict: str = ""
```

**2. O agente** (`agents/fact_checker.py`):

```python
class FactCheckerAgent(CrewAgent):
    name = "fact-checker"
    description = "Confere se cada afirmação do texto tem respaldo na análise."
    output_type = FactCheck

    @property
    def instructions(self) -> str:
        return "Sua função é conferir afirmação por afirmação..."

    def build_prompt(self, state): ...
    def _apply(self, output, state): return {"fact_check": output}
```

**3. O estado** (`state.py`): adicione `fact_check: FactCheck | None`.

**4. O grafo** (`graph.py`): registre o nó e a aresta
`WRITER → FACT_CHECKER → REVIEWER`.

**5. O teste** (`tests/test_crew.py`): garanta que ele entra na ordem certa.

**6. A documentação**: README (tabela dos agentes) e `docs/como-funciona.md`.

O ponto interessante: você **não** precisa mexer no CLI nem na API. Foi para
isso que a fachada existe.

---

## Dúvidas

Abra uma [issue](https://github.com/GuiNascimento77/agent-crew/issues) descrevendo
o que tentou e o que aconteceu. Inclua o erro completo e os passos para
reproduzir — isso ajuda a te ajudar.
