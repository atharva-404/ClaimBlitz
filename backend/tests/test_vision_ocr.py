"""Offline tests for the vision OCR stage (no live network calls).

The per-page OCR calls (``_openai_vision_ocr_page`` / ``_gemini_ocr_page``) are
isolated functions, so these tests monkeypatch them and the settings accessor
to exercise the text-layer fast path, the OpenAI->Gemini provider failover,
the page cap, and the no-provider error — all without touching the network.
"""

from __future__ import annotations

import fitz  # PyMuPDF
import pytest

from agentcore import vision_ocr
from agentcore.vision_ocr import VisionOCRError, extract_text_from_pdf


def _pdf_with_text(text: str) -> bytes:
    """Build a 1-page PDF that has a real text layer.

    Writes each whitespace-split chunk on its own line so nothing is clipped at
    the page margin (insert_text does not wrap), guaranteeing the full text is
    recoverable via get_text().
    """
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in text.split("  "):
        page.insert_text((72, y), line.strip(), fontsize=11)
        y += 16
    data = doc.tobytes()
    doc.close()
    return data


def _blank_image_pdf(pages: int = 1) -> bytes:
    """Build a PDF with pages that have NO text layer (blank pages)."""
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()  # empty page -> get_text() returns ""
    data = doc.tobytes()
    doc.close()
    return data


def test_text_layer_fast_path_makes_no_gemini_call(monkeypatch):
    """A PDF with a real text layer returns it without any vision call."""
    called = {"n": 0}

    def _should_not_be_called(*args, **kwargs):
        called["n"] += 1
        return "SHOULD NOT HAPPEN"

    monkeypatch.setattr(vision_ocr, "_gemini_ocr_page", _should_not_be_called)

    # Double-spaces mark line breaks for the test PDF writer (no clipping).
    body = (
        "MEDICAL CLAIM FORM  Patient Name: Test Person  Diagnosis: J18.9  "
        "Procedure: office visit  Amount: 48760  Provider: Demo Hospital  "
        "Policy Number: DEMO-123  Service Date: 2026-01-01  Status: submitted"
    )
    pdf = _pdf_with_text(body)
    text, meta = extract_text_from_pdf(pdf)

    assert "Test Person" in text
    assert meta["method"] == "text_layer"
    assert called["n"] == 0


class _Settings:
    """Minimal settings stub matching what vision_ocr reads."""

    def __init__(self, *, openai_keys=(), gemini_key="", max_pages=6,
                 base_url="https://api.openai.com/v1", model="gpt-4o-mini",
                 gemini_model="gemini-3.8-flash"):
        self._pool = list(openai_keys)
        self.gemini_api_key = gemini_key
        self.gemini_model = gemini_model
        self.openai_model = model
        self.openai_base_url = base_url
        self.vision_ocr_max_pages = max_pages

    @property
    def openai_key_pool(self):
        return self._pool


def test_vision_path_used_when_no_text_layer(monkeypatch):
    """A no-text PDF routes to the vision path via OpenAI and returns text."""
    monkeypatch.setattr(
        vision_ocr, "get_settings",
        lambda: _Settings(openai_keys=["k1"]),
    )
    monkeypatch.setattr(
        vision_ocr, "_openai_vision_ocr_page",
        lambda png, **kw: "OCR TEXT: ANIL PATIL RUBY HALL CLINIC STAR HEALTH 314754",
    )

    pdf = _blank_image_pdf(pages=1)
    text, meta = extract_text_from_pdf(pdf)

    assert "ANIL PATIL" in text
    assert meta["method"] == "vision_ocr"
    assert meta["pages_processed"] == 1
    assert meta["provider"] == "openai-vision"


def test_failover_to_second_key(monkeypatch):
    """A dead first key fails over to the second key in the pool."""
    monkeypatch.setattr(
        vision_ocr, "get_settings",
        lambda: _Settings(openai_keys=["dead", "good"]),
    )

    def _ocr(png, *, api_key, **kw):
        if api_key == "dead":
            raise VisionOCRError("invalid key 401")
        return "RECOVERED via second key"

    monkeypatch.setattr(vision_ocr, "_openai_vision_ocr_page", _ocr)

    pdf = _blank_image_pdf(pages=1)
    text, meta = extract_text_from_pdf(pdf)
    assert "RECOVERED via second key" in text
    assert meta["provider"] == "openai-vision#2"


def test_failover_openai_to_gemini(monkeypatch):
    """All OpenAI keys dead -> falls over to Gemini."""
    monkeypatch.setattr(
        vision_ocr, "get_settings",
        lambda: _Settings(openai_keys=["dead"], gemini_key="gkey"),
    )
    monkeypatch.setattr(
        vision_ocr, "_openai_vision_ocr_page",
        lambda png, **kw: (_ for _ in ()).throw(VisionOCRError("all openai dead")),
    )
    monkeypatch.setattr(
        vision_ocr, "_gemini_ocr_page",
        lambda png, **kw: "GEMINI OCR TEXT",
    )

    pdf = _blank_image_pdf(pages=1)
    text, meta = extract_text_from_pdf(pdf)
    assert "GEMINI OCR TEXT" in text
    assert meta["provider"] == "gemini-vision"


def test_page_cap_truncates(monkeypatch):
    """vision_ocr_max_pages limits how many pages are OCR'd."""
    monkeypatch.setattr(
        vision_ocr, "get_settings",
        lambda: _Settings(openai_keys=["k1"], max_pages=2),
    )
    calls = {"n": 0}

    def _ocr(png, **kw):
        calls["n"] += 1
        return f"page{calls['n']}"

    monkeypatch.setattr(vision_ocr, "_openai_vision_ocr_page", _ocr)

    pdf = _blank_image_pdf(pages=5)
    text, meta = extract_text_from_pdf(pdf)

    assert calls["n"] == 2
    assert meta["pages_processed"] == 2
    assert meta["pages_total"] == 5
    assert meta["truncated"] is True


def test_no_provider_configured_raises(monkeypatch):
    """A scanned PDF with no OpenAI and no Gemini key raises VisionOCRError."""
    monkeypatch.setattr(
        vision_ocr, "get_settings",
        lambda: _Settings(openai_keys=[], gemini_key=""),
    )
    pdf = _blank_image_pdf(pages=1)
    with pytest.raises(VisionOCRError):
        extract_text_from_pdf(pdf)


def test_gemini_retry_then_success(monkeypatch):
    """The page OCR retries on 503 then succeeds on a later attempt."""
    import urllib.error

    attempts = {"n": 0}

    class _FakeResp:
        def read(self):
            import json
            return json.dumps(
                {"candidates": [{"content": {"parts": [{"text": "RECOVERED TEXT"}]}}]}
            ).encode()

    def _fake_urlopen(req, timeout=90):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise urllib.error.HTTPError(req.full_url, 503, "high demand", {}, None)
        return _FakeResp()

    monkeypatch.setattr(vision_ocr.urllib.request, "urlopen", _fake_urlopen)
    # Avoid real sleeping during backoff.
    monkeypatch.setattr(vision_ocr.time, "sleep", lambda s: None)

    text = vision_ocr._gemini_ocr_page(
        b"fakepng", api_key="k", model="gemini-3.8-flash", base_delay=0.0
    )
    assert text == "RECOVERED TEXT"
    assert attempts["n"] == 2


def test_gemini_all_503_raises(monkeypatch):
    """Persistent 503s exhaust retries and raise VisionOCRError."""
    import urllib.error

    def _always_503(req, timeout=90):
        raise urllib.error.HTTPError(req.full_url, 503, "high demand", {}, None)

    monkeypatch.setattr(vision_ocr.urllib.request, "urlopen", _always_503)
    monkeypatch.setattr(vision_ocr.time, "sleep", lambda s: None)

    with pytest.raises(VisionOCRError):
        vision_ocr._gemini_ocr_page(
            b"fakepng", api_key="k", model="gemini-3.8-flash",
            max_attempts=3, base_delay=0.0,
        )
