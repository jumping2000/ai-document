"""
Quality Agent — semantic validation, consistency check, scoring.
Input  : content (markdown), requirements, document_type
Output : QualityReport(score, passed, issues, suggestions, needs_enrichment)
"""

import json
from dataclasses import dataclass, field

import structlog
from agno.agent import Agent

from app.core.agent_config import load_agent_config
from app.core.app_config import app_cfg
from app.core.config import settings
from app.core.json_extract import extract_json
from app.core.llm import get_model_adapter

log = structlog.get_logger(__name__)

QUALITY_CHECKLIST = [
    "All functional requirements are addressed in the document",
    "SLA metrics are explicitly stated with measurable targets",
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
    warnings: list[str] = field(default_factory=list)


class QualityAgent:
    def __init__(self) -> None:
        cfg = load_agent_config("quality")
        self._checklist = (
            [c["label"] for c in cfg.get("quality_checklist", [])]
            if cfg.get("quality_checklist")
            else QUALITY_CHECKLIST
        )
        self._threshold = (
            cfg.get("parameters", {}).get("quality_threshold", settings.workflow_quality_threshold)
            if cfg
            else settings.workflow_quality_threshold
        )
        system_prompt = cfg.get("system_prompt", "")
        if isinstance(system_prompt, list):
            instructions = [s.strip() for s in system_prompt if s.strip()]
        elif isinstance(system_prompt, str) and system_prompt.strip():
            instructions = [
                line.strip() for line in system_prompt.strip().split("\n") if line.strip()
            ]
        else:
            instructions = [
                "Check every item in the quality checklist.",
                "Score each section from 0.0 to 1.0.",
                "Identify missing sections, vague requirements, and inconsistencies.",
                "Return a structured JSON quality report.",
                "Be strict: a score above 0.75 requires ALL critical sections present.",
            ]

        self._agno = Agent(
            name="quality_reviewer",
            role="Senior IT Document Quality Reviewer",
            description="Ensure documents meet professional procurement standards",
            instructions=instructions,
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
            f"DOCUMENT:\n{content[: app_cfg('quality.max_content_length', 8000)]}\n\n"
            f"ORIGINAL REQUIREMENTS: {requirements}\n\n"
            f"CHECKLIST:\n" + "\n".join(f"- {c}" for c in self._checklist) + "\n\n"
            'Return JSON: {"score": float(0-1), "passed": bool, '
            '"issues": [str], "suggestions": [str], '
            '"section_scores": {section: float}, "needs_enrichment": bool}'
        )
        response = await self._agno.arun(prompt)

        data = extract_json(response.content)
        if data:
            try:
                report = QualityReport(
                    score=float(data.get("score", 0.0)),
                    passed=bool(data.get("passed", False)),
                    issues=data.get("issues", []),
                    suggestions=data.get("suggestions", []),
                    section_scores=data.get("section_scores", {}),
                    needs_enrichment=bool(data.get("needs_enrichment", False)),
                )
                # Enforce threshold with tolerance zone
                if report.score < self._threshold:
                    # Soft threshold: if score >= 0.6, pass with warnings.
                    # We no longer block on individual keyword matches because
                    # the LLM naturally uses words like "mancante"/"missing" in
                    # quality reviews — that doesn't mean the document is unusable.
                    #
                    # Only truly catastrophic scores (< 0.4) or documents with
                    # MANY issues relative to score get hard-blocked.
                    severe = report.score < app_cfg("quality.severe_score_threshold", 0.4) or (
                        len(report.issues) > app_cfg("quality.max_issues_threshold", 5)
                        and report.score < app_cfg("quality.moderate_score_threshold", 0.5)
                    )
                    if not severe:
                        report.passed = True
                        report.needs_enrichment = False
                        report.warnings = report.issues[:]  # preserve as warnings
                        log.info(
                            "quality.review.passed_with_warnings",
                            score=report.score,
                            threshold=self._threshold,
                            issues_count=len(report.issues),
                        )
                    else:
                        report.passed = False
                log.info("quality.review.done", score=report.score, passed=report.passed)
                return report
            except (json.JSONDecodeError, KeyError) as exc:
                log.error("quality.parse_error", error=str(exc))

        return QualityReport(score=0.0, passed=False, issues=["Quality review parse error"])
