from __future__ import annotations

import asyncio
import uuid
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

import sys
from types import ModuleType, SimpleNamespace

# Stub structlog early so importing app.main doesn't fail in test env
structlog_mod = ModuleType("structlog")
structlog_mod.get_logger = lambda _name=None: SimpleNamespace(info=lambda *a, **k: None, debug=lambda *a, **k: None, error=lambda *a, **k: None)
sys.modules["structlog"] = structlog_mod

import os
os.environ["SECRET_KEY"] = "s" * 32
os.environ["JWT_SECRET_KEY"] = "j" * 32
os.environ["DEFAULT_AI_PROVIDER"] = "openai"

# Insert a lightweight stub for app.db.session to avoid creating real DB engine at import time
db_session_stub = ModuleType("app.db.session")
db_session_stub.AsyncSessionLocal = None
async def _dummy_get_db():
    if False:
        yield
    return
db_session_stub.get_db = _dummy_get_db
sys.modules["app.db.session"] = db_session_stub

# Minimal stubs for heavy third-party libs used at import-time
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
class _Document:
    def __init__(self, *args, **kwargs) -> None:
        self.styles = {}
        self.sections = []
    def add_heading(self, *args, **kwargs):
        return None
    def add_paragraph(self, *args, **kwargs):
        return SimpleNamespace(add_run=lambda *a, **k: SimpleNamespace())
    def save(self, *args, **kwargs) -> None:
        return None
docx_module.Document = _Document
sys.modules["docx"] = docx_module
docx_enum_module = ModuleType("docx.enum")
docx_enum_text_module = ModuleType("docx.enum.text")
docx_shared_module = ModuleType("docx.shared")
class _WDAlignParagraph:
    CENTER = "center"
def _inches(value):
    return value
def _pt(value):
    return value
class _RGBColor:
    def __init__(self, *args, **kwargs) -> None:
        pass
docx_enum_text_module.WD_ALIGN_PARAGRAPH = _WDAlignParagraph
docx_shared_module.Inches = _inches
docx_shared_module.Pt = _pt
docx_shared_module.RGBColor = _RGBColor
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

mcp_module = ModuleType("app.mcp.client.mcp_client")
class _MCPClient:
    async def search_documents(self, query: str, limit: int = 5, filters: dict | None = None):
        return []
    async def chat(self, message: str, kb_id: str | None = None, top_k: int = 6):
        return {"answer": "", "sources": [], "search_query": ""}
mcp_module.MCPClient = _MCPClient
mcp_module.MCPError = type("MCPError", (Exception,), {})
sys.modules["app.mcp.client.mcp_client"] = mcp_module

from app.main import app
from app.db import models as db_models
from app import db as db_module
from app.api.routes import workflow as workflow_route


@pytest.mark.asyncio
async def test_start_workflow_persists_row(monkeypatch) -> None:
    # Create in-memory SQLite async engine and sessionmaker for test
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    TestSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(db_models.Base.metadata.create_all)

    # Override AsyncSessionLocal used by routes/background tasks
    # Ensure the route module uses the test sessionmaker for background tasks
    monkeypatch.setattr(db_module.session, "AsyncSessionLocal", TestSessionLocal)
    monkeypatch.setattr(workflow_route, "AsyncSessionLocal", TestSessionLocal)

    # Override dependency get_db
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as s:
            yield s

    app.dependency_overrides[workflow_route.get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        payload = {
            "document_type": "capitolato",
            "title": "Test Persist",
            "raw_description": "Questo è un test per la persistenza della workflow",
            "form_data": {},
        }
        resp = await client.post("/api/v1/workflow/start", json=payload)
        assert resp.status_code == 202
        data = resp.json()
        wf_id = data.get("workflow_id")
        assert wf_id is not None

        # poll DB for terminal state (COMPLETED or FAILED) with timeout
        deadline = asyncio.get_event_loop().time() + 5.0
        state = None
        while asyncio.get_event_loop().time() < deadline:
            async with TestSessionLocal() as s:
                try:
                    wf = await s.get(db_models.Workflow, uuid.UUID(wf_id))
                except Exception:
                    wf = None
                if wf and wf.state in ("COMPLETED", "FAILED"):
                    state = wf.state
                    break
            await asyncio.sleep(0.1)

        assert state in ("COMPLETED", "FAILED")
