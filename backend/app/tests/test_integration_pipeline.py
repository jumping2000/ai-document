"""
Integration tests for the canonical schema pipeline.

Verifies end-to-end data flow:
  flat LLM output → normalize_to_canonical → validate → render template
"""

from __future__ import annotations

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.agents.requirement.agent import normalize_to_canonical
from app.skills.validation.validation_skill import (
    detect_placeholder_content,
    score_requirement_richness,
    validate_document_sections,
    validate_requirements_completeness,
    validate_sla_consistency,
)


@pytest.fixture
def flat_llm_output() -> dict:
    """Simulates what an LLM might return with flat keys."""
    return {
        "project_name": "Sistema ERP Cloud",
        "project_scope": "Digitalizzare i processi amministrativi",
        "stakeholders": ["CIO", "DPO", "Responsabile IT"],
        "functional_requirements": [
            {
                "id": "FR-001",
                "title": "Login SSO",
                "description": "Autenticazione SAML2",
                "priority": "MUST",
            },
            {
                "id": "FR-002",
                "title": "Dashboard",
                "description": "Dashboard personalizzabile",
                "priority": "MUST",
            },
            {
                "id": "FR-003",
                "title": "Reporting",
                "description": "Report configurabili",
                "priority": "SHOULD",
            },
        ],
        "technical_requirements": [
            {
                "id": "TR-001",
                "category": "Hosting",
                "description": "Cloud SaaS multi-tenant",
                "constraint": "",
            },
        ],
        "sla": {"K1": "99%", "K2": "1%", "K3": "0"},
        "security_requirements": ["MFA obbligatorio", "Crittografia AES-256"],
        "compliance": ["ISO 27001", "GDPR"],
        "timeline": {"go_live": "2026-06-01"},
        "integrations": [{"system": "SAP", "type": "API", "protocol": "REST"}],
    }


@pytest.fixture
def template_env() -> Environment:
    """Jinja2 environment pointing at the real templates."""
    import os

    base = os.path.join(os.path.dirname(__file__), "..", "templates")
    return Environment(
        loader=FileSystemLoader(base),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


class TestFullPipeline:
    def test_full_pipeline_canonical_schema(
        self, flat_llm_output: dict, template_env: Environment
    ) -> None:
        # Step 1: normalize flat → nested
        canon = normalize_to_canonical(flat_llm_output)

        assert "project" in canon
        assert canon["project"]["title"] == "Sistema ERP Cloud"
        assert isinstance(canon["scope"]["objectives"], list)
        assert len(canon["scope"]["objectives"]) > 0

        # Step 2: validate completeness
        val = validate_requirements_completeness(canon, "capitolato")
        # Should pass or have minimal issues (some fields may be missing from flat input)
        assert val.confidence > 0.5, f"Confidence too low: {val.confidence}"

        # Step 3: SLA consistency
        sla_val = validate_sla_consistency(canon.get("sla", {}))
        assert sla_val.valid is True or len(sla_val.warnings) > 0

        # Step 4: richness score
        score = score_requirement_richness(canon)
        assert 0.0 <= score <= 1.0

        # Step 5: render template
        template = template_env.get_template("capitolato/base.j2")
        rendered = template.render(enriched_requirements=canon)

        # Title should appear (not the TBD fallback)
        assert "Sistema ERP Cloud" in rendered

        # Functional requirements should appear in the table
        assert "FR-001" in rendered
        assert "FR-002" in rendered
        assert "FR-003" in rendered

        # Step 6: detect placeholders (informational)
        placeholders = detect_placeholder_content(rendered)
        # Template has "[SEZIONE DA COMPLETARE]" hardcoded — that's expected
        # but user-provided data should NOT generate placeholders

    def test_nested_input_passthrough(self) -> None:
        """Already-nested input should pass through normalize_to_canonical."""
        nested = {
            "project": {"title": "Test", "organization": "Org"},
            "scope": {"objectives": ["Obj1"]},
            "functional_requirements": [
                {"id": "FR-1", "title": "T", "description": "D", "priority": "MUST"},
                {"id": "FR-2", "title": "T", "description": "D", "priority": "MUST"},
                {"id": "FR-3", "title": "T", "description": "D", "priority": "MUST"},
            ],
            "technical_requirements": [
                {"id": "TR-1", "category": "C", "description": "D"},
            ],
            "sla": {"K1": "99%", "K2": "1%", "K3": "0"},
            "security_compliance": {"standards": ["ISO 27001"]},
            "timeline": {"go_live": "2026-01-01"},
        }
        canon = normalize_to_canonical(nested)
        assert canon["project"]["title"] == "Test"
        val = validate_requirements_completeness(canon, "capitolato")
        assert val.valid is True

    def test_template_sections_present(
        self, flat_llm_output: dict, template_env: Environment
    ) -> None:
        """Verify document sections are detected in rendered output."""
        canon = normalize_to_canonical(flat_llm_output)
        template = template_env.get_template("capitolato/base.j2")
        rendered = template.render(enriched_requirements=canon)

        doc_val = validate_document_sections(rendered, "capitolato")
        # Most sections should be present
        assert doc_val.confidence > 0.3
