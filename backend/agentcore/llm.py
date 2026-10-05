"""Async LLM client for the agentcore multi-agent system.

Behavior:
- Primary provider: OpenAI ChatGPT (via official openai SDK, async).
- Fallback provider: local Ollama (``format: json``), for offline dev.
- Each provider call is retried with exponential backoff (via ``tenacity``)
  on transient failures (timeouts, connection errors, 429/5xx).
- Every call returns an ``LLMResult`` carrying which provider/model actually
  served the request and how long it took.

For embeddings (used by Pinecone memory), OpenAI's text-embedding-3-small
is used (1536 dimensions by default).
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

_BACKEND_ROOT = str(Path(__file__).resolve().parent.parent)
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from utils.json_cleaner import parse_json_response  # noqa: E402

from .settings import AgentCoreSettings, get_settings  # noqa: E402

logger = logging.getLogger(__name__)


class LLMProviderError(RuntimeError):
    """A single provider failed to produce a usable response."""


class LLMAllProvidersFailedError(RuntimeError):
    """Every configured provider failed."""

    def __init__(self, errors: dict[str, str]) -> None:
        self.errors = errors
        summary = " | ".join(f"{name}: {msg}" for name, msg in errors.items())
        super().__init__(summary or "No LLM provider configured")


@dataclass(frozen=True)
class LLMResult:
    parsed: dict[str, Any]
    raw_text: str
    provider: str
    model: str
    latency_ms: float


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TimeoutException | httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    if isinstance(exc, Exception) and "rate_limit" in str(exc).lower():
        return True
    return False


class OpenAIProvider:
    """Async ChatGPT provider via the official openai SDK."""

    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    @property
    def model(self) -> str:
        return self._model

    async def generate(self, prompt: str, *, temperature: float, max_tokens: int, timeout: float) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url, timeout=timeout)
        try:
            # Enable native JSON mode ONLY for genuine OpenAI endpoints — their
            # implementation is reliable and guarantees valid JSON. We do NOT
            # use it on Groq, whose strict server-side validation hard-rejects a
            # response ("json_validate_failed", empty content) on the slightest
            # malformation from a reasoning model. For non-OpenAI we rely on the
            # system-prompt instruction + tolerant ``parse_json_response``.
            kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a precise assistant. Respond with ONLY a "
                            "single valid JSON object — no markdown fences, no "
                            "prose before or after."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if "openai.com" in (self._base_url or ""):
                kwargs["response_format"] = {"type": "json_object"}
            response = await client.chat.completions.create(**kwargs)
            text = response.choices[0].message.content or ""
            if not text.strip():
                raise LLMProviderError("OpenAI returned an empty response")
            return text.strip()
        finally:
            await client.close()

    async def embed_batch(self, texts: list[str], *, embedding_model: str, timeout: float) -> list[list[float]]:
        """Embed texts via OpenAI embeddings endpoint."""
        from openai import AsyncOpenAI

        if not texts:
            return []

        client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url, timeout=timeout)
        try:
            response = await client.embeddings.create(
                model=embedding_model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        finally:
            await client.close()


class OllamaProvider:
    """Thin async wrapper around a local Ollama endpoint."""

    def __init__(self, client: httpx.AsyncClient, base_url: str, model: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    async def generate(self, prompt: str, *, temperature: float, max_tokens: int, timeout: float) -> str:
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        response = await self._client.post(
            f"{self._base_url}/api/generate",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        text = str(data.get("response", "")).strip()
        if not text:
            raise LLMProviderError("Ollama returned an empty response")
        return text

    async def is_reachable(self) -> bool:
        try:
            response = await self._client.get(f"{self._base_url}/api/tags", timeout=2.0)
            return response.is_success
        except Exception:
            return False


class AsyncLLMClient:
    """OpenAI-primary, Ollama-fallback async client with per-provider retry."""

    def __init__(self, settings: AgentCoreSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._http = httpx.AsyncClient()

        # Build an ordered pool of providers for failover. Each pooled OpenAI
        # key becomes its own provider; if one fails (invalid/quota/rate limit)
        # the next is tried automatically. Groq is appended as a last resort,
        # then Ollama. This is what keeps the demo from ever showing an error.
        self._providers: list[tuple[str, OpenAIProvider | OllamaProvider]] = []

        if not self._settings.use_ollama_only:
            pool = self._settings.openai_key_pool
            for i, key in enumerate(pool):
                label = "openai" if i == 0 else f"openai#{i + 1}"
                self._providers.append((
                    label,
                    OpenAIProvider(
                        api_key=key,
                        model=self._settings.openai_model,
                        base_url=self._settings.openai_base_url,
                    ),
                ))
            # Groq last-resort (OpenAI-compatible), only if a key is configured.
            if self._settings.groq_api_key:
                self._providers.append((
                    "groq",
                    OpenAIProvider(
                        api_key=self._settings.groq_api_key,
                        model=self._settings.groq_model,
                        base_url=self._settings.groq_base_url,
                    ),
                ))

        self._ollama = OllamaProvider(
            self._http,
            base_url=self._settings.ollama_base_url,
            model=self._settings.ollama_model,
        )
        # Ollama is the final fallback (works offline if a model is pulled).
        self._providers.append(("ollama", self._ollama))

        # Back-compat: first OpenAI provider (used by embeddings).
        self._openai = next(
            (p for name, p in self._providers if name.startswith("openai")),
            None,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncLLMClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def call_json(self, prompt: str, *, max_tokens: int = 1200) -> LLMResult:
        """Get a structured JSON response, trying each pooled provider in order.

        Walks the provider pool (OpenAI key #1, key #2, ..., Groq, Ollama) and
        returns the first success. Only raises if EVERY provider fails — so a
        single dead/expired/quota-exhausted key is handled transparently.
        """
        errors: dict[str, str] = {}
        for name, provider in self._providers:
            try:
                return await self._call_provider(name, provider, prompt, max_tokens)
            except Exception as exc:  # noqa: BLE001 - try the next provider
                errors[name] = str(exc)
                logger.warning("LLM provider '%s' failed, trying next: %s", name, str(exc)[:120])
        raise LLMAllProvidersFailedError(errors)

    async def _call_provider(
        self, name: str, provider: OpenAIProvider | OllamaProvider, prompt: str, max_tokens: int
    ) -> LLMResult:
        settings = self._settings

        @retry(
            reraise=True,
            stop=stop_after_attempt(settings.llm_max_retries + 1),
            wait=wait_exponential(multiplier=1, max=15),
            retry=retry_if_exception(_is_retryable),
        )
        async def _attempt() -> str:
            return await provider.generate(
                prompt,
                temperature=settings.llm_temperature,
                max_tokens=max_tokens,
                timeout=settings.llm_timeout_seconds,
            )

        # Try the call, and if the model returns JSON we cannot parse/repair,
        # retry the whole call a couple of times — gpt-oss occasionally
        # truncates or malforms a response but succeeds on a fresh attempt.
        start = time.perf_counter()
        raw_text = ""
        parsed: dict[str, Any] | None = None
        last_parse_err: Exception | None = None
        for _parse_try in range(3):
            try:
                raw_text = await _attempt()
                parsed = parse_json_response(raw_text)
                break
            except LLMProviderError as exc:
                # Empty response (reasoning model spent its budget thinking) —
                # retry a fresh call.
                last_parse_err = exc
                continue
            except Exception as exc:  # noqa: BLE001 - retry on any parse failure
                last_parse_err = exc
                continue
        latency_ms = (time.perf_counter() - start) * 1000

        if parsed is None:
            raise LLMProviderError(
                f"{name} returned no usable JSON after retries: {last_parse_err}"
            )

        return LLMResult(
            parsed=parsed,
            raw_text=raw_text,
            provider=name,
            model=provider.model,
            latency_ms=latency_ms,
        )

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed texts via OpenAI embeddings API."""
        if self._openai is None:
            raise LLMProviderError("OpenAI is not configured; embeddings require OPENAI_API_KEY")

        settings = self._settings

        @retry(
            reraise=True,
            stop=stop_after_attempt(settings.llm_max_retries + 1),
            wait=wait_exponential(multiplier=1, max=15),
            retry=retry_if_exception(_is_retryable),
        )
        async def _attempt() -> list[list[float]]:
            return await self._openai.embed_batch(  # type: ignore[union-attr]
                texts,
                embedding_model=settings.embedding_model,
                timeout=settings.llm_timeout_seconds,
            )

        return await _attempt()

    async def provider_status(self) -> dict[str, Any]:
        return {
            "mode": "ollama_only" if self._settings.use_ollama_only else "openai_with_ollama_fallback",
            "openai_configured": self._openai is not None,
            "openai_model": self._settings.openai_model,
            "ollama_base_url": self._settings.ollama_base_url,
            "ollama_model": self._settings.ollama_model,
            "ollama_reachable": await self._ollama.is_reachable(),
        }


__all__ = [
    "AsyncLLMClient",
    "LLMResult",
    "LLMProviderError",
    "LLMAllProvidersFailedError",
]
