"""A camada de LLM: quem realmente "pensa" no lugar dos agentes.

Por que separar isso em um arquivo só?

  1. Os agentes não sabem (nem precisam saber) qual modelo está por trás.
  2. Dá pra trocar de provedor mudando uma linha no .env.
  3. Dá pra testar tudo sem internet, sem chave de API e sem gastar dinheiro.

Existem duas implementações:

  - PydanticAILLM -> usa modelos de verdade (OpenAI, Anthropic) via Pydantic AI.
  - MockLLM       -> "dublê" determinístico, para testes e para o modo demo.

O detalhe mais importante: o método `complete` recebe um `output_type`
(uma classe Pydantic). O Pydantic AI usa isso para OBRIGAR o modelo a
responder naquele formato exato. Se vier errado, ele repete automaticamente.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

from .config import Settings
from .schemas import Analysis, Draft, Finding, ResearchBrief, ReviewVerdict

# T = "algum tipo de BaseModel". O TypeVar serve para o editor entender
# que se você pede `Draft`, o retorno é `Draft` (e não um BaseModel genérico).
T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class LLMUsage:
    """Quanto um agente gastou em uma chamada (útil para acompanhar custo)."""

    input_tokens: int = 0
    output_tokens: int = 0


@runtime_checkable
class LLM(Protocol):
    """O contrato que qualquer "cérebro" precisa cumprir.

    Enquanto um objeto tiver um método `complete` com esta assinatura, ele
    pode ser usado pelo time. É isso que permite trocar mock <-> OpenAI sem
    mudar mais nada no código.
    """

    async def complete(
        self,
        *,
        system: str,
        user: str,
        output_type: type[T],
        agent_name: str,
    ) -> T:
        """Recebe instruções + tarefa, devolve um objeto do tipo pedido."""
        ...


# =====================================================================
#  Implementação de verdade: Pydantic AI
# =====================================================================


class PydanticAILLM:
    """Fala com LLMs reais (OpenAI, Anthropic) usando o Pydantic AI.

    O Pydantic AI cuida de: montar a chamada, validar a resposta contra o
    `output_type`, e reenviar ao modelo se a validação falhar (retries).
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model = _build_pydantic_ai_model(settings)

    async def complete(
        self,
        *,
        system: str,
        user: str,
        output_type: type[T],
        agent_name: str,
    ) -> T:
        # Importamos aqui dentro para que o projeto funcione mesmo se alguém
        # instalar uma versão sem os providers de nuvem.
        from pydantic_ai import Agent
        from pydantic_ai.settings import ModelSettings

        agent: Agent[None, T] = Agent(
            model=self._model,
            output_type=output_type,
            name=agent_name,
            retries=2,
            model_settings=ModelSettings(temperature=self.settings.temperature),
        )

        # `instructions` é o "system prompt": as regras de comportamento.
        # `user` é a tarefa concreta daquela etapa.
        result = await agent.run(user, instructions=system)
        return result.output


def _build_pydantic_ai_model(settings: Settings) -> Any:
    """Cria o objeto de modelo do Pydantic AI conforme o provedor escolhido."""
    if settings.provider == "openai":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        provider = OpenAIProvider(
            api_key=settings.api_key,
            base_url=settings.openai_base_url,
        )
        return OpenAIChatModel(settings.model_name, provider=provider)

    if settings.provider == "anthropic":
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider(api_key=settings.api_key)
        return AnthropicModel(settings.model_name, provider=provider)

    raise ValueError(f"Provedor desconhecido: {settings.provider!r}. Use 'openai' ou 'anthropic'.")


# =====================================================================
#  Implementação de demonstração: MockLLM
# =====================================================================


class MockLLM:
    """ "Dublê" de LLM: não chama a internet e não gasta nada.

    Para que serve?
      - Testes automatizados rápidos e determinísticos.
      - Modo demo: você clona o repositório, roda, e vê o fluxo funcionando
        sem ter nenhuma chave de API.
      - Desenvolvimento da orquestração: você mexe no grafo sem pagar por
        chamadas de modelo.

    Repare que o conteúdo gerado é claramente marcado como simulado — de
    propósito. Nada aqui se passa por uma resposta de IA de verdade.

    O primeiro parecer do revisor é sempre uma REPROVAÇÃO. Assim você
    consegue ver o ciclo "redator -> revisor -> redator" acontecendo.
    """

    def __init__(self, *, critical_reviewer: bool = True) -> None:
        self._critical_reviewer = critical_reviewer
        self._verdicts = 0

    async def complete(
        self,
        *,
        system: str,
        user: str,
        output_type: type[T],
        agent_name: str,
    ) -> T:
        builder = _MOCK_BUILDERS.get(output_type)
        if builder is None:
            raise NotImplementedError(f"O MockLLM não sabe simular o tipo {output_type.__name__}.")

        snippet = _first_line(user)
        result = builder(snippet)

        # Comportamento especial do revisor: reprova na primeira vez.
        if isinstance(result, ReviewVerdict) and self._critical_reviewer:
            self._verdicts += 1
            if self._verdicts == 1:
                return output_type.model_validate(
                    {
                        **result.model_dump(),
                        "approved": False,
                        "score": 6,
                        "issues": ["[SIMULADO] Falta uma seção de exemplos práticos."],
                        "feedback": "[SIMULADO] Acrescente pelo menos um exemplo concreto.",
                    }
                )

        return result


# Prefixos que os agentes usam na primeira linha do prompt.
_TOPIC_PREFIXES = ("Tema a investigar:", "Tema original:", "Tema:")


def _first_line(text: str, limit: int = 160) -> str:
    """Pega a primeira linha não vazia do prompt, para o mock "ecoar" a tarefa.

    Também remove rótulos como "Tema:" para que o texto simulado fique limpo.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        for prefix in _TOPIC_PREFIXES:
            if stripped.startswith(prefix):
                stripped = stripped[len(prefix) :].strip()
                break
        return stripped[:limit]
    return "(tarefa vazia)"


def _mock_brief(topic: str) -> ResearchBrief:
    return ResearchBrief(
        question=topic,
        findings=[
            Finding(
                title="[SIMULADO] Achado de exemplo nº 1",
                summary=(
                    "Conteúdo de demonstração gerado localmente, sem chamar nenhum "
                    "modelo de IA. Serve para você ver o fluxo de ponta a ponta."
                ),
                source="mock://fonte-1",
                confidence=0.6,
            ),
            Finding(
                title="[SIMULADO] Achado de exemplo nº 2",
                summary="Outro achado fictício, apenas para preencher a estrutura de dados.",
                source="mock://fonte-2",
                confidence=0.4,
            ),
        ],
        open_questions=["[SIMULADO] Que dados reais confirmariam isto?"],
    )


def _mock_analysis(topic: str) -> Analysis:
    return Analysis(
        key_points=[
            "[SIMULADO] O fluxo entre os quatro agentes funcionou.",
            "[SIMULADO] Os dados estruturados atravessaram as etapas sem erro.",
        ],
        risks=["[SIMULADO] O conteúdo só é confiável quando `provider` é um LLM de verdade."],
        recommendation="[SIMULADO] Rode com --provider openai para gerar conteúdo real.",
        confidence=0.5,
    )


def _mock_draft(topic: str) -> Draft:
    markdown = (
        "# [SIMULADO] Texto de demonstração\n\n"
        f"**Tema pedido:** {topic}\n\n"
        "Este texto foi produzido pelo modo de demonstração (`provider=mock`).\n"
        "Ele existe para provar que a orquestração funciona de ponta a ponta:\n"
        "pesquisa -> análise -> redação -> revisão.\n\n"
        "## Como ver conteúdo de verdade\n\n"
        "Configure uma chave de API no arquivo `.env` e rode novamente com\n"
        "`--provider openai` (ou `--provider anthropic`).\n"
    )
    return Draft(
        title="[SIMULADO] Texto de demonstração",
        markdown=markdown,
        word_count=len(markdown.split()),
    )


def _mock_verdict(topic: str) -> ReviewVerdict:
    return ReviewVerdict(
        approved=True,
        score=9,
        issues=[],
        feedback="[SIMULADO] Texto aprovado pelo revisor de demonstração.",
    )


# Dicionário que liga "tipo pedido" -> "função que fabrica um exemplo".
_MOCK_BUILDERS: dict[type[BaseModel], Any] = {
    ResearchBrief: _mock_brief,
    Analysis: _mock_analysis,
    Draft: _mock_draft,
    ReviewVerdict: _mock_verdict,
}


# =====================================================================
#  Fábrica: decide qual implementação usar
# =====================================================================


def build_llm(settings: Settings) -> LLM:
    """Devolve o LLM certo para a configuração atual."""
    if settings.provider == "mock":
        return MockLLM()
    return PydanticAILLM(settings)
