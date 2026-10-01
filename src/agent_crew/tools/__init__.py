"""Ferramentas que os agentes podem usar (hoje: busca na web)."""

from .search import SearchHit, SearchTool, build_search_tool

__all__ = ["SearchHit", "SearchTool", "build_search_tool"]
