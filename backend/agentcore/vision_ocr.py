"""Vision-based OCR for scanned / image-only PDFs — with provider failover.

ClaimBlitz's "OCR Agent" is an LLM that reads *already-extracted* text — it
does not read pixels. Text-layer PDFs (e.g. the synthetic demo claim) extract
fine with PyMuPDF's ``page.get_text()``. Real scanned hospital documents are
images with no text layer, so ``get_text()`` returns nothing.

This module adds a real OCR stage:

- FAST PATH (text layer): if the PDF already has an extractable text layer,
  return it immediately and make NO network calls. Keeps the synthetic demo
  fast and fully offline-capable.
- VISION PATH (scanned): render each page to a PNG with PyMuPDF and transcribe
  it with a vision model. We try, IN ORDER, every OpenAI key in the pool
  (``gpt-4o-mini`` is vision-capable) and finally Google Gemini. If one key is
  dead / rate-limited / out of quota, the next is tried automatically — so a
  live demo never surfaces an OCR auth error.

Each per-page call also retries transient 429/500/503 with backoff. A total
failure raises ``VisionOCRError`` the caller turns into a graceful response
(never a raw 500).
"""

from __future__ import annotations

import base64
import json
import logging
import time
import urllib.error
import urllib.request

from .settings import get_settings

logger = logging.getLogger(__name__)

# A text layer with at least this many stripped characters is considered
# "real" — below it we assume the PDF is a scan and fall back to vision OCR.
_TEXT_LAYER_MIN_CHARS = 100

# Page separator inserted between vision-OCR'd pages so downstream extraction
# can tell page boundaries apart.
_PAGE_SEPARATOR = "\n\n----- PAGE {n} -----\n\n"

_OCR_INSTRUCTION = (
    "You are an OCR engine. Transcribe ALL readable text from this scanned "
    "medical / insurance claim document page exactly as it appears, preserving "
    "labels, table rows, names, dates and amounts. Output plain text only — no "
    "commentary, no markdown, no explanations."
)

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
)


class VisionOCRError(RuntimeError):
    """Raised when vision OCR cannot produce text (unconfigured or all failed)."""


class _EmptyPageError(Exception):
    """Internal: a provider returned no usable text for a page (not fatal)."""


# ---------------------------------------------------------------------------
# OpenAI vision (gpt-4o-mini) — PRIMARY OCR path, uses the key pool
# ---------------------------------------------------------------------------


def _openai_vision_ocr_page(
    png_bytes: bytes, *, api_key: str, model: str, base_url: str,
    max_attempts: int = 4, base_delay: float = 4.0,
) -> str:
    """OCR one page image via an OpenAI-compatible vision chat completion.

    Isolated so tests can monkeypatch it. Raises on hard auth/other failure so
    the caller can fail over to the next key; returns "" on an empty page.
    """
    from openai import OpenAI

    b64 = base64.b64encode(png_bytes).decode()
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=120)
    last_err = ""
    for attempt in range(max_attempts):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _OCR_INSTRUCTION},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{b64}"},
                            },
                        ],
                    }
                ],
                max_tokens=4096,
                temperature=0.0,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            last_err = msg
            # Retry transient conditions; fail fast on auth so we fail over.
            transient = any(s in msg.lower() for s in ("rate limit", "429", "500", "502", "503", "timeout", "overloaded"))
            if transient and attempt < max_attempts - 1:
                time.sleep(base_delay * (attempt + 1))
                continue
            break
    raise VisionOCRError(f"OpenAI vision OCR failed: {last_err[:200]}")


# ---------------------------------------------------------------------------
# Gemini vision — FALLBACK OCR path
# ---------------------------------------------------------------------------


def _gemini_ocr_page(png_bytes: bytes, *, api_key: str, model: str,
                     max_attempts: int = 4, base_delay: float = 6.0) -> str:
    """OCR one page image via Gemini REST, backoff on 503/429/500."""
    b64 = base64.b64encode(png_bytes).decode()
    body = json.dumps(
        {
            "contents": [
                {
                    "parts": [
                        {"text": _OCR_INSTRUCTION},
                        {"inline_data": {"mime_type": "image/png", "data": b64}},
                    ]
                }
            ],
            "generationConfig": {"maxOutputTokens": 8192, "temperature": 0.0},
        }
    ).encode()
    url = _GEMINI_URL.format(model=model, key=api_key)

    last_err = ""
    for attempt in range(max_attempts):
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}
        )
        try:
            resp = urllib.request.urlopen(req, timeout=120)
            return _parse_gemini_text(json.loads(resp.read()))
        except urllib.error.HTTPError as exc:
            code = exc.code
            last_err = f"HTTP {code}"
            if code in (503, 429, 500) and attempt < max_attempts - 1:
                time.sleep(base_delay * (attempt + 1))
                continue
            try:
                last_err = f"HTTP {code}: {exc.read().decode()[:160]}"
            except Exception:  # noqa: BLE001
                pass
            break
        except (urllib.error.URLError, TimeoutError) as exc:
            last_err = str(exc)
            if attempt < max_attempts - 1:
                time.sleep(base_delay * (attempt + 1))
                continue
            break
        except json.JSONDecodeError as exc:
            last_err = f"invalid JSON: {exc}"
            break
        except _EmptyPageError:
            return ""
    raise VisionOCRError(f"Gemini OCR failed: {last_err}")


def _parse_gemini_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        raise _EmptyPageError("no candidates")
    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    texts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")]
    if not texts:
        raise _EmptyPageError("no text parts")
    return "".join(texts)


# ---------------------------------------------------------------------------
# Provider pool: ordered list of (label, callable) to try per page
# ---------------------------------------------------------------------------


def _build_ocr_providers(settings) -> list[tuple[str, object]]:
    """Ordered OCR providers for failover: OpenAI keys first, then Gemini."""
    providers: list[tuple[str, object]] = []
    model = settings.openai_model or "gpt-4o-mini"
    base = settings.openai_base_url or "https://api.openai.com/v1"
    # Only genuine OpenAI endpoints are vision-capable here (Groq gpt-oss isn't).
    if "openai.com" in base:
        for i, key in enumerate(settings.openai_key_pool):
            label = "openai-vision" if i == 0 else f"openai-vision#{i + 1}"
            providers.append((
                label,
                lambda png, k=key: _openai_vision_ocr_page(
                    png, api_key=k, model=model, base_url=base
                ),
            ))
    # Gemini fallback (if a key is set).
    if settings.gemini_api_key:
        providers.append((
            "gemini-vision",
            lambda png: _gemini_ocr_page(
                png, api_key=settings.gemini_api_key, model=settings.gemini_model
            ),
        ))
    return providers


def _ocr_page_with_failover(png_bytes: bytes, providers) -> tuple[str, str]:
    """Try each OCR provider in order; return (text, provider_label).

    Raises VisionOCRError only if ALL providers fail for this page.
    """
    errors = []
    for label, fn in providers:
        try:
            return fn(png_bytes), label
        except VisionOCRError as exc:
            errors.append(f"{label}: {exc}")
            logger.warning("OCR provider '%s' failed, trying next: %s", label, str(exc)[:120])
    raise VisionOCRError("all OCR providers failed: " + " | ".join(errors))


def extract_text_from_pdf(pdf_bytes: bytes, *, max_pages: int | None = None) -> tuple[str, dict]:
    """Extract text from PDF bytes: text layer if present, else vision OCR.

    Returns ``(text, meta)``:
      - text layer: ``{"method": "text_layer", "pages_processed": N}``
      - vision OCR: ``{"method": "vision_ocr", "provider": ..., "pages_processed": N,
                       "pages_total": M, "truncated": bool}``
    Raises ``VisionOCRError`` only if the vision path is required and every
    configured provider/key fails.
    """
    import fitz  # PyMuPDF (already a dependency)

    settings = get_settings()
    if max_pages is None:
        max_pages = settings.vision_ocr_max_pages

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_total = doc.page_count

    # ---- FAST PATH: text layer -------------------------------------------
    text_layer = "".join(page.get_text() for page in doc)
    if len(text_layer.strip()) >= _TEXT_LAYER_MIN_CHARS:
        doc.close()
        return text_layer, {"method": "text_layer", "pages_processed": pages_total}

    # ---- VISION PATH: render pages, OCR with provider failover -----------
    providers = _build_ocr_providers(settings)
    if not providers:
        doc.close()
        raise VisionOCRError(
            "Scanned document has no text layer and no vision OCR provider is "
            "configured (set OPENAI_API_KEY/OPENAI_API_KEYS or GEMINI_API_KEY)."
        )

    n_to_process = min(pages_total, max_pages) if max_pages else pages_total
    truncated = n_to_process < pages_total

    parts: list[str] = []
    non_empty_pages = 0
    used_provider = ""
    for i in range(n_to_process):
        pix = doc[i].get_pixmap(dpi=200)
        png_bytes = pix.tobytes("png")
        try:
            page_text, used_provider = _ocr_page_with_failover(png_bytes, providers)
        except VisionOCRError:
            doc.close()
            raise
        if page_text.strip():
            non_empty_pages += 1
        parts.append(_PAGE_SEPARATOR.format(n=i + 1) + page_text)

    doc.close()
    full_text = "".join(parts)

    if non_empty_pages == 0:
        raise VisionOCRError(
            f"Vision OCR produced no text across {n_to_process} page(s)."
        )
    meta = {
        "method": "vision_ocr",
        "provider": used_provider,
        "pages_processed": n_to_process,
        "pages_total": pages_total,
        "truncated": truncated,
    }
    logger.info(
        "Vision OCR via %s: %d/%d pages, %d chars",
        used_provider, n_to_process, pages_total, len(full_text),
    )
    return full_text, meta


__all__ = ["extract_text_from_pdf", "VisionOCRError"]
