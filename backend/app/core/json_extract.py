"""
Robust JSON extraction from LLM responses.

Handles common LLM quirks: trailing commas, markdown fences,
multiple JSON objects, prose mixed with JSON.
"""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json(text: str) -> dict[str, Any] | None:
    """
    Extract the first valid JSON object from an LLM response.

    Strategy:
    1. Strip markdown code fences (```json ... ```)
    2. Try raw_decode from first '{' (handles nested braces correctly)
    3. Fallback: fix trailing commas and retry

    Returns None if no valid JSON object found.
    """
    if not text:
        return None

    # Strip markdown fences
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```", "", cleaned)

    # Find first '{' and try raw_decode
    for i, ch in enumerate(cleaned):
        if ch == "{":
            decoder = json.JSONDecoder()
            try:
                obj, _ = decoder.raw_decode(cleaned, i)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass

    # Fallback: fix trailing commas and retry
    fixed = re.sub(r",\s*([}\]])", r"\1", cleaned)
    for i, ch in enumerate(fixed):
        if ch == "{":
            decoder = json.JSONDecoder()
            try:
                obj, _ = decoder.raw_decode(fixed, i)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass

    return None
