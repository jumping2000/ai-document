"""
Lead Writer Agent — generates final documents from enriched requirements.
Input  : enriched_requirements, document_type, quality_issues (for revisions)
Output : WriterResult(markdown, sections)
"""
import structlog
from dataclasses import dataclass
from typing import Any

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.skills.export.export_skill import ExportSkill

log = structlog.get_logger(__name__)


@dataclass
class WriterResult:
    markdown: str
    sections: list[str]
    docx_path: str
    pdf_path: str


class LeadWriterAgent:
    def __init__(self) -> None:
        self._jinja = Environment(
            loader=FileSystemLoader(settings.templates_base_path),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._exporter = ExportSkill()
        self._agno = Agent(
            name="lead_writer",
            role="Senior Technical Writer",
            goal="Produce complete, professional IT procurement documents",
            instructions=[
                "Write in clear, formal Italian or English as specified.",
                "Follow the document template structure strictly.",
                "Include all required sections: scope, requirements, SLA, security.",
                "Use numbered sections and subsections.",
                "Include a requirements traceability matrix.",
                "Cite standards and regulations correctly.",
            ],
            model=OpenAIChat(id=settings.default_ai_model),
            markdown=True,
        )

    async def write(
        self,
        enriched_requirements: dict[str, Any],
        document_type: str,
        quality_issues: list[str],
    ) -> WriterResult:
        log.info("writer.write.start", doc_type=document_type, revisions=len(quality_issues))

        revision_note = ""
        if quality_issues:
            revision_note = (
                f"\n\nIMPORTANT — Fix these issues from the quality review:\n"
                + "\n".join(f"- {i}" for i in quality_issues)
            )

        template_name = f"{document_type}/base.j2"
        try:
            template = self._jinja.get_template(template_name)
            template_content = template.render(**enriched_requirements)
        except Exception:
            template_content = _default_template(document_type)

        prompt = (
            f"Generate a complete '{document_type}' document.\n"
            f"Template structure:\n{template_content}\n"
            f"Requirements: {enriched_requirements}\n"
            f"{revision_note}\n\n"
            "Output the complete document in Markdown. Use ## for sections, ### for subsections."
        )
        response = await self._agno.arun(prompt)
        markdown = response.content.strip()

        sections = [
            line.lstrip("#").strip()
            for line in markdown.splitlines()
            if line.startswith("## ")
        ]

        project = enriched_requirements.get("project", {})
        title = project.get("title") or enriched_requirements.get("project_name") or document_type
        workflow_id = (
            enriched_requirements.get("_workflow_id")
            or enriched_requirements.get("workflow_id")
            or "unknown"
        )
        docx_path = await self._exporter.export_docx(markdown, title, workflow_id, document_type)
        pdf_path = await self._exporter.export_pdf(markdown, title, workflow_id, document_type)

        log.info("writer.write.done", sections=len(sections), docx=docx_path)
        return WriterResult(markdown=markdown, sections=sections,
                            docx_path=docx_path, pdf_path=pdf_path)


def _default_template(document_type: str) -> str:
    if document_type == "capitolato":
        return """
# Capitolato Tecnico — {{ project_name }}
## 1. Premessa e Contesto
## 2. Oggetto della Fornitura
## 3. Requisiti Funzionali
## 4. Requisiti Non Funzionali
## 5. Livelli di Servizio (SLA)
## 6. Sicurezza e Conformità
## 7. Integrazioni e Interoperabilità
## 8. Architettura Target
## 9. Piano di Progetto
## 10. Criteri di Accettazione
## 11. Allegati
"""
    return """
# Documento Requisiti Tecnici — {{ project_name }}
## 1. Scope
## 2. Requisiti Funzionali
## 3. Requisiti Non Funzionali
## 4. Architettura
## 5. Sicurezza
## 6. Testing e Acceptance
"""
