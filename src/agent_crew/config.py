"""Configuração do projeto.

Toda configuração vem de variáveis de ambiente, com valores padrão seguros.
Lemos o arquivo `.env` automaticamente (se ele existir), usando pydantic-settings.

Por que fazer assim?
- Segredos (chaves de API) ficam fora do código e fora do Git.
- Quem clonar o repositório só precisa copiar `.env.example` para `.env`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Provedores de LLM suportados.
ProviderName = Literal["mock", "openai", "anthropic"]

# Backends de busca na web suportados.
SearchBackendName = Literal["mock", "tavily"]


class Settings(BaseSettings):
    """Todas as configurações do projeto, carregadas do ambiente/.env."""

    model_config = SettingsConfigDict(
        env_prefix="AGENT_CREW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Qual "cérebro" (LLM) o time vai usar -------------------------
    provider: ProviderName = "mock"
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.2

    # --- Chaves de API (opcionais; só a do provedor escolhido é usada) --
    # SecretStr esconde o valor se alguém imprimir as configurações.
    openai_api_key: SecretStr | None = Field(default=None)
    anthropic_api_key: SecretStr | None = Field(default=None)
    # Alguns provedores compatíveis com OpenAI (ex.: Groq, Together).
    openai_base_url: str | None = Field(default=None)

    # --- Fluxo do time -------------------------------------------------
    max_revisions: int = 1
    language: str = "pt-BR"

    # --- Ferramenta de busca na web ------------------------------------
    search_backend: SearchBackendName = "mock"
    tavily_api_key: SecretStr | None = Field(default=None)
    search_max_results: int = 5

    # ---------------------------------------------------------------
    #  Propriedades calculadas (não vêm do ambiente, são derivadas)
    # ---------------------------------------------------------------

    @property
    def api_key(self) -> str | None:
        """Devolve a chave de API do provedor escolhido, se houver."""
        if self.provider == "openai":
            return self.openai_api_key.get_secret_value() if self.openai_api_key else None
        if self.provider == "anthropic":
            return self.anthropic_api_key.get_secret_value() if self.anthropic_api_key else None
        return None

    def validate_for_run(self) -> None:
        """Dá um erro claro ANTES de rodar, se faltar alguma chave.

        Isso evita a experiência ruim de descobrir o problema no meio do
        processamento, com metade do trabalho já feito.
        """
        if self.provider in ("openai", "anthropic") and not self.api_key:
            var = "OPENAI_API_KEY" if self.provider == "openai" else "ANTHROPIC_API_KEY"
            raise RuntimeError(
                f"O provedor '{self.provider}' precisa da variável {var}.\n"
                f"Opções:\n"
                f"  1) Coloque a chave no arquivo .env  ({var}=sk-...)\n"
                f"  2) Ou rode sem chave nenhuma usando o provedor de demonstração:\n"
                f'     agent-crew run "sua pergunta" --provider mock'
            )
        if self.search_backend == "tavily" and not self.tavily_api_key:
            raise RuntimeError(
                "O backend de busca 'tavily' precisa da variável TAVILY_API_KEY "
                "no arquivo .env (ou use AGENT_CREW_SEARCH_BACKEND=mock)."
            )


def _env_files() -> tuple[str, ...]:
    """Descobre arquivos .env: o do diretório atual e o do projeto."""
    project_root = Path(__file__).resolve().parents[2]
    files: list[str] = []
    for candidate in (Path.cwd() / ".env", project_root / ".env"):
        if candidate.is_file():
            files.append(str(candidate))
    return tuple(files)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devolve a configuração (lida uma única vez e guardada em cache)."""
    return Settings(_env_file=_env_files() or ".env")


def reset_settings_cache() -> None:
    """Limpa o cache. Útil em testes e quando o .env muda em tempo de execução."""
    get_settings.cache_clear()
