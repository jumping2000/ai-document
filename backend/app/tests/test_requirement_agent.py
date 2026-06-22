"""Tests for requirement agent canonical schema and normalize_to_canonical adapter."""

import json

from app.agents.requirement.agent import (
    CANONICAL_CRITICAL_FIELDS,
    CANONICAL_SCHEMA,
    normalize_to_canonical,
)


# ---------------------------------------------------------------------------
# CANONICAL_SCHEMA is valid JSON-serializable
# ---------------------------------------------------------------------------
class TestCanonicalSchemaPromptFormat:
    def test_canonical_schema_prompt_format(self):
        """CANONICAL_SCHEMA must be JSON-serializable (used in LLM prompt)."""
        serialized = json.dumps(CANONICAL_SCHEMA, ensure_ascii=False)
        parsed = json.loads(serialized)
        assert parsed == CANONICAL_SCHEMA

    def test_canonical_critical_fields_are_nonempty_strings(self):
        for dotpath in CANONICAL_CRITICAL_FIELDS:
            assert isinstance(dotpath, str) and dotpath.strip()


# ---------------------------------------------------------------------------
# normalize_to_canonical — passthrough
# ---------------------------------------------------------------------------
class TestNormalizePassthrough:
    def test_normalize_to_canonical_passthrough(self):
        """Nested input that already conforms should pass through unchanged."""
        nested: dict = {
            "project": {
                "title": "My Project",
                "organization": "ACME",
                "reference_code": None,
                "description": "Desc",
            },
            "scope": {
                "objectives": ["Obj1"],
                "in_scope": ["In1"],
                "out_of_scope": ["Out1"],
            },
            "functional_requirements": [
                {"id": "FR-001", "title": "F1", "description": "d", "priority": "MUST"}
            ],
            "technical_requirements": [{"id": "TR-001", "category": "Hosting", "description": "t"}],
            "sla": {
                "availability": "99.9%",
                "rto": "4h",
                "rpo": "1h",
                "response_time": "<3s",
                "custom_kpis": [],
            },
            "security_compliance": {
                "standards": ["ISO 27001"],
                "requirements": ["MFA"],
                "data_classification": "Confidenziale",
            },
            "timeline": {"project_start": "2026-01-01", "go_live": "2026-12-01", "milestones": []},
            "integrations": [{"system": "CRM", "type": "API", "protocol": "REST"}],
            "stakeholders": [{"role": "PM", "responsibilities": "Manage"}],
            "constraints": ["Budget < 100k"],
        }
        result = normalize_to_canonical(nested)
        # All top-level keys preserved
        for key in nested:
            assert key in result
        # Nested structures preserved exactly
        assert result["project"]["title"] == "My Project"
        assert result["scope"]["objectives"] == ["Obj1"]
        assert result["functional_requirements"][0]["id"] == "FR-001"
        assert result["sla"]["availability"] == "99.9%"
        assert result["security_compliance"]["standards"] == ["ISO 27001"]
        assert result["timeline"]["go_live"] == "2026-12-01"
        assert result["integrations"][0]["system"] == "CRM"
        assert result["stakeholders"][0]["role"] == "PM"
        assert result["constraints"] == ["Budget < 100k"]


# ---------------------------------------------------------------------------
# normalize_to_canonical — flat → nested mapping
# ---------------------------------------------------------------------------
class TestNormalizeFlatToNested:
    def test_normalize_to_canonical_flat_to_nested(self):
        """Flat keys are mapped to canonical nested structure."""
        flat: dict = {
            "project_name": "Portale Web",
            "project_scope": "Migliorare UX",
            "security_requirements": ["MFA obbligatorio", "AES-256"],
            "budget_range": "€150.000",
            "target_architecture": "Microservices on K8s",
            "sla": "99.5%",
            "kpi": ["Uptime", "Response < 2s"],
            "compliance": ["GDPR", "ISO 27001"],
            "stakeholders": ["CIO", "PM", "DPO"],
            "end_users": ["Dipendenti", "Partner"],
            "timeline": "2026-12-31",
            "integrations": [{"system": "SAP", "type": "API"}],
            "constraints": ["No cloud pubblico"],
            "functional_requirements": [
                {"id": "FR-001", "title": "Login", "description": "SSO", "priority": "MUST"}
            ],
            "non_functional_requirements": [
                {"id": "TR-NF-001", "category": "Performance", "description": "< 2s"}
            ],
        }
        result = normalize_to_canonical(flat)

        # project_name → project.title
        assert result["project"]["title"] == "Portale Web"
        # project_scope (string) → scope.objectives (list)
        assert result["scope"]["objectives"] == ["Migliorare UX"]
        # security_requirements → security_compliance.requirements
        assert result["security_compliance"]["requirements"] == ["MFA obbligatorio", "AES-256"]
        # compliance → security_compliance.standards (overrides empty default from security_requirements)
        assert result["security_compliance"]["standards"] == ["GDPR", "ISO 27001"]
        # budget_range → budget.indicative_value
        assert result["budget"]["indicative_value"] == "€150.000"
        # target_architecture → appended as TR
        tr_ids = [tr["id"] for tr in result["technical_requirements"]]
        assert "TR-ARCH-001" in tr_ids
        # sla → sla.availability
        assert result["sla"]["availability"] == "99.5%"
        # kpi → sla.custom_kpis
        assert result["sla"]["custom_kpis"] == ["Uptime", "Response < 2s"]
        # compliance → security_compliance.standards
        assert result["security_compliance"]["standards"] == ["GDPR", "ISO 27001"]
        # stakeholders (list of strings) → list of dicts
        assert all(isinstance(s, dict) for s in result["stakeholders"])
        assert result["stakeholders"][0]["role"] == "CIO"
        # end_users → scope.in_scope
        assert result["scope"]["in_scope"] == ["Dipendenti", "Partner"]
        # timeline → timeline.go_live
        assert result["timeline"]["go_live"] == "2026-12-31"
        # integrations preserved
        assert result["integrations"] == [{"system": "SAP", "type": "API"}]
        # constraints preserved
        assert result["constraints"] == ["No cloud pubblico"]
        # functional_requirements preserved
        assert len(result["functional_requirements"]) == 1
        assert result["functional_requirements"][0]["id"] == "FR-001"
        # non_functional_requirements → technical_requirements (appended)
        nf_ids = [tr["id"] for tr in result["technical_requirements"]]
        assert "TR-NF-001" in nf_ids


# ---------------------------------------------------------------------------
# normalize_to_canonical — partial (mixed flat + nested, nested wins)
# ---------------------------------------------------------------------------
class TestNormalizePartial:
    def test_normalize_to_canonical_partial(self):
        """Nested keys take precedence over flat keys."""
        mixed: dict = {
            # nested already present
            "project": {
                "title": "Existing Title",
                "organization": "Org",
            },
            "scope": {
                "objectives": ["Existing Obj"],
            },
            "sla": {"availability": "99.99%"},
            "security_compliance": {
                "standards": ["ISO 27001"],
                "requirements": ["Existing Req"],
            },
            "timeline": {"go_live": "2026-06-01"},
            "functional_requirements": [
                {"id": "FR-EX", "title": "Existing", "description": "d", "priority": "MUST"}
            ],
            "technical_requirements": [
                {"id": "TR-EX", "category": "Hosting", "description": "existing"}
            ],
            "integrations": [{"system": "Existing", "type": "API", "protocol": "REST"}],
            "stakeholders": [{"role": "Existing", "responsibilities": "r"}],
            "constraints": ["Existing constraint"],
            # flat keys that would normally map — should NOT overwrite nested
            "project_name": "Flat Title",
            "project_scope": "Flat Scope",
            "security_requirements": ["Flat Req"],
            "sla_flat": "95%",
            "timeline_flat": "2027-01-01",
        }
        result = normalize_to_canonical(mixed)

        # Nested takes precedence
        assert result["project"]["title"] == "Existing Title"
        assert result["scope"]["objectives"] == ["Existing Obj"]
        assert result["security_compliance"]["requirements"] == ["Existing Req"]
        assert result["security_compliance"]["standards"] == ["ISO 27001"]
        assert result["sla"]["availability"] == "99.99%"
        assert result["timeline"]["go_live"] == "2026-06-01"
        assert len(result["functional_requirements"]) == 1
        assert result["functional_requirements"][0]["id"] == "FR-EX"
        assert len(result["technical_requirements"]) == 1
        assert result["technical_requirements"][0]["id"] == "TR-EX"
        assert result["integrations"] == [{"system": "Existing", "type": "API", "protocol": "REST"}]
        assert result["stakeholders"] == [{"role": "Existing", "responsibilities": "r"}]
        assert result["constraints"] == ["Existing constraint"]
