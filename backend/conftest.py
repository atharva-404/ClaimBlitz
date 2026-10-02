"""Shared test fixtures for the ClaimBlitz backend.

Backend tests must be deterministic and offline — no test may hit a real LLM
provider or a live network endpoint. The ``offline_llm`` fixture below is
autouse so that, by default, every test runs with ``AsyncLLMClient.call_json``
raising ``LLMAllProvidersFailedError`` immediately (no OpenAI/Ollama network
calls, no retry/back-off waits). This exercises the Supervisor's real
resilience path (ABSTAIN synthesis, REVIEW routing) quickly instead of waiting
on dead-connection retries. Tests that need scripted LLM responses can
monkeypatch ``call_json`` themselves within the test.
"""

import pytest
from fastapi.testclient import TestClient

from agentcore.api.app import create_app
from agentcore.llm import AsyncLLMClient, LLMAllProvidersFailedError


@pytest.fixture(autouse=True)
def offline_llm(monkeypatch):
    """Prevent any real LLM/network call during tests (deterministic + fast)."""

    async def _no_network(self, prompt, *, max_tokens=1200):
        raise LLMAllProvidersFailedError({"test": "LLM disabled under pytest"})

    monkeypatch.setattr(AsyncLLMClient, "call_json", _no_network, raising=True)
    return _no_network


@pytest.fixture
def test_client():
    """Provides a TestClient against the new multi-agent API."""
    app = create_app()
    return TestClient(app)
