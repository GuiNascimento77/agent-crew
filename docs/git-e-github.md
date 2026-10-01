# Git e GitHub: do zero ao projeto publicado

Guia pensado para quem está começando. Sem enrolação e sem pular etapas.

---

## 1. Antes de tudo: Git e GitHub não são a mesma coisa

Essa confusão é a primeira que todo mundo tem, então vale separar bem:

| | Git | GitHub |
|---|---|---|
| **O que é** | Um programa que roda no **seu computador** | Um **site** (na nuvem) |
| **Para que serve** | Guardar o histórico do seu código | Hospedar esse histórico e mostrar para o mundo |
| **Precisa de internet?** | Não | Sim |
| **Analogia** | O Word com "controlar alterações" | O Google Drive onde você guarda o arquivo |

O Git cria uma **linha do tempo** do seu projeto. Cada vez que você
"salva um ponto" nessa linha do tempo, isso se chama **commit**. Um commit
tem: o que mudou, quem mudou, quando, e uma mensagem explicando o porquê.

O GitHub guarda essa linha do tempo online. E é ele que as pessoas olham
quando você diz "meu projeto está no meu GitHub".

> **Por que isso importa no portfólio?** Porque um recrutador ou um cliente
> não quer só ver o resultado final. Ele quer ver **como você trabalha**:
> commits pequenos e claros, mensagens que explicam decisões, histórico de
> evolução. Isso já conta como sinal de senioridade.

---

## 2. Instalando e configurando (uma vez só)

```bash
# Verifique se já está instalado
git --version

# Se não estiver: 
#   Ubuntu/Debian: sudo apt install git
#   macOS:         xcode-select --install
#   Windows:       baixe em https://git-scm.com/download/win
```

Agora diga ao Git quem você é. Isso vai em cada commit que você fizer:

```bash
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"
```

> Dica: use o **mesmo e-mail** da sua conta do GitHub. É assim que o GitHub
> liga seus commits ao seu perfil.

Um detalhe que facilita a vida desde o começo:

```bash
# Guarda sua senha/token para você não digitar toda hora
git config --global credential.helper store

# Muda o nome padrão da branch principal de "master" para "main"
# (é o padrão que o GitHub usa hoje)
git config --global init.defaultBranch main
```

---

## 3. O vocabulário mínimo

Cinco palavras resolvem 90% do dia a dia:

| Comando | O que faz | Analogia |
|---------|-----------|----------|
| `git status` | Mostra o que mudou e o que ainda não foi salvo | Olhar a mesa antes de arrumar |
| `git add` | Escolhe **o que** vai entrar no próximo commit | Separar o que vai na caixa |
| `git commit` | Salva um ponto na linha do tempo | Fechar e etiquetar a caixa |
| `git push` | Envia seus commits para o GitHub | Postar a caixa |
| `git pull` | Traz o que está no GitHub para o seu computador | Receber uma caixa |

Fluxo mental:

```
  seu código  ──(git add)──▶  área de preparo  ──(git commit)──▶  histórico local
                                                                        │
                                                                   (git push)
                                                                        ▼
                                                                     GitHub
```

---

## 4. As três formas de começar

### Forma A — Você já tem o projeto e quer criar o repositório

Este é o seu caso. O projeto já está pronto no seu computador:

```bash
cd agent-crew

# 1. Inicializa o Git nesta pasta (cria a "linha do tempo")
git init

# 2. Confere o que o Git está vendo
git status

# 3. Adiciona todos os arquivos ao primeiro commit
git add .

# 4. Faz o primeiro commit
git commit -m "feat: time de agentes de IA com LangGraph, API FastAPI e CLI"
```

Antes do `git add`, confira **sempre** que o arquivo `.env` **não** vai
subir junto. Ele está no `.gitignore` justamente para isso. Para ter
certeza:

```bash
git status --short | grep -i "\.env"
# se aparecer apenas ".env.example", está tudo certo.
# se aparecer ".env" sozinho, PARE e verifique antes de continuar.
```

**Nunca** comite chaves de API. Uma chave pública é uma chave que alguém vai
usar na sua conta — e a conta é sua.

### Forma B — O repositório já existe no GitHub e você quer copiar

```bash
git clone https://github.com/SEU-USUARIO/agent-crew.git
cd agent-crew
```

### Forma C — Começar do zero pelo GitHub

Crie o repositório vazio no site, depois:

```bash
git clone https://github.com/SEU-USUARIO/agent-crew.git
cd agent-crew
# ... crie seus arquivos ...
git add .
git commit -m "feat: versão inicial"
git push
```

---

## 5. Ligando seu projeto local ao GitHub

Você fez `git init` e o commit. Agora precisa dizer **para onde** enviar.

**Passo 1 — Crie o repositório no GitHub:**

1. Entre em [github.com](https://github.com) e faça login.
2. Clique no **+** no canto superior direito → **New repository**.
3. **Repository name**: `agent-crew`
4. **Description**: aproveite — é a primeira coisa que as pessoas leem.
5. Marque **Public** (você quer que apareça no portfólio).
6. **NÃO** marque "Add a README file", "Add .gitignore" nem "Choose a
   license". Você já tem tudo isso no seu computador; marcar aqui cria
   arquivos que vão conflitar com os seus.
7. Clique em **Create repository**.

**Passo 2 — Conecte e envie:**

O GitHub vai mostrar exatamente estes comandos na página do repositório novo:

```bash
# Apelida o endereço do repositório remoto de "origin"
git remote add origin https://github.com/SEU-USUARIO/agent-crew.git

# Renomeia sua branch para "main" (padrão do GitHub)
git branch -M main

# Envia seus commits e liga a branch local à remota (-u = "grava essa ligação")
git push -u origin main
```

Pronto. Atualize a página do GitHub e seu projeto está lá.

---

## 6. O dia a dia depois disso

O ciclo se repete sempre assim:

```bash
# 1. Veja o que mudou
git status

# 2. Veja exatamente o que mudou, linha por linha (opcional, mas valioso)
git diff

# 3. Escolha o que entra
git add .                          # tudo
git add src/agent_crew/graph.py    # só um arquivo (mais preciso)

# 4. Salve com uma mensagem que explique o PORQUÊ
git commit -m "fix: evita loop infinito quando o revisor nunca aprova"

# 5. Envie
git push
```

### Como escrever uma boa mensagem de commit

Use o padrão **Conventional Commits**. É simples e é o que o mercado usa:

```
tipo(escopo): descrição curta no imperativo
```

| Tipo | Quando usar |
|------|-------------|
| `feat` | Adicionou algo novo |
| `fix` | Corrigiu um bug |
| `docs` | Mexeu só em documentação |
| `test` | Adicionou ou ajustou testes |
| `refactor` | Mudou o código sem mudar o comportamento |
| `chore` | Tarefas de manutenção (dependências, config) |

Compare os dois estilos:

```
❌ "atualizações"
❌ "mexi em umas coisas"
❌ "agora funciona"

✅ feat(search): adiciona ferramenta de busca Tavily
✅ fix(graph): evita loop infinito quando o revisor nunca aprova
✅ docs(readme): explica como rodar sem chave de API
```

Quem lê o segundo estilo entende **o que** mudou e **por que** — em 5
segundos. Isso vale ouro no portfólio.

---

## 7. Autenticação: a senha não funciona mais

Se ao dar `git push` o GitHub pedir usuário e senha, **a senha da sua
conta não vai funcionar**. Hoje o GitHub exige um **Personal Access Token**
(PAT), que é uma senha temporária só para o Git.

**Como criar:**

1. GitHub → clique na sua foto → **Settings**
2. Menu lateral, no fim: **Developer settings**
3. **Personal access tokens** → **Tokens (classic)**
4. **Generate new token (classic)**
5. **Note**: `git no notebook` — **Expiration**: 90 dias
6. **Scopes**: marque **`repo`**
7. **Generate token** e **copie o valor agora** (ele só aparece uma vez)

Quando o `git push` pedir:
- **Username**: seu usuário do GitHub
- **Password**: cole o **token** (não a senha da conta)

Se você configurou `credential.helper store`, ele não pergunta de novo.

> **Sobre segurança:** o token é tão poderoso quanto sua senha. Nunca
> coloque em arquivo, nunca comite, nunca cole em chat ou print de tela.
> Vazou? Volte em Settings e revogue na hora.

**Sobre "fazer o push pra você":** isso exigiria que você entregasse um
token seu para outra pessoa (ou para um agente) usar em seu nome. Não
recomendo — e não é necessário. Os comandos acima são sempre os mesmos, e
depois que você faz uma vez, vira automático. Guia passo a passo é melhor
que token na mão de terceiros.

---

## 8. Deixando o repositório bonito para portfólio

Um repositório arrumado diz "eu me importo com meu trabalho". O mínimo:

- [ ] **README.md** com o que é, como rodar, e o que você aprendeu ← você já tem
- [ ] **Descrição** e **topics** preenchidos no site (engrenagem ao lado de "About")
- [ ] **LICENSE** presente (MIT é a mais comum)
- [ ] **.gitignore** impedindo lixo e segredos de subirem
- [ ] **Testes** que rodam sozinhos (`pytest`)
- [ ] **Commits pequenos** com mensagens claras
- [ ] **Print ou GIF** do projeto rodando — a primeira coisa que alguém olha

### Sobre os `topics`

Na página do repositório, clique na engrenagem ao lado de **About** e
adicione:

```
ai-agents  langgraph  pydantic-ai  fastapi  llm  multi-agent  python  portfolio
```

É por aqui que gente procurando esses assuntos te encontra.

### Sobre o "About"

Uma linha objetiva vale mais que um parágrafo:

> Time de agentes de IA (pesquisa, análise, redação e revisão) orquestrado
> com LangGraph e Pydantic AI, com API FastAPI e CLI. Funciona sem chave de
> API no modo demo.

---

## 9. Erros comuns (e como sair deles)

**"Permission denied (publickey)"**
Você está usando SSH mas não configurou a chave. Ou configure
([guia oficial](https://docs.github.com/pt/authentication/connecting-to-github-with-ssh)),
ou use HTTPS com token, que é mais simples para começar.

**"Updates were rejected because the remote contains work that you do not have"**
O GitHub tem commits que você não tem localmente (normalmente um README
criado pelo site). Resolva com:

```bash
git pull --rebase origin main
git push
```

Se não quiser lidar com o merge agora:

```bash
git pull origin main --allow-unrelated-histories
git push
```

**"failed to push some refs"** logo depois de criar o repo
Você não fez `git pull` da primeira vez. Mesmo comando acima.

**Comitei minha chave de API sem querer** 😱
1. **Revogue a chave imediatamente** no painel do provedor. Isso é a
   prioridade — não o Git.
2. Gere uma nova.
3. Remova o arquivo do controle de versão:

```bash
git rm --cached .env
echo ".env" >> .gitignore
git commit -m "chore: remove credenciais do controle de versão"
```

4. Lembre: o commit antigo **continua no histórico**. Se for um repositório
   público, revogar a chave é o que realmente resolve.

**Quero desfazer o último commit mas manter as mudanças:**

```bash
git reset --soft HEAD~1
```

---

## 10. O que fazer agora, na prática

Na ordem:

```bash
cd agent-crew
cp .env.example .env            # seu .env de trabalho (não vai subir)
git init
git add .
git status --short | grep -i "\.env"        # confirme: só o .env.example
git commit -m "feat: time de agentes de IA com LangGraph, Pydantic AI, API e CLI"
```

Depois, no site do GitHub: crie o repositório `agent-crew` (público, **sem**
README/.gitignore/license). E então:

```bash
git remote add origin https://github.com/SEU-USUARIO/agent-crew.git
git branch -M main
git push -u origin main
```

Pronto. Seu portfólio tem um projeto de agentes de IA publicado, com
testes, documentação e licença.

---

## Cola rápida

```bash
git status                        # o que mudou?
git diff                          # quais linhas mudaram?
git add .                         # quero tudo no próximo commit
git add caminho/arquivo.py        # quero só este arquivo
git commit -m "feat: descrição"   # salva o ponto na linha do tempo
git push                          # envia para o GitHub
git pull                          # traz do GitHub
git log --oneline --graph         # ver o histórico de forma bonita
git remote -v                     # para onde este projeto está ligado?
```
