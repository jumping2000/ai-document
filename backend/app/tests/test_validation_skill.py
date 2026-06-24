"""
Tests for validation skill functions and MCP client.

All tests are unit-level — no external services required.
"""

from __future__ import annotations

import pytest

from app.skills.validation.validation_skill import (
    detect_placeholder_content,
    score_requirement_richness,
    validate_document_sections,
    validate_requirements_completeness,
    validate_sla_consistency,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def complete_capitolato_requirements() -> dict:
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
            {"id": "FR-001", "title": "Login SSO", "description": "...", "priority": "MUST"},
            {"id": "FR-002", "title": "Dashboard", "description": "...", "priority": "MUST"},
            {"id": "FR-003", "title": "Reporting", "description": "...", "priority": "SHOULD"},
        ],
        "technical_requirements": [
            {"id": "TR-001", "category": "Hosting", "description": "Cloud SaaS", "constraint": ""},
        ],
        "sla": {"K1": "99%", "K2": "1%", "K3": "0"},
        "security_compliance": {
            "standards": ["ISO 27001", "GDPR"],
            "requirements": ["MFA obbligatorio", "Crittografia AES-256"],
        },
        "timeline": {"project_start": "2025-09-01", "go_live": "2026-03-01"},
        "integrations": [{"system": "SAP", "type": "API", "protocol": "REST"}],
        "stakeholders": [{"role": "CIO", "responsibilities": "Sponsor tecnico"}],
        "constraints": [],
        "acceptance_criteria": ["UAT superato al 95%"],
    }


@pytest.fixture
def incomplete_requirements() -> dict:
    return {
        "project": {"title": "Progetto X"},
        "scope": {},
        "functional_requirements": [],
        "technical_requirements": [],
        "sla": {},
        "security_compliance": {},
        "timeline": {},
    }


# ── validate_requirements_completeness ───────────────────────────────────────


class TestValidateRequirementsCompleteness:
    def test_complete_requirements_passes(self, complete_capitolato_requirements: dict) -> None:
        result = validate_requirements_completeness(complete_capitolato_requirements, "capitolato")
        assert result.valid is True
        assert result.missing_fields == []
        assert result.confidence == 1.0

    def test_incomplete_requirements_fails(self, incomplete_requirements: dict) -> None:
        result = validate_requirements_completeness(incomplete_requirements, "capitolato")
        assert result.valid is False
        assert len(result.missing_fields) > 0
        assert result.confidence < 1.0

    def test_too_few_functional_requirements(self, complete_capitolato_requirements: dict) -> None:
        reqs = complete_capitolato_requirements.copy()
        reqs["functional_requirements"] = [
            {"id": "FR-001", "title": "One", "description": "...", "priority": "MUST"},
        ]
        result = validate_requirements_completeness(reqs, "capitolato")
        assert any("funzionali" in issue.lower() for issue in result.issues)

    def test_requisiti_document_type(self, complete_capitolato_requirements: dict) -> None:
        result = validate_requirements_completeness(complete_capitolato_requirements, "requisiti")
        assert result.valid is True

    def test_confidence_partial(self, incomplete_requirements: dict) -> None:
        reqs = incomplete_requirements.copy()
        reqs["project"] = {"title": "Test Project", "organization": "Test Org"}
        reqs["scope"] = {"objectives": ["Obj1"]}
        result = validate_requirements_completeness(reqs, "capitolato")
        assert 0.0 < result.confidence < 1.0


# ── validate_sla_consistency ──────────────────────────────────────────────────


class TestValidateSLAConsistency:
    def test_valid_sla_all_kpis_present(self) -> None:
        """Valid when all expected KPIs are present."""
        result = validate_sla_consistency({"K1": "99%", "K2": "1%", "K3": "0"})
        assert result.valid is True
        assert result.issues == []

    def test_missing_required_kpi_fails(self) -> None:
        """Missing required KPI generates an issue."""
        result = validate_sla_consistency({"K2": "1%", "K3": "0"})
        assert result.valid is False
        assert any("Qualità del Codice" in issue for issue in result.issues)

    def test_empty_sla_fails(self) -> None:
        """Empty SLA → all KPIs missing → invalid."""
        result = validate_sla_consistency({})
        assert result.valid is False
        assert len(result.issues) >= 1

    def test_missing_optional_kpo_warning(self) -> None:
        """Missing optional KPO generates a warning, not a blocking issue."""
        result = validate_sla_consistency({"K1": "99%", "K2": "1%", "K3": "0"})
        # KPOs reuse same field names as KPIs → all present
        assert result.valid is True
        assert result.warnings == []

    def test_value_not_validated(self) -> None:
        """Values are NOT validated — only presence matters."""
        result = validate_sla_consistency({"K1": "50%", "K2": "99%", "K3": "30"})
        assert result.valid is True  # all KPIs present, even with "bad" values


# ── validate_document_sections ────────────────────────────────────────────────


class TestValidateDocumentSections:
    COMPLETE_DOC = """
# Capitolato

## Oggetto dell'Appalto
Contenuto...

## Requisiti Funzionali
FR-001...

## Requisiti Tecnici
TR-001...

## Sicurezza e Compliance
ISO 27001...

## Service Level Agreement (SLA)
99.9% availability...

## Integrazioni
SAP REST...

## Piano di Progetto
Timeline...

## Criteri di Valutazione
Peso offerta tecnica 70%...
"""

    def test_complete_document_passes(self) -> None:
        result = validate_document_sections(self.COMPLETE_DOC, "capitolato")
        assert result.valid is True

    def test_missing_section_detected(self) -> None:
        doc = "# Capitolato\n\n## Oggetto\nContenuto...\n"
        result = validate_document_sections(doc, "capitolato")
        assert result.valid is False
        assert len(result.missing_fields) > 0

    def test_empty_document_fails(self) -> None:
        result = validate_document_sections("", "capitolato")
        assert result.valid is False
        assert result.confidence == 0.0


# ── detect_placeholder_content ───────────────────────────────────────────────


class TestDetectPlaceholderContent:
    def test_detects_tbd(self) -> None:
        content = "Il fornitore dovrà rispettare [TBD] gli standard."
        result = detect_placeholder_content(content)
        assert "[TBD]" in result

    def test_detects_multiple_placeholders(self) -> None:
        content = "Budget: [TBD]. Timeline: [TODO]. Sezione: SEZIONE DA COMPLETARE"
        result = detect_placeholder_content(content)
        assert len(result) >= 2

    def test_clean_document_returns_empty(self) -> None:
        content = "Capitolato completo con tutti i contenuti definiti."
        result = detect_placeholder_content(content)
        assert result == []


# ── score_requirement_richness ────────────────────────────────────────────────


class TestScoreRequirementRichness:
    def test_complete_requirements_high_score(self, complete_capitolato_requirements: dict) -> None:
        score = score_requirement_richness(complete_capitolato_requirements)
        assert score > 0.3  # reasonable minimum for a complete set

    def test_empty_requirements_zero_score(self) -> None:
        score = score_requirement_richness({})
        assert score == 0.0

    def test_score_range(self, complete_capitolato_requirements: dict) -> None:
        score = score_requirement_richness(complete_capitolato_requirements)
        assert 0.0 <= score <= 1.0

    def test_more_requirements_higher_score(self, complete_capitolato_requirements: dict) -> None:
        base = score_requirement_richness(complete_capitolato_requirements)

        enriched = complete_capitolato_requirements.copy()
        enriched["functional_requirements"] = [
            {"id": f"FR-{i:03d}", "title": f"FR {i}", "description": "...", "priority": "MUST"}
            for i in range(1, 11)
        ]
        enriched_score = score_requirement_richness(enriched)
        assert enriched_score >= base
