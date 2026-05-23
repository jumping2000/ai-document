"""
Requirement Agent — collects and structures user requirements.
Input  : document_type, existing partial requirements
Output : RequirementResult(requirements, summary, missing_fields, confidence)
"""
import json
import re
from dataclasses import dataclass
from typing import Any

import structlog
from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.core.config import settings

log = structlog.get_logger(__name__)

REQUIREMENT_FIELDS = [
    "project_name", "project_scope", "stakeholders", "end_users",
    "functional_requirements", "non_functional_requirements",
    "sla", "kpi", "security_requirements", "compliance",
    "integrations", "constraints", "target_architecture",
    "timeline", "budget_range", "document_language",
]

CRITICAL_FIELDS = [
    "project_name", "project_scope", "functional_requirements",
    "security_requirements", "sla", "target_architecture",
]


@dataclass
class RequirementResult:
    requirements: dict[str, Any]
    summary: str
    missing_fields: list[str]
    confidence: float


class RequirementError(Exception):
    pass


class RequirementAgent:
    def __init__(self) -> None:
        self._agno = Agent(
            name="requirement_analyst",
            role="Senior IT Business Analyst",
            goal="Collect complete, structured requirements for IT document generation",
            instructions=[
                "Extract all required fields from user input.",
                "Prioritize functional requirements by business impact.",
                "Identify implicit requirements the user may have overlooked.",
                "Always output valid, complete JSON with no prose.",
            ],
            model=OpenAIChat(id=settings.default_ai_model),
            markdown=False,
        )

    async def collect(
        self,
        workflow_id: str,
        document_type: str,
        existing: dict[str, Any],
    ) -> RequirementResult:
        log.info("requirement.collect.start", workflow_id=workflow_id)

        prompt = (
            "You are a senior IT Business Analyst. "
            f"Document type: {document_type}\n"
            f"Existing: {existing or 'none'}\n\n"
            f"Return ONLY a JSON object with keys: {REQUIREMENT_FIELDS}.\n"
            "Use null for unknown fields, [] for empty lists."
        )
        response = await self._agno.arun(prompt)
        match = re.search(r"\{.*\}", response.content, re.DOTALL)
        if not match:
            raise RequirementError(f"Non-JSON response: {response.content[:200]}")

        data: dict[str, Any] = json.loads(match.group())
        missing = [f for f in CRITICAL_FIELDS if not data.get(f)]
        confidence = max(0.0, 1.0 - len(missing) / len(REQUIREMENT_FIELDS))

        summary_resp = await self._agno.arun(
            f"Summarize in 3 sentences for a '{document_type}': {data}"
        )

        log.info("requirement.collect.done", workflow_id=workflow_id, missing=missing)
        return RequirementResult(
            requirements=data,
            summary=summary_resp.content.strip(),
            missing_fields=missing,
            confidence=confidence,
        )
