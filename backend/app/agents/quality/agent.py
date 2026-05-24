"""
Quality Agent — semantic validation, consistency check, scoring.
Input  : content (markdown), requirements, document_type
Output : QualityReport(score, passed, issues, suggestions, needs_enrichment)
"""
import json
import re
import structlog
from dataclasses import dataclass, field

from agno.agent import Agent
from app.core.llm import get_model_adapter

from app.core.config import settings

log = structlog.get_logger(__name__)

QUALITY_CHECKLIST = [
    "All functional requirements are addressed in the document",
    "SLA targets are explicitly stated with numeric values",
    "Security requirements reference at least one standard (ISO, OWASP, GDPR)",
    "Document has a coherent structure with numbered sections",
    "No contradictions between sections",
    "Technical constraints are reflected in the architecture section",
    "Stakeholders and roles are defined",
    "Acceptance criteria are measurable",
]


@dataclass
class QualityReport:
    score: float
    passed: bool
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    section_scores: dict[str, float] = field(default_factory=dict)
    needs_enrichment: bool = False


class QualityAgent:
    def __init__(self) -> None:
        self._agno = Agent(
            name="quality_reviewer",
            role="Senior IT Document Quality Reviewer",
            description="Ensure documents meet professional procurement standards",
            instructions=[
                "Check every item in the quality checklist.",
                "Score each section from 0.0 to 1.0.",
                "Identify missing sections, vague requirements, and inconsistencies.",
                "Return a structured JSON quality report.",
                "Be strict: a score above 0.75 requires ALL critical sections present.",
            ],
            model=get_model_adapter(),
            markdown=False,
        )

    async def review(
        self,
        content: str,
        requirements: dict,
        document_type: str,
    ) -> QualityReport:
        log.info("quality.review.start", doc_type=document_type, content_len=len(content))

        prompt = (
            f"Review this '{document_type}' document against requirements.\n\n"
            f"DOCUMENT:\n{content[:8000]}\n\n"
            f"ORIGINAL REQUIREMENTS: {requirements}\n\n"
            f"CHECKLIST:\n" + "\n".join(f"- {c}" for c in QUALITY_CHECKLIST) + "\n\n"
            "Return JSON: {\"score\": float(0-1), \"passed\": bool, "
            "\"issues\": [str], \"suggestions\": [str], "
            "\"section_scores\": {section: float}, \"needs_enrichment\": bool}"
        )
        response = await self._agno.arun(prompt)
        match = re.search(r"\{.*\}", response.content, re.DOTALL)

        if match:
            try:
                data = json.loads(match.group())
                report = QualityReport(
                    score=float(data.get("score", 0.0)),
                    passed=bool(data.get("passed", False)),
                    issues=data.get("issues", []),
                    suggestions=data.get("suggestions", []),
                    section_scores=data.get("section_scores", {}),
                    needs_enrichment=bool(data.get("needs_enrichment", False)),
                )
                # Enforce threshold
                if report.score < settings.workflow_quality_threshold:
                    report.passed = False
                log.info("quality.review.done", score=report.score, passed=report.passed)
                return report
            except (json.JSONDecodeError, KeyError) as exc:
                log.error("quality.parse_error", error=str(exc))

        return QualityReport(score=0.0, passed=False, issues=["Quality review parse error"])
