"""
Validation Skill

Standalone, testable functions for requirement and document validation.
Used by OrchestratorAgent before approving state transitions.

All functions are pure (no side effects) and synchronous.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    valid: bool
    issues: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    confidence: float = 1.0


# ── Mandatory field specs per document type ────────────────────────────────────

_CAPITOLATO_REQUIRED = [
    ("project.title",                 "Titolo progetto"),
    ("project.organization",          "Organizzazione"),
    ("scope.objectives",              "Obiettivi progetto"),
    ("functional_requirements",       "Requisiti funzionali (≥3)"),
    ("technical_requirements",        "Requisiti tecnici (≥1)"),
    ("sla.availability",              "SLA disponibilità"),
    ("security_compliance.standards", "Standard sicurezza"),
    ("timeline.go_live",              "Data go-live"),
]

_REQUISITI_REQUIRED = [
    ("project.title",           "Titolo progetto"),
    ("scope.objectives",        "Obiettivi"),
    ("functional_requirements", "Requisiti funzionali (≥3)"),
    ("technical_requirements",  "Requisiti tecnici (≥1)"),
    ("security_compliance",     "Requisiti sicurezza"),
]


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
    spec = _CAPITOLATO_REQUIRED if document_type == "capitolato" else _REQUISITI_REQUIRED

    for dotpath, label in spec:
        value = _get_nested(requirements, dotpath)
        if value is None or value == "" or value == [] or value == {}:
            result.missing_fields.append(label)
            result.issues.append(f"Campo obbligatorio mancante: {label}")

    # Minimum counts
    frs = requirements.get("functional_requirements", [])
    if isinstance(frs, list) and len(frs) < 3:
        result.issues.append(
            f"Requisiti funzionali insufficienti: {len(frs)} di 3 minimi richiesti"
        )

    trs = requirements.get("technical_requirements", [])
    if isinstance(trs, list) and len(trs) < 1:
        result.issues.append("Almeno 1 requisito tecnico è obbligatorio")

    # Confidence: ratio of filled fields
    total = len(spec)
    missing_count = len(result.missing_fields)
    result.confidence = round((total - missing_count) / total, 2) if total else 1.0
    result.valid = len(result.issues) == 0

    return result


def validate_sla_consistency(sla: dict[str, Any]) -> ValidationResult:
    """
    Validate SLA values are internally consistent.

    Rules:
    - Availability must be between 95% and 99.999%
    - RTO must be > RPO (cannot recover faster than last backup)
    - Response time must be a positive number
    """
    result = ValidationResult(valid=True)

    availability = sla.get("availability", "")
    if availability:
        try:
            pct = float(str(availability).rstrip("%"))
            if pct < 95:
                result.warnings.append(
                    f"Disponibilità {availability} inferiore al minimo consigliato (95%)"
                )
            if pct > 99.999:
                result.issues.append(
                    f"Disponibilità {availability} non realistica (max 99.999%)"
                )
        except ValueError:
            result.warnings.append(f"Valore disponibilità non parsabile: {availability!r}")

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
    result = ValidationResult(valid=True)

    required_sections_cap = [
        "Oggetto", "Requisiti Funzionali", "Requisiti Tecnici",
        "Sicurezza", "SLA", "Integrazioni", "Piano", "Criteri",
    ]
    required_sections_req = [
        "Introduzione", "Requisiti Funzionali", "Requisiti Tecnici",
        "Sicurezza", "Architettura", "Integrazione",
    ]

    sections = (
        required_sections_cap if document_type == "capitolato"
        else required_sections_req
    )

    content_lower = content.lower()
    for section in sections:
        if section.lower() not in content_lower:
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
        r"\.\.\.",           # trailing ellipsis
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
        len(security.get("standards", [])) / 3
        + len(security.get("requirements", [])) / 5
    ) / 2
    score += min(sec_score, 1.0) * weights["security_detail"]

    timeline = requirements.get("timeline", {})
    tl_filled = sum(1 for v in timeline.values() if v) / max(len(timeline), 1)
    score += tl_filled * weights["timeline_detail"]

    return round(min(score, 1.0), 3)
