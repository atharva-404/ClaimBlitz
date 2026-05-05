from __future__ import annotations

import os
from functools import lru_cache

import google.generativeai as genai
import requests

from utils.json_cleaner import parse_json_response


class LLMClient:
    def __init__(self) -> None:
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()

        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.ollama_model_name = os.getenv("OLLAMA_MODEL", "llama3.1:8b").strip()

        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        self.timeout_seconds = int(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
        self.use_ollama_only = os.getenv("USE_OLLAMA_ONLY", "false").lower() == "true"

        self._gemini_model = None
        if self.gemini_api_key and not self.use_ollama_only:
            genai.configure(api_key=self.gemini_api_key)
            self._gemini_model = genai.GenerativeModel(self.gemini_model_name)

    def call_json(self, prompt: str, max_tokens: int = 1200) -> dict:
        provider_errors: list[str] = []

        if not self.use_ollama_only and self._gemini_model is not None:
            try:
                gemini_raw = self._call_gemini(prompt=prompt, max_tokens=max_tokens)
                return parse_json_response(gemini_raw)
            except Exception as exc:  # pragma: no cover - network/runtime dependent
                provider_errors.append(f"Gemini failed: {exc}")

        try:
            ollama_raw = self._call_ollama(prompt=prompt, max_tokens=max_tokens)
            return parse_json_response(ollama_raw)
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            provider_errors.append(f"Ollama failed: {exc}")

        raise RuntimeError(" | ".join(provider_errors) or "No LLM provider configured")

    def provider_status(self) -> dict:
        return {
            "mode": "ollama_only" if self.use_ollama_only else "gemini_with_ollama_fallback",
            "gemini_configured": bool(self.gemini_api_key),
            "gemini_model": self.gemini_model_name,
            "ollama_base_url": self.ollama_base_url,
            "ollama_model": self.ollama_model_name,
            "ollama_reachable": self._is_ollama_reachable(),
        }

    def _call_gemini(self, prompt: str, max_tokens: int) -> str:
        if self._gemini_model is None:
            raise RuntimeError("Gemini is not configured")

        response = self._gemini_model.generate_content(
            prompt,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": max_tokens,
            },
            request_options={"timeout": self.timeout_seconds},
        )

        try:
            text = response.text
            if text and text.strip():
                return text
        except Exception:
            # Some responses may not expose `.text` directly.
            pass

        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                part_text = getattr(part, "text", None)
                if part_text and part_text.strip():
                    return part_text

        raise RuntimeError("Gemini returned an empty response")

    def _call_ollama(self, prompt: str, max_tokens: int) -> str:
        payload = {
            "model": self.ollama_model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.temperature,
                "num_predict": max_tokens,
            },
        }

        response = requests.post(
            f"{self.ollama_base_url}/api/generate",
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        data = response.json()
        text = str(data.get("response", "")).strip()
        if not text:
            raise RuntimeError("Ollama returned an empty response")

        return text

    def _is_ollama_reachable(self) -> bool:
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=2)
            return response.ok
        except Exception:
            return False


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    return LLMClient()
