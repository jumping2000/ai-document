from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace

import pytest


def _install_import_stubs() -> None:
    class _Logger:
        def __getattr__(self, _name: str):
            return lambda *args, **kwargs: None

    structlog_module = ModuleType("structlog")
    structlog_module.get_logger = lambda _name=None: _Logger()
    sys.modules["structlog"] = structlog_module

    sqlalchemy_module = ModuleType("sqlalchemy")
    sqlalchemy_ext_module = ModuleType("sqlalchemy.ext")
    sqlalchemy_asyncio_module = ModuleType("sqlalchemy.ext.asyncio")
    sqlalchemy_asyncio_module.AsyncSession = object
    sys.modules["sqlalchemy"] = sqlalchemy_module
    sys.modules["sqlalchemy.ext"] = sqlalchemy_ext_module
    sys.modules["sqlalchemy.ext.asyncio"] = sqlalchemy_asyncio_module

    config_module = ModuleType("app.core.config")
    config_module.settings = SimpleNamespace(
        default_ai_model="gpt-4o",
        default_ai_provider="openai",
        openai_api_key="sk-test",
        workflow_quality_threshold=0.75,
        templates_base_path="",
        documents_base_path="",
        mcp_server_url="http://localhost:8001",
        mcp_api_key="",
        mcp_timeout_seconds=30,
        mcp_max_retries=3,
    )
    sys.modules["app.core.config"] = config_module

    agno_module = ModuleType("agno")
    agno_agent_module = ModuleType("agno.agent")
    agno_openai_module = ModuleType("agno.models.openai")

    class _Agent:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def arun(self, _prompt: str):
            return SimpleNamespace(content="{}")

    class _OpenAIChat:
        def __init__(self, *args, **kwargs) -> None:
            pass

    agno_agent_module.Agent = _Agent
    agno_openai_module.OpenAIChat = _OpenAIChat
    sys.modules["agno"] = agno_module
    sys.modules["agno.agent"] = agno_agent_module
    sys.modules["agno.models.openai"] = agno_openai_module

    jinja2_module = ModuleType("jinja2")

    class _Template:
        def render(self, **_kwargs) -> str:
            return ""

    class _Environment:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def get_template(self, _name: str) -> _Template:
            return _Template()

    class _FileSystemLoader:
        def __init__(self, *args, **kwargs) -> None:
            pass

    def _select_autoescape(_args):
        return False

    jinja2_module.Environment = _Environment
    jinja2_module.FileSystemLoader = _FileSystemLoader
    jinja2_module.select_autoescape = _select_autoescape
    sys.modules["jinja2"] = jinja2_module

    docx_module = ModuleType("docx")
    docx_enum_module = ModuleType("docx.enum")
    docx_enum_text_module = ModuleType("docx.enum.text")
    docx_shared_module = ModuleType("docx.shared")

    class _Document:
        def __init__(self, *args, **kwargs) -> None:
            self.styles = {
                "Normal": SimpleNamespace(font=SimpleNamespace(name="", size=0)),
                "Title": SimpleNamespace(font=SimpleNamespace(size=0, bold=False, color=SimpleNamespace(rgb=None))),
                "Body Text": SimpleNamespace(),
            }
            self.sections = []

        def add_heading(self, *args, **kwargs):
            return None

        def add_paragraph(self, *args, **kwargs):
            return SimpleNamespace(
                add_run=lambda *run_args, **run_kwargs: SimpleNamespace(),
                style=None,
                paragraph_format=SimpleNamespace(left_indent=None),
            )

        def save(self, *args, **kwargs) -> None:
            return None

    class _WDAlignParagraph:
        CENTER = "center"

    def _inches(value):
        return value

    def _pt(value):
        return value

    class _RGBColor:
        def __init__(self, *args, **kwargs) -> None:
            pass

    docx_module.Document = _Document
    docx_enum_text_module.WD_ALIGN_PARAGRAPH = _WDAlignParagraph
    docx_shared_module.Inches = _inches
    docx_shared_module.Pt = _pt
    docx_shared_module.RGBColor = _RGBColor
    sys.modules["docx"] = docx_module
    sys.modules["docx.enum"] = docx_enum_module
    sys.modules["docx.enum.text"] = docx_enum_text_module
    sys.modules["docx.shared"] = docx_shared_module

    reportlab_module = ModuleType("reportlab")
    reportlab_lib_module = ModuleType("reportlab.lib")
    reportlab_colors_module = ModuleType("reportlab.lib.colors")
    reportlab_pagesizes_module = ModuleType("reportlab.lib.pagesizes")
    reportlab_styles_module = ModuleType("reportlab.lib.styles")
    reportlab_units_module = ModuleType("reportlab.lib.units")
    reportlab_platypus_module = ModuleType("reportlab.platypus")

    reportlab_colors_module.black = "black"
    reportlab_pagesizes_module.A4 = "A4"
    reportlab_styles_module.getSampleStyleSheet = lambda: {}
    reportlab_styles_module.ParagraphStyle = lambda *args, **kwargs: SimpleNamespace()
    reportlab_units_module.cm = 1

    class _Flowable:
        def __init__(self, *args, **kwargs) -> None:
            pass

    reportlab_platypus_module.HRFlowable = _Flowable
    reportlab_platypus_module.Paragraph = _Flowable
    reportlab_platypus_module.SimpleDocTemplate = _Flowable
    reportlab_platypus_module.Spacer = _Flowable
    reportlab_platypus_module.Table = _Flowable
    reportlab_platypus_module.TableStyle = _Flowable

    sys.modules["reportlab"] = reportlab_module
    sys.modules["reportlab.lib"] = reportlab_lib_module
    sys.modules["reportlab.lib.colors"] = reportlab_colors_module
    sys.modules["reportlab.lib.pagesizes"] = reportlab_pagesizes_module
    sys.modules["reportlab.lib.styles"] = reportlab_styles_module
    sys.modules["reportlab.lib.units"] = reportlab_units_module
    sys.modules["reportlab.platypus"] = reportlab_platypus_module

    mcp_module = ModuleType("app.mcp.client.mcp_client")

    class _MCPClient:
        async def search_documents(self, query: str, limit: int = 5, filters: dict | None = None):
            return []
        async def chat(self, message: str, kb_id: str | None = None, top_k: int = 6):
            return {"answer": "", "sources": [], "search_query": ""}

    mcp_module.MCPClient = _MCPClient
    mcp_module.MCPError = type("MCPError", (Exception,), {})
    sys.modules["app.mcp.client.mcp_client"] = mcp_module


def _load_runner_module(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    templates_path = Path(__file__).resolve().parents[1] / "templates"

    monkeypatch.setenv("SECRET_KEY", "s" * 32)
    monkeypatch.setenv("JWT_SECRET_KEY", "j" * 32)
    monkeypatch.setenv("DOCUMENTS_BASE_PATH", str(tmp_path / "documents"))
    monkeypatch.setenv("TEMPLATES_BASE_PATH", str(templates_path))

    for module_name in (
        "app.core.config",
        "app.agents.lead_writer.agent",
        "app.workflows.execution.runner",
    ):
        sys.modules.pop(module_name, None)

    _install_import_stubs()

    return importlib.import_module("app.workflows.execution.runner")


@pytest.mark.asyncio
async def test_runner_completes_workflow_with_real_agent_contracts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner_module = _load_runner_module(monkeypatch, tmp_path)

    complete_requirements = {
        "project": {"title": "Sistema ERP", "organization": "Comune di Roma"},
        "scope": {"objectives": ["Digitalizzare i processi"]},
        "functional_requirements": [
            {"id": "FR-001"},
            {"id": "FR-002"},
            {"id": "FR-003"},
        ],
        "technical_requirements": [{"id": "TR-001"}],
        "sla": {"availability": "99.9%"},
        "security_compliance": {"standards": ["ISO 27001"]},
        "timeline": {"go_live": "2026-01-01"},
    }

    class FakeRequirementAgent:
        async def collect(self, workflow_id: str, document_type: str, existing: dict):
            return SimpleNamespace(
                requirements=complete_requirements,
                summary="summary",
                missing_fields=[],
                confidence=1.0,
            )

    class FakeProcurementAgent:
        async def enrich(self, requirements: dict, document_type: str):
            return SimpleNamespace(
                enriched=requirements,
                sources=["kb"],
                standards_applied=["ISO 27001"],
            )

    class FakeLeadWriterAgent:
        async def write(
            self,
            enriched_requirements: dict,
            document_type: str,
            quality_issues: list[str],
        ):
            return SimpleNamespace(
                markdown=(
                    "# Documento\n\n"
                    "## Oggetto\nTest\n\n"
                    "## Requisiti Funzionali\nTest\n\n"
                    "## Requisiti Tecnici\nTest\n\n"
                    "## Sicurezza\nTest\n\n"
                    "## SLA\nTest\n\n"
                    "## Integrazioni\nTest\n\n"
                    "## Piano\nTest\n\n"
                    "## Criteri\nTest\n"
                ),
                sections=["Oggetto"],
                docx_path="doc.docx",
                pdf_path="doc.pdf",
            )

    class FakeQualityAgent:
        async def review(self, content: str, requirements: dict, document_type: str):
            return SimpleNamespace(
                score=0.92,
                passed=True,
                issues=[],
                suggestions=[],
                section_scores={"overall": 0.92},
                needs_enrichment=False,
            )

    monkeypatch.setattr(runner_module, "RequirementAgent", FakeRequirementAgent)
    monkeypatch.setattr(runner_module, "ProcurementAgent", FakeProcurementAgent)
    monkeypatch.setattr(runner_module, "LeadWriterAgent", FakeLeadWriterAgent)
    monkeypatch.setattr(runner_module, "QualityAgent", FakeQualityAgent)

    runner = runner_module.WorkflowRunner(db=object())

    result = await runner.run(
        workflow_id="wf-001",
        document_type="capitolato",
        initial_input={"raw_description": "Documento di test"},
    )

    assert result == {"status": "completed", "quality_score": 0.92}
