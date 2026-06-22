"""Tests for app.core.json_extract module."""

from app.core.json_extract import extract_json


def test_nested_braces():
    """Should correctly parse JSON with nested objects."""
    text = '{"enriched": {"project": {"title": "Migrazione"}, "constraints": ["A", "B"]}, "standards_applied": ["ISO 27001"], "sources": ["doc1.pdf"]}'
    data = extract_json(text)
    assert data is not None
    assert "enriched" in data
    assert data["enriched"]["project"]["title"] == "Migrazione"


def test_markdown_fences():
    """Should strip markdown code fences before parsing."""
    text = '```json\n{"score": 0.85, "passed": true, "issues": []}\n```'
    data = extract_json(text)
    assert data is not None
    assert data["score"] == 0.85
    assert data["passed"] is True


def test_trailing_commas():
    """Should handle trailing commas in JSON."""
    text = '{"a": 1, "b": [2, 3,], }'
    data = extract_json(text)
    assert data is not None
    assert data["a"] == 1
    assert data["b"] == [2, 3]


def test_no_json_returns_none():
    """Should return None when no JSON object found."""
    assert extract_json("Just some text without JSON") is None
    assert extract_json("") is None
    assert extract_json(None) is None


def test_prose_before_json():
    """Should extract JSON embedded in LLM prose."""
    text = 'I analyzed the requirements and here is the result:\n{"score": 0.9, "passed": true}\nHope this helps!'
    data = extract_json(text)
    assert data is not None
    assert data["score"] == 0.9


def test_prose_after_json():
    """Should extract JSON followed by prose."""
    text = '{"result": "ok"}\n\nNote: This is a summary.'
    data = extract_json(text)
    assert data is not None
    assert data["result"] == "ok"
