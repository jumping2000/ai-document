"""
Validation Skill

Standalone, testable functions for requirement and document validation.
Used by OrchestratorAgent before approving state transitions.

All functions are pure (no side effects) and synchronous.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.app_config import app_cfg


@dataclass
class ValidationResult:
    valid: bool
    issues: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    confidence: float = 1.0


# ── Fallback field specs (same values as template.yaml) ────────────────────────

_FALLBACK_REQUIRED: dict[str, list[dict[str, Any]]] = {
    "capitolato": [
        {"path": "project.title", "label": "Titolo progetto"},
        {"path": "project.organization", "label": "Organizzazione"},
        {"path": "scope.objectives", "label": "Obiettivi progetto"},
        {"path": "functional_requirements", "label": "Requisiti funzionali", "min_items": 3},
        {"path": "technical_requirements", "label": "Requisiti tecnici", "min_items": 1},
        {"path": "sla.metrics", "label": "Indicatori SLA", "min_items": 1},
        {"path": "security_compliance.standards", "label": "Standard sicurezza"},
        {"path": "timeline.go_live", "label": "Data go-live"},
    ],
    "requisiti": [
        {"path": "project.title", "label": "Titolo progetto"},
        {"path": "scope.objectives", "label": "Obiettivi"},
        {"path": "functional_requirements", "label": "Requisiti funzionali", "min_items": 3},
        {"path": "technical_requirements", "label": "Requisiti tecnici", "min_items": 1},
        {"path": "sla.metrics", "label": "Indicatori SLA", "min_items": 1},
        {"path": "security_compliance", "label": "Requisiti sicurezza"},
    ],
    "documento": [
        {"path": "project.title", "label": "Titolo progetto"},
        {"path": "definitions", "label": "Definizioni", "min_items": 1},
        {"path": "architecture.topology", "label": "Schema Logico e Topologia"},
        {"path": "architecture.components", "label": "Componenti Core", "min_items": 1},
        {"path": "security.access_control", "label": "Controlli Accesso"},
    ],
}


def _get_required_fields(document_type: str) -> list[dict[str, Any]]:
    """Load required_fields from template.yaml, with fallback to hard-coded."""
    from app.core.template_config import load_template_config

    config = load_template_config(document_type)
    fields = config.get("required_fields")
    if fields:
        return fields
    return _FALLBACK_REQUIRED.get(document_type, [])


def _get_nested(data: dict, dotpath: str) -> Any:
    """Traverse nested dict with dot-notation path."""
    parts = dotpath.split(".")
    current = data
    for p in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(p)
    return current


def validate_requirements_completeness(
    requirements: dict[str, Any],
    document_type: str = "capitolato",
) -> ValidationResult:
    """
    Check structural completeness of collected requirements.

    Input:  requirements dict from RequirementAgent
    Output: ValidationResult with issues and confidence score
    """
    result = ValidationResult(valid=True)
    fields = _get_required_fields(document_type)

    for field_spec in fields:
        dotpath = field_spec["path"]
        label = field_spec["label"]
        value = _get_nested(requirements, dotpath)
        if value is None or value == "" or value == [] or value == {}:
            result.missing_fields.append(label)
            result.issues.append(f"Campo obbligatorio mancante: {label}")

    # Minimum counts from config min_items
    frs = requirements.get("functional_requirements", [])
    fr_spec = next((f for f in fields if f["path"] == "functional_requirements"), None)
    fr_min = fr_spec.get("min_items", 3) if fr_spec else 3
    if isinstance(frs, list) and len(frs) < fr_min:
        result.issues.append(
            f"Requisiti funzionali insufficienti: {len(frs)} di {fr_min} minimi richiesti"
        )

    trs = requirements.get("technical_requirements", [])
    tr_spec = next((f for f in fields if f["path"] == "technical_requirements"), None)
    tr_min = tr_spec.get("min_items", 1) if tr_spec else 1
    if isinstance(trs, list) and len(trs) < tr_min:
        result.issues.append(f"Almeno {tr_min} requisito tecnico è obbligatorio")

    # Confidence: ratio of filled fields
    total = len(fields)
    missing_count = len(result.missing_fields)
    result.confidence = round((total - missing_count) / total, 2) if total else 1.0

    # Structural issues (min_items violations) are always blocking
    has_structural = any(
        "insufficienti" in i or "obbligatorio" not in i
        for i in result.issues
        if "Requisiti funzionali insufficienti" in i or "requisito tecnico è obbligatorio" in i
    )
    # Re-check: structural = min_items violations only
    structural_issues = [
        i for i in result.issues if "insufficienti" in i or "requisito tecnico è obbligatorio" in i
    ]

    if structural_issues:
        # Structural gaps always block
        result.valid = False
    elif result.missing_fields and result.confidence >= app_cfg(
        "validation.confidence_threshold", 0.75
    ):
        # Missing metadata fields with high confidence → warn but allow
        result.valid = True
        result.warnings = [f"Campo opzionale mancante: {f}" for f in result.missing_fields]
    else:
        result.valid = len(result.issues) == 0

    return result


def _parse_duration_hours(value: str) -> float | None:
    """Parse a duration string like '4h', '30m', '2h30m' into hours."""
    import re

    value = value.strip().lower()
    hours = 0.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*h", value)
    if m:
        hours += float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*m(?:in)?", value)
    if m:
        hours += float(m.group(1)) / 60
    if hours == 0.0:
        try:
            hours = float(value)
        except ValueError:
            return None
    return hours


def validate_sla_metrics(
    sla: dict[str, Any] | None,
    document_type: str = "capitolato",
) -> ValidationResult:
    """
    Validate free-form SLA metrics list.

    For 'documento' type, SLA is never required.
    For 'capitolato' and 'requisiti', at least one metric with metric+target is required.
    """
    if document_type == "documento":
        return ValidationResult(valid=True)

    if not sla or not isinstance(sla, dict):
        return ValidationResult(
            valid=False,
            issues=["SLA: nessuna metrica definita. Inserire almeno una metrica SLA."],
            missing_fields=["sla.metrics"],
        )

    metrics = sla.get("metrics", [])
    if not metrics or not isinstance(metrics, list) or len(metrics) == 0:
        return ValidationResult(
            valid=False,
            issues=["SLA: inserire almeno una metrica (es. Disponibilità, RTO, RPO)."],
            missing_fields=["sla.metrics"],
        )

    issues = []
    for i, m in enumerate(metrics):
        if not isinstance(m, dict):
            issues.append(f"SLA metrics[{i}]: deve essere un oggetto con 'metric' e 'target'.")
            continue
        if not m.get("metric"):
            issues.append(f"SLA metrics[{i}]: campo 'metric' mancante.")
        if not m.get("target"):
            issues.append(
                f"SLA metrics[{i}]: campo 'target' mancante per '{m.get('metric', '?')}'."
            )

    return ValidationResult(
        valid=len(issues) == 0,
        issues=issues,
        missing_fields=[] if len(issues) == 0 else ["sla.metrics"],
    )

    # If SLA section is completely empty, that's a warning (some docs may not need SLA)
    if not sla:
        result.warnings.append("Sezione SLA vuota")
        result.confidence = 0.5

    # Confidence: ratio of present KPI fields
    total = len(expected_kpis) if expected_kpis else 1
    missing_kpis = len(
        [
            f
            for f in result.missing_fields
            if f in [k if isinstance(k, str) else k.get("label", "") for k in expected_kpis]
        ]
    )
    result.confidence = round((total - missing_kpis) / total, 2) if total else 1.0

    # Blocking only if required KPIs are missing
    if result.issues:
        result.valid = False

    return result


def validate_document_sections(
    content: str,
    document_type: str = "capitolato",
) -> ValidationResult:
    """
    Check that all required sections are present in the generated document.

    Input:  markdown content string
    Output: ValidationResult with missing_sections list
    """
    import re as _re

    result = ValidationResult(valid=True)

    required_sections_cap = [
        "Oggetto",
        "Requisiti Funzionali",
        "Requisiti Tecnici",
        "Sicurezza",
        "SLA",
        "Integrazioni",
        "Piano",
        "Criteri",
    ]
    required_sections_req = [
        "Introduzione",
        "Requisiti Funzionali",
        "Requisiti Tecnici",
        "Sicurezza",
        "Architettura",
        "Integrazione",
    ]

    sections = required_sections_cap if document_type == "capitolato" else required_sections_req

    # Extract markdown headings for robust matching
    headings = _re.findall(r"^#+\s+(.+)$", content, _re.MULTILINE)
    headings_lower = [h.lower() for h in headings]

    for section in sections:
        sec_lower = section.lower()
        # Match if section keyword appears in any heading
        found = any(sec_lower in h for h in headings_lower)
        # Fallback: also match in body text (for inline sections)
        if not found:
            found = sec_lower in content.lower()
        if not found:
            result.missing_fields.append(section)
            result.issues.append(f"Sezione mancante nel documento: '{section}'")

    total = len(sections)
    missing = len(result.missing_fields)
    result.confidence = round((total - missing) / total, 2) if total else 1.0
    result.valid = missing == 0

    return result


def detect_placeholder_content(content: str) -> list[str]:
    """
    Detect unfilled placeholders in a generated document.

    Returns a list of placeholder strings found.
    Common patterns: [TBD], [TODO], [PLACEHOLDER], empty markdown tables.
    """
    import re

    patterns = [
        r"\[TBD\]",
        r"\[TODO\]",
        r"\[PLACEHOLDER\]",
        r"\[DA DEFINIRE\]",
        r"\[INSERIRE\]",
        r"SEZIONE DA COMPLETARE",
        r"\.\.\.",  # trailing ellipsis
    ]
    found = []
    for pat in patterns:
        matches = re.findall(pat, content, re.IGNORECASE)
        found.extend(matches)

    return list(set(found))


def score_requirement_richness(requirements: dict[str, Any]) -> float:
    """
    Compute a 0.0–1.0 richness score for a requirements dict.

    Rewards: more FRs, more TRs, SLA detail, integration count, stakeholders.
    """
    score = 0.0
    weights = {
        "functional_requirements": 0.30,
        "technical_requirements": 0.20,
        "sla_detail": 0.15,
        "integrations": 0.10,
        "stakeholders": 0.10,
        "security_detail": 0.10,
        "timeline_detail": 0.05,
    }

    frs = requirements.get("functional_requirements", [])
    score += min(len(frs) / 10, 1.0) * weights["functional_requirements"]

    trs = requirements.get("technical_requirements", [])
    score += min(len(trs) / 5, 1.0) * weights["technical_requirements"]

    sla = requirements.get("sla", {})
    sla_filled = sum(1 for v in sla.values() if v) / max(len(sla), 1)
    score += sla_filled * weights["sla_detail"]

    integrations = requirements.get("integrations", [])
    score += min(len(integrations) / 3, 1.0) * weights["integrations"]

    stakeholders = requirements.get("stakeholders", [])
    score += min(len(stakeholders) / 3, 1.0) * weights["stakeholders"]

    security = requirements.get("security_compliance", {})
    sec_score = (
        len(security.get("standards", [])) / 3 + len(security.get("requirements", [])) / 5
    ) / 2
    score += min(sec_score, 1.0) * weights["security_detail"]

    timeline = requirements.get("timeline", {})
    tl_filled = sum(1 for v in timeline.values() if v) / max(len(timeline), 1)
    score += tl_filled * weights["timeline_detail"]

    return round(min(score, 1.0), 3)
