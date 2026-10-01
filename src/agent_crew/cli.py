"""Interface de linha de comando (CLI).

Feita com Typer (argumentos e ajuda) + Rich (saída bonita no terminal).

Comandos disponíveis:

    agent-crew run "sua pergunta"     roda o time inteiro
    agent-crew agents                 lista os agentes do time
    agent-crew providers              mostra os provedores e o que está configurado
    agent-crew serve                  sobe a API HTTP
    agent-crew version                mostra a versão

Todo comando tem ajuda: `agent-crew run --help`.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import __version__
from .config import Settings, get_settings
from .crew import initial_state, result_from_state, stream_crew
from .graph import AGENT_SEQUENCE, build_agents
from .schemas import CrewRequest, CrewResult

app = typer.Typer(
    name="agent-crew",
    help="Time de agentes de IA: pesquisador, analista, redator e revisor.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()

# Rótulos de exibição de cada agente, na ordem do fluxo.
AGENT_LABELS = {
    "pesquisador": "Pesquisador",
    "analista": "Analista",
    "redator": "Redator",
    "revisor": "Revisor",
}


# =====================================================================
#  Helpers
# =====================================================================


def _apply_overrides(
    *,
    provider: str | None = None,
    model: str | None = None,
    search: str | None = None,
    temperature: float | None = None,
) -> Settings:
    """Aplica os `--flags` da linha de comando sobre o que veio do .env.

    `model_copy(update=...)` cria uma CÓPIA com os campos trocados. Fazer
    assim (em vez de alterar o objeto original) evita efeitos colaterais
    estranhos em quem já tinha usado a configuração antes.
    """
    settings = get_settings()
    overrides: dict[str, object] = {}
    if provider:
        overrides["provider"] = provider
    if model:
        overrides["model_name"] = model
    if search:
        overrides["search_backend"] = search
    if temperature is not None:
        overrides["temperature"] = temperature
    return settings.model_copy(update=overrides) if overrides else settings


def _print_step(index: int, agent_name: str, detail: str) -> None:
    """Imprime uma linha de progresso: `[2] Analista` + o que ele fez.

    Não mostramos "2/4" porque o total de passos varia: quando o revisor
    devolve o texto, o redator e o revisor rodam de novo.
    """
    label = AGENT_LABELS.get(agent_name, agent_name)
    header = Text(f"[{index}] ", style="bold cyan")
    header.append(label, style="bold")
    console.print(header)
    console.print(f"    {detail}", style="dim")
    console.print()


# =====================================================================
#  Comando principal: run
# =====================================================================


@app.command()
def run(
    question: Annotated[
        str, typer.Argument(help="O tema que o time deve investigar e escrever sobre.")
    ],
    audience: Annotated[
        str, typer.Option("--audience", "-a", help="Para quem o texto final é escrito.")
    ] = "público geral",
    revisions: Annotated[
        int,
        typer.Option(
            "--revisions",
            "-r",
            help="Reescritas que o revisor pode pedir (0 = padrão do .env, até 5).",
        ),
    ] = 0,
    provider: Annotated[
        str | None, typer.Option("--provider", "-p", help="mock | openai | anthropic")
    ] = None,
    model: Annotated[
        str | None, typer.Option("--model", "-m", help="Nome do modelo (ex.: gpt-4o-mini).")
    ] = None,
    search: Annotated[str | None, typer.Option("--search", help="mock | tavily")] = None,
    temperature: Annotated[
        float | None, typer.Option("--temperature", "-t", help="0 = previsível, 1 = criativo.")
    ] = None,
    out: Annotated[
        Path | None, typer.Option("--out", "-o", help="Salva o texto final em um arquivo .md.")
    ] = None,
    save_json: Annotated[
        Path | None, typer.Option("--json", help="Salva o resultado completo em JSON.")
    ] = None,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Não mostra o texto final no terminal.")
    ] = False,
) -> None:
    """Roda o time de agentes e imprime (ou salva) o texto final.

    Exemplos:

      agent-crew run "Como funciona o protocolo MCP?"

      agent-crew run "IA na educação" --audience "professores" -r 2

      agent-crew run "Panorama de energia solar no Brasil" -p openai -o saida.md
    """
    settings = _apply_overrides(
        provider=provider, model=model, search=search, temperature=temperature
    )

    request = CrewRequest(question=question, audience=audience, max_revisions=revisions)
    result = asyncio.run(_run_and_report(request, settings, quiet=quiet))

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result.markdown, encoding="utf-8")
        console.print(f"Texto salvo em [bold]{out}[/bold]", style="green")

    if save_json:
        save_json.parent.mkdir(parents=True, exist_ok=True)
        save_json.write_text(
            json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        console.print(f"Resultado completo salvo em [bold]{save_json}[/bold]", style="green")


async def _run_and_report(request: CrewRequest, settings: Settings, *, quiet: bool) -> CrewResult:
    """Executa o fluxo mostrando o progresso, e devolve o resultado final."""
    console.print()
    console.print(
        Panel.fit(
            Text(request.question, style="bold"),
            title="[bold cyan]agent-crew[/bold cyan]",
            subtitle=f"provider={settings.provider} · modelo={settings.model_name} · público={request.audience}",
            border_style="cyan",
        )
    )
    console.print()

    state = initial_state(request, settings)

    try:
        # Geradores assíncronos não aceitam `enumerate`, então contamos na mão.
        index = 0
        async for agent_name, snapshot in stream_crew(request, settings=settings):
            index += 1
            state = snapshot
            timeline = snapshot.get("timeline") or []
            detail = timeline[-1] if timeline else ""
            _print_step(index, agent_name, detail)
    except RuntimeError as error:
        # Erros de configuração (chave faltando etc.) merecem mensagem limpa.
        console.print(
            Panel(str(error), title="[bold red]Configuração[/bold red]", border_style="red")
        )
        raise typer.Exit(code=1) from error

    result = result_from_state(state, request)
    _print_summary(result, quiet=quiet)
    return result


def _print_summary(result: CrewResult, *, quiet: bool) -> None:
    """Imprime o parecer do revisor, a timeline e o texto final."""
    review = result.review
    if review:
        cor = "green" if review.approved else "yellow"
        status = "APROVADO" if review.approved else "NÃO APROVADO"
        console.print(
            Panel(
                f"Nota: [bold]{review.score}/10[/bold] · Status: [bold]{status}[/bold]\n"
                f"Reescritas: {result.revisions}\n\n{review.feedback or '(sem comentários)'}",
                title="[bold]Parecer do revisor[/bold]",
                border_style=cor,
            )
        )
        console.print()

    console.print("[bold]Linha do tempo[/bold]", style="dim")
    for linha in result.timeline:
        console.print(f"  • {linha}")
    console.print()

    if not quiet and result.markdown:
        console.print(
            Panel(Markdown(result.markdown), title="[bold]Texto final[/bold]", border_style="cyan")
        )


# =====================================================================
#  Comandos auxiliares
# =====================================================================


@app.command()
def agents() -> None:
    """Lista os agentes do time, na ordem em que trabalham."""
    settings = get_settings()

    # Só precisamos das descrições: o contexto pode ser um dublê.
    from .agents.base import CrewContext
    from .llm import MockLLM
    from .tools.search import MockSearch

    context = CrewContext(settings=settings, llm=MockLLM(), search=MockSearch())
    crew = build_agents(context)

    table = Table(title="Time de agentes", border_style="cyan")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Agente", style="bold")
    table.add_column("Saída (formato Pydantic)")
    table.add_column("Papel")

    for index, name in enumerate(AGENT_SEQUENCE, start=1):
        agent = crew[name]
        table.add_row(str(index), name, agent.output_type.__name__, agent.description)

    console.print()
    console.print(table)
    console.print()
    console.print(
        "[dim]Fluxo: pesquisador → analista → redator → revisor (↺ volta ao redator se reprovar)[/dim]"
    )


@app.command()
def providers() -> None:
    """Mostra os provedores disponíveis e o que está configurado agora."""
    settings = get_settings()

    table = Table(title="Provedores", border_style="cyan")
    table.add_column("Provedor", style="bold")
    table.add_column("Precisa de chave?")
    table.add_column("Status")

    linhas = [
        ("mock", "não", "sempre pronto (conteúdo simulado)"),
        (
            "openai",
            "sim (OPENAI_API_KEY)",
            "configurado" if settings.openai_api_key else "falta a chave",
        ),
        (
            "anthropic",
            "sim (ANTHROPIC_API_KEY)",
            "configurado" if settings.anthropic_api_key else "falta a chave",
        ),
    ]
    for nome, chave, status in linhas:
        marcado = " ← atual" if nome == settings.provider else ""
        cor = "green" if "pronto" in status or "configurado" in status else "yellow"
        table.add_row(nome + marcado, chave, f"[{cor}]{status}[/{cor}]")

    console.print()
    console.print(table)

    busca = settings.search_backend
    pronto = busca == "mock" or bool(settings.tavily_api_key)
    console.print(
        f"\nBusca na web: [bold]{busca}[/bold] ({'pronta' if pronto else 'falta TAVILY_API_KEY'})"
    )
    console.print(
        f"Modelo: [bold]{settings.model_name}[/bold] · temperatura: {settings.temperature}"
    )
    console.print(f"Reescritas permitidas: {settings.max_revisions} · idioma: {settings.language}")
    console.print()


@app.command()
def serve(
    host: Annotated[str, typer.Option("--host", help="Endereço de escuta.")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", help="Porta do servidor.")] = 8000,
    reload: Annotated[
        bool, typer.Option("--reload", help="Recarrega ao salvar arquivos (desenvolvimento).")
    ] = False,
) -> None:
    """Sobe a API HTTP (FastAPI + documentação automática).

    Depois de subir, abra http://127.0.0.1:8000/docs para ver e testar
    todos os endpoints pelo navegador.
    """
    try:
        import uvicorn
    except ImportError as error:  # pragma: no cover
        console.print("[red]uvicorn não instalado. Rode: pip install 'uvicorn[standard]'[/red]")
        raise typer.Exit(code=1) from error

    console.print(
        f"API em [bold]http://{host}:{port}[/bold] — docs em [bold]http://{host}:{port}/docs[/bold]"
    )
    uvicorn.run("agent_crew.api:app", host=host, port=port, reload=reload)


@app.command()
def version() -> None:
    """Mostra a versão do projeto e as versões das bibliotecas principais."""
    import importlib.metadata as md

    console.print(f"[bold]agent-crew[/bold] {__version__}")
    for pacote in ("langgraph", "pydantic-ai", "fastapi", "typer"):
        try:
            console.print(f"  {pacote}: {md.version(pacote)}", style="dim")
        except md.PackageNotFoundError:  # pragma: no cover
            console.print(f"  {pacote}: não instalado", style="dim")


def main() -> None:
    """Ponto de entrada usado pelo comando `agent-crew` do terminal."""
    try:
        app()
    except KeyboardInterrupt:  # Ctrl+C limpo, sem stack trace feio
        console.print("\n[yellow]Interrompido pelo usuário.[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()
