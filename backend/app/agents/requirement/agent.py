"""
Requirement Agent — collects and structures user requirements.
Input  : document_type, existing partial requirements
Output : RequirementResult(requirements, summary, missing_fields, confidence)
"""

from dataclasses import dataclass, field
from typing import Any

import structlog
from agno.agent import Agent

from app.core.agent_config import load_agent_config
from app.core.json_extract import extract_json
from app.core.llm import get_model_adapter

log = structlog.get_logger(__name__)

CANONICAL_SCHEMA = {
    "project": {
        "title": "Nome del progetto/esercizio",
        "organization": "Nome dell'organizzazione committente",
        "reference_code": "Codice identificativo gara/RdO (opzionale)",
        "description": "Breve descrizione del contesto e scopo del progetto",
    },
    "scope": {
        "objectives": ["Obiettivo 1", "Obiettivo 2", "Obiettivo 3"],
        "in_scope": ["Cosa è incluso nella fornitura"],
        "out_of_scope": ["Cosa è escluso"],
    },
    "functional_requirements": [
        {
            "id": "FR-001",
            "title": "Nome del requisito",
            "description": "Descrizione dettagliata del requisito funzionale",
            "priority": "MUST",
        }
    ],
    "technical_requirements": [
        {
            "id": "TR-001",
            "category": "Hosting / Architettura / Sicurezza / Integrazione",
            "description": "Descrizione del requisito tecnico",
            "constraint": "Eventuale vincolo (opzionale)",
        }
    ],
    "sla": {
        "metrics": [
            {"metric": "Nome metrica", "target": "Valore target", "note": "Note (opzionale)"}
        ],
        "penalties": "Eventuali penali contrattuali descritte dall'utente",
    },
    "security_compliance": {
        "standards": ["ISO 27001", "GDPR"],
        "requirements": ["MFA obbligatorio", "Crittografia AES-256"],
        "data_classification": "Confidenziale / Pubblico / Riservato",
    },
    "timeline": {
        "project_start": "YYYY-MM-DD",
        "go_live": "YYYY-MM-DD",
        "milestones": [],
    },
    "integrations": [
        {"system": "Nome sistema", "type": "API/DB/File", "protocol": "REST/SOAP/..."}
    ],
    "stakeholders": [{"role": "CIO / PM / DPO", "responsibilities": "Responsabilità principale"}],
    "constraints": ["Vincolo normativo", "Vincolo budgetario"],
    "regulatory_references": [
        {"code": "D.Lgs 36/2023", "description": "Codice contratti pubblici"}
    ],
    "evaluation_criteria": [
        {"criterion": "Prezzo", "weight": "30%"},
        {"criterion": "Qualità tecnica", "weight": "70%"},
    ],
    "budget": {
        "indicative_value": "€ XXX.XXX",
        "currency": "EUR",
        "notes": "",
    },
}

CANONICAL_CRITICAL_FIELDS = [
    "project.title",
    "project.organization",
    "scope.objectives",
    "functional_requirements",
    "technical_requirements",
    "security_compliance.standards",
    "timeline.go_live",
]

_FLAT_TO_NESTED: dict[str, tuple[str, str]] = {
    "project_name": ("project", "title"),
    "budget_range": ("budget", "indicative_value"),
    "timeline": ("timeline", "go_live"),
}


def normalize_to_canonical(raw: dict[str, Any]) -> dict[str, Any]:
    """Map flat LLM keys to canonical nested EnrichedRequirements schema."""

    def _safe_dict(val: Any) -> dict:
        return dict(val) if isinstance(val, dict) else {}

    def _safe_list(val: Any) -> list:
        return list(val) if isinstance(val, list) else []

    canon: dict[str, Any] = {
        "project": _safe_dict(raw.get("project")),
        "scope": _safe_dict(raw.get("scope")),
        "functional_requirements": _safe_list(raw.get("functional_requirements")),
        "technical_requirements": _safe_list(raw.get("technical_requirements")),
        "sla": _safe_dict(raw.get("sla")),
        "security_compliance": _safe_dict(raw.get("security_compliance")),
        "timeline": _safe_dict(raw.get("timeline")),
        "integrations": _safe_list(raw.get("integrations")),
        "stakeholders": _safe_list(raw.get("stakeholders")),
        "constraints": _safe_list(raw.get("constraints")),
        "regulatory_references": _safe_list(raw.get("regulatory_references")),
        "evaluation_criteria": _safe_list(raw.get("evaluation_criteria")),
        "budget": _safe_dict(raw.get("budget")),
    }

    for flat_key, (section_key, field_key) in _FLAT_TO_NESTED.items():
        value = raw.get(flat_key)
        if value is None:
            continue
        if isinstance(canon[section_key], dict) and not canon[section_key].get(field_key):
            canon[section_key][field_key] = value

    # project_scope as string → list
    if not canon["scope"].get("objectives") and raw.get("project_scope"):
        val = raw["project_scope"]
        canon["scope"]["objectives"] = [val] if isinstance(val, str) else val

    # security_requirements → security_compliance
    if not canon["security_compliance"].get("requirements") and raw.get("security_requirements"):
        canon["security_compliance"]["requirements"] = raw["security_requirements"]
        if not canon["security_compliance"].get("standards"):
            canon["security_compliance"]["standards"] = []

    # target_architecture → append as technical requirement
    if raw.get("target_architecture") and isinstance(raw["target_architecture"], str):
        canon["technical_requirements"].append(
            {
                "id": "TR-ARCH-001",
                "category": "Architettura",
                "description": raw["target_architecture"],
            }
        )

    # stakeholders as flat list of strings → list of dicts
    if raw.get("stakeholders") and isinstance(raw["stakeholders"], list):
        if all(isinstance(s, str) for s in raw["stakeholders"]):
            canon["stakeholders"] = [
                {"role": s, "responsibilities": ""} for s in raw["stakeholders"]
            ]

    # kpi as list → sla.metrics (each item becomes a metric object)
    if raw.get("kpi") and isinstance(raw["kpi"], list):
        existing_metrics = canon["sla"].get("metrics", [])
        for item in raw["kpi"]:
            if isinstance(item, dict) and item.get("metric"):
                existing_metrics.append(
                    {
                        "metric": item["metric"],
                        "target": item.get("target", ""),
                        "note": item.get("note", ""),
                    }
                )
            elif isinstance(item, str):
                existing_metrics.append({"metric": item, "target": "", "note": ""})
        canon["sla"]["metrics"] = existing_metrics

    # compliance list → security_compliance.standards
    if raw.get("compliance") and isinstance(raw["compliance"], list):
        if not canon["security_compliance"].get("standards"):
            canon["security_compliance"]["standards"] = raw["compliance"]

    # end_users → scope.in_scope
    if raw.get("end_users") and isinstance(raw["end_users"], list):
        if not canon["scope"].get("in_scope"):
            canon["scope"]["in_scope"] = raw["end_users"]

    # non_functional_requirements → append to technical_requirements
    if raw.get("non_functional_requirements") and isinstance(
        raw["non_functional_requirements"], list
    ):
        canon["technical_requirements"].extend(raw["non_functional_requirements"])

    return canon


@dataclass
class RequirementResult:
    requirements: dict[str, Any]
    summary: str
    missing_fields: list[str]
    confidence: float
    search_terms: list[str] = field(default_factory=list)


class RequirementError(Exception):
    pass


class RequirementAgent:
    def __init__(self) -> None:
        cfg = load_agent_config("requirement")
        self._schema = cfg.get("output_schema", CANONICAL_SCHEMA) if cfg else CANONICAL_SCHEMA
        self._critical_fields = (
            cfg.get("critical_fields", CANONICAL_CRITICAL_FIELDS)
            if cfg
            else CANONICAL_CRITICAL_FIELDS
        )
        self._min_fr = cfg.get("parameters", {}).get("min_functional_requirements", 3) if cfg else 3
        self._min_tr = cfg.get("parameters", {}).get("min_technical_requirements", 1) if cfg else 1
        raw_prompt = cfg.get("system_prompt", "") if cfg else ""
        if isinstance(raw_prompt, list):
            instructions = raw_prompt
        elif isinstance(raw_prompt, str) and raw_prompt.strip():
            instructions = [line.strip() for line in raw_prompt.strip().split("\n") if line.strip()]
        else:
            instructions = [
                "Extract all required fields from user input.",
                "Prioritize functional requirements by business impact.",
                "Identify implicit requirements the user may have overlooked.",
                "Always output valid, complete JSON with no prose.",
            ]

        self._agno = Agent(
            name="requirement_analyst",
            role="Senior IT Business Analyst",
            description="Collect complete, structured requirements for IT document generation",
            instructions=instructions,
            model=get_model_adapter(),
            markdown=False,
        )

    async def collect(
        self,
        workflow_id: str,
        document_type: str,
        existing: dict[str, Any],
    ) -> RequirementResult:
        import json as _json
        import traceback

        log.info("requirement.collect.start", workflow_id=workflow_id)

        try:
            schema_json = _json.dumps(self._schema, indent=2, ensure_ascii=False)
            existing_json = _json.dumps(existing, ensure_ascii=False) if existing else "none"
        except (TypeError, ValueError) as exc:
            log.error(
                "requirement.collect.serialize_input_failed",
                workflow_id=workflow_id,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            raise

        prompt = (
            "You are a senior IT Business Analyst.\n"
            f"Document type: {document_type}\n"
            f"Existing context: {existing_json}\n\n"
            "Return ONLY a JSON object conforming to this schema:\n"
            f"{schema_json}\n\n"
            "Also extract 'search_terms': a list of specific technologies, products, "
            "standards, frameworks, and systems mentioned in the user input. "
            "Be specific: proper nouns, not generic concepts. Maximum 10 terms. "
            "Examples: 'sessionmanager', 'OAuth2', 'PostgreSQL', 'Kubernetes', 'ISO 27001'.\n\n"
            "Rules:\n"
            "- Use null for unknown string fields, [] for unknown lists.\n"
            f"- functional_requirements: at least {self._min_fr} items.\n"
            f"- technical_requirements: at least {self._min_tr} item.\n"
            "- All 'id' fields must be unique.\n"
            "- priority must be MUST, SHOULD, or COULD.\n"
            "- Do NOT include prose — only the JSON object."
        )

        try:
            response = await self._agno.arun(prompt)
        except (TypeError, ValueError) as exc:
            log.error(
                "requirement.collect.llm_call_failed",
                workflow_id=workflow_id,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            raise

        raw = extract_json(response.content)
        if raw is None:
            raise RequirementError(f"Non-JSON response: {response.content[:200]}")

        canon = normalize_to_canonical(raw)

        # Check critical fields using dot-path traversal
        missing: list[str] = []
        for dotpath in self._critical_fields:
            parts = dotpath.split(".")
            current: Any = canon
            for p in parts:
                if isinstance(current, dict):
                    current = current.get(p)
                else:
                    current = None
                    break
            if current is None or current == "" or current == [] or current == {}:
                missing.append(dotpath)

        confidence = max(0.0, 1.0 - len(missing) / len(self._critical_fields))

        try:
            canon_json = _json.dumps(canon, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            log.error(
                "requirement.collect.serialize_canon_failed",
                workflow_id=workflow_id,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            raise

        try:
            summary_resp = await self._agno.arun(
                f"Summarize in 3 sentences for a '{document_type}': {canon_json}"
            )
        except (TypeError, ValueError) as exc:
            log.error(
                "requirement.collect.summary_call_failed",
                workflow_id=workflow_id,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            raise

        log.info(
            "requirement.collect.done",
            workflow_id=workflow_id,
            missing=missing,
            confidence=confidence,
        )
        search_terms: list[str] = raw.get("search_terms", []) if isinstance(raw, dict) else []
        return RequirementResult(
            requirements=canon,
            summary=summary_resp.content.strip(),
            missing_fields=missing,
            confidence=confidence,
            search_terms=search_terms,
        )
