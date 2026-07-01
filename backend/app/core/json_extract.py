"""
Robust JSON extraction from LLM responses.

Handles common LLM quirks: trailing commas, markdown fences,
unescaped characters, multiple JSON objects, prose mixed with JSON.
"""

from __future__ import annotations

import json
import re
from typing import Any


def _try_decode(text: str, pos: int) -> tuple[Any, int] | None:
    """Try to JSON-decode starting at pos. Returns (obj, end_pos) or None."""
    try:
        decoder = json.JSONDecoder()
        obj, end = decoder.raw_decode(text, pos)
        return obj, end
    except json.JSONDecodeError:
        return None


def _fix_json(text: str) -> str:
    """Apply common JSON fixes for LLM output quirks."""
    fixed = text
    fixed = re.sub(r",\s*([}\]])", r"\1", fixed)
    fixed = re.sub(r"//[^\n]*", "", fixed)
    return fixed


def extract_json(text: str) -> dict[str, Any] | None:
    """
    Extract the first valid JSON object from an LLM response.

    Strategy:
    1. Strip markdown code fences
    2. Try raw_decode from first '{'
    3. Apply fixes (trailing commas, comments) and retry from first '{'
    4. Brace-count extraction (string-aware) for the outermost object
    5. Last resort: scan inner objects

    Returns None if no valid JSON object found.
    """
    if not text:
        return None

    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```", "", cleaned)

    first_brace = cleaned.find("{")
    if first_brace == -1:
        return None

    # Attempt 1: raw parse from first '{'
    try:
        obj, _ = json.JSONDecoder().raw_decode(cleaned, first_brace)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Attempt 2: fix common issues and retry from first '{'
    fixed = _fix_json(cleaned)
    result = _try_decode(fixed, first_brace)
    if result is not None and isinstance(result[0], dict):
        return result[0]

    # Attempt 3: brace-counting extraction (string-aware)
    depth = 0
    end_pos = -1
    in_string = False
    escape_next = False
    for i in range(first_brace, len(cleaned)):
        ch = cleaned[i]
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
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
                end_pos = i + 1
                break

    if end_pos > first_brace:
        snippet = cleaned[first_brace:end_pos]
        fixed_snippet = _fix_json(snippet)
        result = _try_decode(fixed_snippet, 0)
        if result is not None and isinstance(result[0], dict):
            return result[0]

    # Last resort: scan all '{' positions for any valid dict
    for i, ch in enumerate(cleaned):
        if ch == "{" and i != first_brace:
            result = _try_decode(cleaned, i)
            if result is not None and isinstance(result[0], dict):
                return result[0]

    return None
