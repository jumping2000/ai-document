"""
Tests for the canonical EnrichedRequirements schema.

Validates that the TypedDict structure accepts valid data,
requires mandatory fields, and allows optional fields to be omitted.
"""

from __future__ import annotations

from app.skills.validation.schema import (
    EnrichedRequirements,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_full_enriched_requirements() -> EnrichedRequirements:
    """Construct a fully-populated EnrichedRequirements dict."""
    return {
        "project": {
            "title": "Sistema ERP Cloud",
            "organization": "Comune di Roma",
            "reference_code": "CAP-2025-001",
            "description": "Fornitura sistema ERP cloud per PA.",
        },
        "scope": {
            "objectives": ["Digitalizzare i processi", "Ridurre i costi"],
            "in_scope": ["Modulo HR", "Modulo Finance"],
            "out_of_scope": ["Infrastruttura esistente"],
        },
        "functional_requirements": [
            {
                "id": "FR-001",
                "title": "Login SSO",
                "description": "Autenticazione SSO",
                "priority": "MUST",
            },
            {
                "id": "FR-002",
                "title": "Dashboard",
                "description": "Dashboard principale",
                "priority": "SHOULD",
            },
        ],
        "technical_requirements": [
            {
                "id": "TR-001",
                "category": "Architettura",
                "description": "Microservizi",
                "constraint": "Kubernetes",
            },
        ],
        "sla": {
            "K1": "99%",
            "K2": "1%",
            "K3": "0",
        },
        "security_compliance": {
            "standards": ["ISO 27001", "GDPR"],
            "requirements": ["Crittografia end-to-end"],
            "data_classification": "Confidenziale",
        },
        "timeline": {
            "project_start": "2025-03-01",
            "go_live": "2025-12-01",
            "milestones": ["MVP 2025-06-01", "UAT 2025-09-01"],
        },
        "integrations": [{"system": "SAP", "type": "REST"}],
        "stakeholders": [{"name": "Marco Bianchi", "role": "CTO"}],
        "constraints": ["Budget massimo 500k EUR"],
        "regulatory_references": [{"directive": "AgID Cloud PA"}],
        "evaluation_criteria": [{"criterion": "Costo", "weight": 40}],
        "budget": {"amount": 500000, "currency": "EUR"},
    }


def _make_minimal_enriched_requirements() -> EnrichedRequirements:
    """Construct with only required fields — no NotRequired fields."""
    return {
        "project": {
            "title": "Sistema ERP Cloud",
            "organization": "Comune di Roma",
        },
        "scope": {
            "objectives": ["Digitalizzare i processi"],
        },
        "functional_requirements": [
            {
                "id": "FR-001",
                "title": "Login SSO",
                "description": "Autenticazione SSO",
                "priority": "MUST",
            },
        ],
        "technical_requirements": [
            {"id": "TR-001", "category": "Architettura", "description": "Microservizi"},
        ],
        "sla": {
            "availability": "99.9%",
        },
        "security_compliance": {
            "standards": ["ISO 27001"],
        },
        "timeline": {
            "go_live": "2025-12-01",
        },
    }


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_enriched_requirements_shape():
    """Full dict with all fields (required + optional) is a valid EnrichedRequirements."""
    data = _make_full_enriched_requirements()
    # Runtime check: dict satisfies the TypedDict structure
    assert isinstance(data, dict)
    assert "project" in data
    assert "scope" in data
    assert "functional_requirements" in data
    assert "technical_requirements" in data
    assert "sla" in data
    assert "security_compliance" in data
    assert "timeline" in data
    # Optional top-level fields present
    assert "integrations" in data
    assert "stakeholders" in data
    assert "constraints" in data
    assert "regulatory_references" in data
    assert "evaluation_criteria" in data
    assert "budget" in data
    # Sub-structure required fields
    assert data["project"]["title"] == "Sistema ERP Cloud"
    assert data["project"]["organization"] == "Comune di Roma"
    assert data["scope"]["objectives"] == ["Digitalizzare i processi", "Ridurre i costi"]
    assert data["functional_requirements"][0]["id"] == "FR-001"
    assert data["functional_requirements"][0]["priority"] == "MUST"
    assert data["technical_requirements"][0]["category"] == "Architettura"
    assert data["sla"]["K1"] == "99%"
    assert data["security_compliance"]["standards"] == ["ISO 27001", "GDPR"]
    assert data["timeline"]["go_live"] == "2025-12-01"


def test_enriched_requirements_minimal():
    """Dict with only required fields (no NotRequired) is valid."""
    data = _make_minimal_enriched_requirements()
    assert isinstance(data, dict)
    assert data["project"]["title"] == "Sistema ERP Cloud"
    assert data["project"]["organization"] == "Comune di Roma"
    # No optional project fields
    assert "reference_code" not in data["project"]
    assert "description" not in data["project"]
    # No optional scope fields
    assert "in_scope" not in data["scope"]
    assert "out_of_scope" not in data["scope"]
    # No optional top-level fields
    assert "integrations" not in data
    assert "stakeholders" not in data
    assert "constraints" not in data
    assert "regulatory_references" not in data
    assert "evaluation_criteria" not in data
    assert "budget" not in data


def test_enriched_requirements_optional_fields():
    """Optional fields are omitted when not provided — no defaults inserted."""
    data = _make_minimal_enriched_requirements()

    # Project optional fields
    assert "reference_code" not in data["project"]
    assert "description" not in data["project"]

    # Scope optional fields
    assert "in_scope" not in data["scope"]
    assert "out_of_scope" not in data["scope"]

    # Technical requirement optional field
    assert "constraint" not in data["technical_requirements"][0]

    # SLA optional fields
    assert "rto" not in data["sla"]
    assert "rpo" not in data["sla"]
    assert "response_time" not in data["sla"]
    assert "custom_kpis" not in data["sla"]

    # Security optional fields
    assert "requirements" not in data["security_compliance"]
    assert "data_classification" not in data["security_compliance"]

    # Timeline optional fields
    assert "project_start" not in data["timeline"]
    assert "milestones" not in data["timeline"]

    # Top-level optional fields
    for field in (
        "integrations",
        "stakeholders",
        "constraints",
        "regulatory_references",
        "evaluation_criteria",
        "budget",
    ):
        assert field not in data, f"Optional field '{field}' should be omitted"
