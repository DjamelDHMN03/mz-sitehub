"""
Couche AIProvider (section 67) : abstrait le modèle de langage utilisé,
pour pouvoir changer de fournisseur (Ollama local, ou API externe si une
clé est explicitement fournie — section 68) sans toucher au reste de
l'application (assistant.py, routers/assistant.py).

Priorité absolue : IA LOCALE (Ollama). Aucune clé API externe requise pour
faire fonctionner l'Assistant en V1 — 0 DA (section 68).
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import get_settings


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class AIResponse:
    content: str | None  # texte libre du modèle (jamais utilisé comme source de données factuelle)
    tool_calls: list[ToolCall] = field(default_factory=list)


class AIProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AIResponse: ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...


class OllamaProvider(AIProvider):
    """Fournisseur par défaut — modèle local via Ollama, aucun coût API
    (section 68). Non exécutable dans cet environnement de construction
    (pas d'Ollama qui tourne ici), mais l'implémentation suit exactement
    l'API HTTP documentée d'Ollama (/api/chat, /api/embeddings)."""

    def __init__(self, base_url: str, model: str, embed_model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embed_model = embed_model

    async def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AIResponse:
        payload: dict[str, Any] = {"model": self.model, "messages": messages, "stream": False}
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

        message = data.get("message", {})
        tool_calls = [
            ToolCall(name=tc["function"]["name"], arguments=tc["function"].get("arguments", {}))
            for tc in message.get("tool_calls", [])
        ]
        return AIResponse(content=message.get("content"), tool_calls=tool_calls)

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings", json={"model": self.embed_model, "prompt": text}
            )
            response.raise_for_status()
            return response.json()["embedding"]


class AnthropicProvider(AIProvider):
    """Fournisseur externe optionnel — utilisé UNIQUEMENT si AI_API_KEY est
    explicitement renseignée dans .env (section 68 : jamais activé par défaut,
    jamais de coût API imposé). Squelette prêt, non implémenté tant qu'aucune
    clé réelle n'est fournie — évite d'écrire et de prétendre tester un appel
    réseau qu'on ne peut pas vérifier ici."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def chat(self, messages, tools=None) -> AIResponse:
        raise NotImplementedError(
            "AnthropicProvider non implémenté — à construire au moment où une "
            "clé API est réellement fournie et testable (section 68)"
        )

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider == "ollama":
        return OllamaProvider(settings.ollama_base_url, settings.ollama_model, settings.ollama_embed_model)
    if settings.ai_provider in ("anthropic", "openai"):
        if not settings.ai_api_key:
            raise RuntimeError(
                f"AI_PROVIDER={settings.ai_provider} mais AI_API_KEY n'est pas renseignée dans .env"
            )
        return AnthropicProvider(settings.ai_api_key)
    raise RuntimeError(f"AI_PROVIDER invalide : {settings.ai_provider}")
