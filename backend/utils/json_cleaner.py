from __future__ import annotations

import json
import re
from json import JSONDecodeError
from typing import Any


_CODE_BLOCK_RE = re.compile(r"^```(?:json)?\s*|\s*```$", flags=re.IGNORECASE | re.MULTILINE)


def strip_code_fences(raw_text: str) -> str:
    return _CODE_BLOCK_RE.sub("", raw_text.strip()).strip()


def _extract_first_json_object(raw_text: str) -> str:
    start = raw_text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model response")

    depth = 0
    in_string = False
    escaped = False

    for idx in range(start, len(raw_text)):
        ch = raw_text[idx]

        if escaped:
            escaped = False
            continue

        if ch == "\\":
            escaped = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return raw_text[start : idx + 1]

    # Truncated response (model cut off before closing). Best-effort repair:
    # close any open string and balance the remaining braces so a nearly
    # complete object is still usable instead of being discarded entirely.
    return _repair_truncated_json(raw_text, start)


def _repair_truncated_json(raw_text: str, start: int) -> str:
    """Close an unbalanced/truncated JSON object as best we can."""
    frag = raw_text[start:]
    depth = 0
    in_string = False
    escaped = False
    for ch in frag:
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1

    repaired = frag
    # Drop a trailing partial token after the last complete comma/brace so the
    # closing braces attach to valid content.
    if in_string:
        repaired += '"'
    # Trim a dangling trailing comma or colon that would make closing invalid.
    repaired = repaired.rstrip()
    while repaired and repaired[-1] in ",:":
        repaired = repaired[:-1].rstrip()
    repaired += "}" * max(depth, 0)
    return repaired


def parse_json_response(raw_text: str) -> dict[str, Any]:
    cleaned = strip_code_fences(raw_text)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except JSONDecodeError:
        pass

    extracted = _extract_first_json_object(cleaned)
    try:
        parsed = json.loads(extracted)
    except JSONDecodeError:
        # Last-ditch: strip any trailing partial key/value and retry.
        parsed = json.loads(_truncate_to_last_complete(extracted))
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object response")
    return parsed


def _truncate_to_last_complete(text: str) -> str:
    """Cut a repaired object back to its last complete value + close braces."""
    # Find the last closing brace and keep up to there; if none, give up to {}.
    last = text.rfind("}")
    if last != -1:
        candidate = text[: last + 1]
        try:
            json.loads(candidate)
            return candidate
        except JSONDecodeError:
            pass
    return "{}"
