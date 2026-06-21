# AI Document Platform — API Reference

> **Version**: 1.0.0  
> **Last Updated**: 2026-06-21  
> **Stack**: Python 3.11+ / FastAPI / SQLAlchemy 2.0 / Agno / React

---

## Table of Contents

1. [Core Configuration](#1-core-configuration)
2. [LLM Factory](#2-llm-factory)
3. [Agents](#3-agents)
   - [RequirementAgent](#31-requirementagent)
   - [ProcurementAgent](#32-procurementagent)
   - [OrchestratorAgent](#33-orchestratoragent)
   - [LeadWriterAgent](#34-leadwriteragent)
   - [QualityAgent](#35-qualityagent)
4. [State Machine](#4-state-machine)
   - [WorkflowState](#41-workflowstate)
   - [WorkflowTrigger](#42-workflowtrigger)
   - [WorkflowContext](#43-workflowcontext)
   - [Transition](#44-transition)
   - [StateMachine](#45-statemachine)
5. [Workflow Runner](#5-workflow-runner)
   - [WorkflowRunner](#51-workflowrunner)
   - [SSE Functions](#52-sse-functions)
6. [MCP Client](#6-mcp-client)
   - [MCPClient](#61-mcpclient)
   - [MCPError](#62-mcperror)
7. [Skills](#7-skills)
   - [ExportSkill](#71-exportskill)
   - [ValidationSkill](#72-validationskill)
   - [RetrievalSkill](#73-retrievalskill)
8. [Database Models](#8-database-models)
   - [User](#81-user)
   - [Workflow](#82-workflow)
   - [WorkflowState (DB)](#83-workflowstate-db)
   - [AgentOutput](#84-agentoutput)
   - [Document](#85-document)
   - [QualityReport (DB)](#86-qualityreport-db)
   - [AuditLog](#87-auditlog)
9. [API Routes](#9-api-routes)
   - [POST /workflow/start](#post-workflowstart)
   - [GET /workflow/{id}](#get-workflowid)
   - [POST /workflow/{id}/approve](#post-workflowidapprove)
   - [POST /workflow/{id}/retry](#post-workflowidretry)
   - [GET /workflow/{id}/documents](#get-workflowiddocuments)
   - [GET /workflow/{id}/quality-report](#get-workflowidquality-report)
10. [WebSocket Events](#10-websocket-events)
11. [UML Diagrams](#11-uml-diagrams)

---

## 1. Core Configuration

**Module**: `backend/app/core/config.py`

### class Settings(BaseSettings)

Pydantic Settings class that reads configuration from environment variables and `.env` file.

```python
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Literal
```

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `app_name` | `str` | `"AI Document Platform"` | Application name |
| `app_env` | `Literal["development", "styling", "production"]` | `"development"` | Environment mode |
| `debug` | `bool` | `False` | Debug mode flag |
| `secret_key` | `str` | *(required, min 32 chars)* | Application secret key |
| `api_v1_prefix` | `str` | `"/api/v1"` | API version prefix |
| `database_url` | `str` | `"postgresql+asyncpg://..."` | PostgreSQL connection string |
| `database_pool_size` | `int` | `10` | Connection pool size |
| `database_max_overflow` | `int` | `20` | Max overflow connections |
| `redis_url` | `str` | `"redis://localhost:6379/0"` | Redis connection string |
| `jwt_secret_key` | `str` | *(required, min 32 chars)* | JWT signing key |
| `jwt_algorithm` | `str` | `"HS256"` | JWT algorithm |
| `jwt_access_token_expire_minutes` | `int` | `480` | Token expiry (8 hours) |
| `openai_api_key` | `str` | `""` | OpenAI API key |
| `anthropic_api_key` | `str` | `""` | Anthropic API key |
| `openrouter_api_key` | `str` | `""` | OpenRouter API key |
| `ollama_url` | `str` | `"http://localhost:11434"` | Ollama server URL |
| `ollama_api_key` | `str` | `""` | Ollama API key |
| `default_ai_model` | `str` | `"gpt-4o"` | Default LLM model |
| `default_ai_provider` | `Literal["openai", "anthropic", "openrouter", "ollama"]` | `"openai"` | LLM provider |
| `mcp_server_url` | `str` | `"http://localhost:8100/sse"` | MCP server URL |
| `mcp_api_key` | `str` | `""` | MCP API key |
| `mcp_timeout_seconds` | `int` | `30` | MCP request timeout |
| `mcp_max_retries` | `int` | `3` | MCP retry count |
| `mcp_default_kb_id` | `str` | `"default"` | Default knowledge base ID |
| `workflow_max_retries` | `int` | `3` | Max workflow retries |
| `workflow_quality_threshold` | `float` | `0.75` | Quality pass threshold (0.0–1.0) |
| `workflow_timeout_minutes` | `int` | `60` | Workflow timeout |
| `documents_base_path` | `str` | `"/app/documents"` | Document storage path |
| `templates_base_path` | `str` | `"/app/app/templates"` | Jinja2 templates path |
| `log_level` | `str` | `"INFO"` | Logging level |
| `otlp_endpoint` | `str` | `"http://localhost:4317"` | OpenTelemetry endpoint |
| `prometheus_enabled` | `bool` | `True` | Prometheus metrics |

#### Validators

```python
@field_validator("jwt_secret_key", "secret_key", mode="before")
@classmethod
def pad_secret(cls, v: str) -> str:
    """Ensure minimum length in dev by padding — raise in production."""
    if len(v) < 32:
        return v.ljust(32, "0")
    return v
```

#### Functions

```python
@lru_cache
def get_settings() -> Settings:
    """Cached singleton for application settings."""
    return Settings()

settings = get_settings()  # Module-level singleton
```

---

## 2. LLM Factory

**Module**: `backend/app/core/llm.py`

### get_model_adapter()

Factory function that returns an Agno-compatible model instance based on configuration.

```python
def get_model_adapter() -> Any:
    """
    Returns an agno-compatible model instance.
    
    Supported providers:
    - "openai"    → agno.models.openai.OpenAIChat
    - "anthropic" → agno.models.anthropic.claude.Claude
    - "openrouter"→ agno.models.openrouter.openrouter.OpenRouter
    - "ollama"    → agno.models.ollama.chat.Ollama
    
    Returns:
        Model instance compatible with agno.Agent
        
    Raises:
        ImportError: If provider SDK is not installed
        ValueError: If provider is unsupported
    """
```

#### Provider Mapping

| Provider | Class | Key Parameters |
|----------|-------|----------------|
| `openai` | `OpenAIChat` | `id=settings.default_ai_model`, `api_key=settings.openai_api_key` |
| `anthropic` | `Claude` | `id=settings.default_ai_model`, `api_key=settings.anthropic_api_key` |
| `openrouter` | `OpenRouter` | `id=settings.default_ai_model`, `api_key=settings.openrouter_api_key` |
| `ollama` | `Ollama` | `id=settings.default_ai_model`, `host=settings.ollama_url`, `api_key=settings.ollama_api_key` |

---

## 3. Agents

### 3.1 RequirementAgent

**Module**: `backend/app/agents/requirement/agent.py`

Collects and structures user requirements for document generation.

#### Constants

```python
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
```

#### class RequirementResult

```python
@dataclass
class RequirementResult:
    requirements: dict[str, Any]      # Structured requirements dict
    summary: str                       # 3-sentence summary
    missing_fields: list[str]          # Critical fields not provided
    confidence: float                  # 0.0–1.0 completeness score
```

#### class RequirementError(Exception)

Raised when the agent fails to parse a valid JSON response.

#### class RequirementAgent

```python
class RequirementAgent:
    def __init__(self) -> None:
        """
        Initialize with agno.Agent configured as:
        - name: "requirement_analyst"
        - role: "Senior IT Business Analyst"
        - model: get_model_adapter()
        """
    
    async def collect(
        self,
        workflow_id: str,
        document_type: str,
        existing: dict[str, Any],
    ) -> RequirementResult:
        """
        Collect and structure requirements from user input.
        
        Args:
            workflow_id: Unique workflow identifier
            document_type: Type of document (e.g., "capitolato", "requisiti")
            existing: Partial requirements already provided by user
            
        Returns:
            RequirementResult with structured requirements
            
        Raises:
            RequirementError: If LLM response is not valid JSON
            
        Process:
            1. Send prompt to LLM with field specifications
            2. Parse JSON response
            3. Identify missing critical fields
            4. Calculate confidence score: 1.0 - (missing_count / total_fields)
            5. Generate 3-sentence summary
        """
```

---

### 3.2 ProcurementAgent

**Module**: `backend/app/agents/procurement/agent.py`

Enriches requirements with standards, regulations, and best practices via MCP/RAG.

#### class ProcurementResult

```python
@dataclass
class ProcurementResult:
    enriched: dict[str, Any]         # Enriched requirements
    sources: list[str]               # KB sources used
    standards_applied: list[str]     # Standards referenced (ISO, GDPR, etc.)
```

#### class ProcurementAgent

```python
class ProcurementAgent:
    def __init__(self) -> None:
        """
        Initialize with:
        - MCPClient for knowledge base access
        - agno.Agent configured as:
          - name: "procurement_specialist"
          - role: "IT Procurement Specialist"
          - Instructions: ISO 27001, ISO 9001, GDPR, OWASP, CIS, D.Lgs. 36/2023
        """
    
    async def enrich(
        self,
        requirements: dict[str, Any],
        document_type: str,
    ) -> ProcurementResult:
        """
        Enrich requirements with standards and regulations.
        
        Args:
            requirements: Structured requirements from RequirementAgent
            document_type: Type of document
            
        Returns:
            ProcurementResult with enriched requirements
            
        Process:
            1. Query MCP knowledge base for relevant standards
            2. Send prompt to LLM with requirements + KB context
            3. Parse JSON response with enriched data
        """
    
    async def _fetch_kb_context(
        self,
        requirements: dict,
        document_type: str,
    ) -> str:
        """
        Fetch relevant context from MCP knowledge base.
        
        Args:
            requirements: Requirements dict for query building
            document_type: Document type for context
            
        Returns:
            Concatenated content from KB search results
            
        Note:
            Returns fallback message if MCP is unavailable
        """
```

---

### 3.3 OrchestratorAgent

**Module**: `backend/app/agents/orchestrator/agent.py`

Controls the workflow state machine and coordinates all agents.

#### class OrchestratorAgent

```python
class OrchestratorAgent:
    def __init__(self, context: WorkflowContext, event_bus) -> None:
        """
        Initialize orchestrator with workflow context.
        
        Args:
            context: WorkflowContext with workflow state
            event_bus: Event emitter for SSE streaming
            
        Attributes:
            sm: StateMachine instance
            requirement_agent: RequirementAgent
            procurement_agent: ProcurementAgent
            lead_writer_agent: LeadWriterAgent
            quality_agent: QualityAgent
            _agno: Agent for validation decisions
        """
    
    async def run(self) -> WorkflowContext:
        """
        Execute the complete workflow.
        
        Returns:
            WorkflowContext with final state
            
        Process:
            1. Trigger START transition
            2. Loop until terminal state:
               - Execute current state handler
               - Handle exceptions with ERROR trigger
            3. Return final context
        """
    
    async def _step(self) -> None:
        """
        Execute one step based on current state.
        
        Dispatches to:
        - _run_briefing()      → BRIEFING state
        - _run_enrichment()    → ENRICHMENT state
        - _run_validation()    → VALIDATION state
        - _run_writing()       → WRITING state
        - _run_quality()       → QUALITY_ANALYSIS state
        """
    
    async def _run_briefing(self) -> None:
        """
        BRIEFING state handler.
        
        Calls RequirementAgent.collect() and transitions to ENRICHMENT.
        Emits: agent_start, agent_done, state_change
        """
    
    async def _run_enrichment(self) -> None:
        """
        ENRICHMENT state handler.
        
        Calls ProcurementAgent.enrich() and transitions to VALIDATION.
        Emits: agent_start, agent_done, state_change
        """
    
    async def _run_validation(self) -> None:
        """
        VALIDATION state handler.
        
        Validates completeness via LLM prompt.
        Transitions to WRITING if complete, or back to BRIEFING on failure.
        Emits: agent_start, validation_failed (if applicable), state_change
        """
    
    async def _run_writing(self) -> None:
        """
        WRITING state handler.
        
        Calls LeadWriterAgent.write() and transitions to QUALITY_ANALYSIS.
        Emits: agent_start, agent_done, state_change
        """
    
    async def _run_quality(self) -> None:
        """
        QUALITY_ANALYSIS state handler.
        
        Calls QualityAgent.review() and:
        - Transitions to COMPLETED if passed
        - Transitions to WRITING (retry) if writing issues
        - Transitions to ENRICHMENT (retry) if enrichment needed
        
        Emits: agent_start, quality_report, state_change
        """
    
    async def _emit(self, event_type: str, payload: dict) -> None:
        """
        Emit SSE event via event bus.
        
        Args:
            event_type: Event name (state_change, agent_start, etc.)
            payload: Event data
        """
```

---

### 3.4 LeadWriterAgent

**Module**: `backend/app/agents/lead_writer/agent.py`

Generates final documents from enriched requirements.

#### class WriterResult

```python
@dataclass
class WriterResult:
    markdown: str        # Generated markdown content
    sections: list[str]  # Extracted section headings
    docx_path: str       # Path to generated .docx file
    pdf_path: str        # Path to generated .pdf file
```

#### class LeadWriterAgent

```python
class LeadWriterAgent:
    def __init__(self) -> None:
        """
        Initialize with:
        - Jinja2 Environment for template rendering
        - ExportSkill for document conversion
        - agno.Agent configured as:
          - name: "lead_writer"
          - role: "Senior Technical Writer"
          - Instructions: Italian/English, formal style, numbered sections, traceability matrix
        """
    
    async def write(
        self,
        enriched_requirements: dict[str, Any],
        document_type: str,
        quality_issues: list[str],
    ) -> WriterResult:
        """
        Generate complete document from requirements.
        
        Args:
            enriched_requirements: Enriched requirements from ProcurementAgent
            document_type: Type of document (capitolato, requisiti)
            quality_issues: Issues from previous quality review (for revisions)
            
        Returns:
            WriterResult with markdown, sections, and file paths
            
        Process:
            1. Load Jinja2 template for document_type
            2. Render template with requirements
            3. Include revision notes if quality_issues provided
            4. Generate markdown via LLM
            5. Extract section headings
            6. Export to .docx and .pdf
        """
```

#### Default Templates

**Capitolato**:
```
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
```

**Requisiti Tecnici**:
```
# Documento Requisiti Tecnici — {{ project_name }}
## 1. Scope
## 2. Requisiti Funzionali
## 3. Requisiti Non Funzionali
## 4. Architettura
## 5. Sicurezza
## 6. Testing e Acceptance
```

---

### 3.5 QualityAgent

**Module**: `backend/app/agents/quality/agent.py`

Performs semantic validation, consistency checks, and scoring.

#### Quality Checklist

```python
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
```

#### class QualityReport

```python
@dataclass
class QualityReport:
    score: float                                    # 0.0–1.0 quality score
    passed: bool                                    # True if score >= threshold
    issues: list[str] = field(default_factory=list) # Issues found
    suggestions: list[str] = field(default_factory=list) # Improvement suggestions
    section_scores: dict[str, float] = field(default_factory=dict) # Per-section scores
    needs_enrichment: bool = False                  # True if re-enrichment needed
```

#### class QualityAgent

```python
class QualityAgent:
    def __init__(self) -> None:
        """
        Initialize with agno.Agent configured as:
        - name: "quality_reviewer"
        - role: "Senior IT Document Quality Reviewer"
        - Instructions: Check all checklist items, score 0.0–1.0, be strict
        """
    
    async def review(
        self,
        content: str,
        requirements: dict,
        document_type: str,
    ) -> QualityReport:
        """
        Review document quality against requirements.
        
        Args:
            content: Generated markdown content
            requirements: Original enriched requirements
            document_type: Type of document
            
        Returns:
            QualityReport with score, issues, and suggestions
            
        Process:
            1. Build prompt with document + requirements + checklist
            2. Send to LLM for review
            3. Parse JSON response
            4. Enforce quality_threshold from settings
            5. Determine if needs_enrichment or needs_rewriting
        """
```

---

## 4. State Machine

**Module**: `backend/app/workflows/state_machine/machine.py`

### 4.1 WorkflowState

```python
class WorkflowState(StrEnum):
    INIT = "INIT"                           # Initial state
    BRIEFING = "BRIEFING"                   # Collecting requirements
    ENRICHMENT = "ENRICHMENT"               # Enriching with standards
    VALIDATION = "VALIDATION"               # Validating completeness
    WRITING = "WRITING"                     # Generating document
    QUALITY_ANALYSIS = "QUALITY_ANALYSIS"   # Reviewing quality
    COMPLETED = "COMPLETED"                 # Successfully completed
    FAILED = "FAILED"                       # Failed after retries
```

### 4.2 WorkflowTrigger

```python
class WorkflowTrigger(StrEnum):
    START = "start"                                   # Begin workflow
    REQUIREMENTS_COLLECTED = "requirements_collected"  # Briefing done
    ENRICHMENT_DONE = "enrichment_done"               # Enrichment done
    VALIDATION_PASSED = "validation_passed"            # Validation OK
    VALIDATION_FAILED = "validation_failed"            # Validation failed
    WRITING_DONE = "writing_done"                     # Writing done
    QUALITY_PASSED = "quality_passed"                 # Quality OK
    QUALITY_FAILED_WRITING = "quality_failed_writing" # Quality failed (rewrite)
    QUALITY_FAILED_ENRICHMENT = "quality_failed_enrichment" # Quality failed (re-enrich)
    FATAL_ERROR = "fatal_error"                       # Unrecoverable error
    HUMAN_APPROVED = "human_approved"                 # Human approval
```

### 4.3 WorkflowContext

```python
@dataclass
class WorkflowContext:
    workflow_id: str                                    # Unique workflow ID
    document_type: str                                  # Document type
    state: WorkflowState = WorkflowState.INIT           # Current state
    retry_count: int = 0                               # Validation retry count
    writing_retry_count: int = 0                       # Writing retry count
    enrichment_retry_count: int = 0                    # Enrichment retry count
    max_retries: int = 3                               # Max retries allowed
    quality_threshold: float = 0.75                    # Quality pass threshold
    requirements: dict = field(default_factory=dict)   # Raw requirements
    enriched_requirements: dict = field(default_factory=dict) # Enriched requirements
    draft_content: str = ""                            # Generated markdown
    quality_score: float = 0.0                         # Final quality score
    quality_issues: list = field(default_factory=list) # Quality issues
    human_approval_required: bool = False              # Human-in-the-loop flag
    metadata: dict = field(default_factory=dict)       # Additional metadata
```

### 4.4 Transition

```python
@dataclass
class Transition:
    from_state: WorkflowState                           # Source state
    trigger: WorkflowTrigger                            # Trigger event
    to_state: WorkflowState                             # Target state
    guard: Callable[[WorkflowContext], bool] | None = None  # Condition function
    action: Callable[[WorkflowContext], None] | None = None # Side-effect function
```

### 4.5 StateMachine

```python
class StateMachine:
    """
    Deterministic, stateless state machine.
    All mutable state lives in WorkflowContext.
    """
    
    def __init__(self) -> None:
        """
        Initialize with all valid transitions:
        
        INIT → (START) → BRIEFING
        BRIEFING → (REQUIREMENTS_COLLECTED) → ENRICHMENT
        ENRICHMENT → (ENRICHMENT_DONE) → VALIDATION
        VALIDATION → (VALIDATION_PASSED) → WRITING
        VALIDATION → (VALIDATION_FAILED) → BRIEFING [guard: retries < max]
        VALIDATION → (VALIDATION_FAILED) → FAILED [guard: retries >= max]
        WRITING → (WRITING_DONE) → QUALITY_ANALYSIS
        QUALITY_ANALYSIS → (QUALITY_PASSED) → COMPLETED
        QUALITY_ANALYSIS → (QUALITY_FAILED_WRITING) → WRITING [guard: writing_retries < max]
        QUALITY_ANALYSIS → (QUALITY_FAILED_WRITING) → FAILED [guard: writing_retries >= max]
        QUALITY_ANALYSIS → (QUALITY_FAILED_ENRICHMENT) → ENRICHMENT [guard: enrichment_retries < max]
        QUALITY_ANALYSIS → (QUALITY_FAILED_ENRICHMENT) → FAILED [guard: enrichment_retries >= max]
        * → (FATAL_ERROR) → FAILED
        """
    
    def trigger(
        self,
        ctx: WorkflowContext,
        trigger: WorkflowTrigger,
    ) -> WorkflowState:
        """
        Execute a state transition.
        
        Args:
            ctx: WorkflowContext with current state
            trigger: Trigger to execute
            
        Returns:
            New WorkflowState
            
        Raises:
            ValueError: If no valid transition exists or all guards fail
            
        Side Effects:
            - Updates ctx.state
            - Increments retry counters on failure triggers
            - Executes transition action if defined
        """
    
    def can_trigger(
        self,
        ctx: WorkflowContext,
        trigger: WorkflowTrigger,
    ) -> bool:
        """
        Check if a trigger is valid from current state.
        
        Args:
            ctx: WorkflowContext with current state
            trigger: Trigger to check
            
        Returns:
            True if at least one transition matches and guard passes
        """
    
    @staticmethod
    def terminal_states() -> set[WorkflowState]:
        """Return set of terminal states: {COMPLETED, FAILED}."""
```

#### State Diagram

```
                    ┌───────────────────────────────────────────────────────┐
                    │                                                       │
                    ▼                                                       │
    ┌──────┐    ┌──────────┐    ┌────────────┐    ┌───────────┐    ┌────────┴────┐
    │ INIT │──▶│ BRIEFING │───▶│ ENRICHMENT │──▶│ VALIDATION│───▶│   WRITING   │
    └──────┘    └──────────┘    └────────────┘    └───────────┘    └────────┬────┘
                    ▲               ▲                  │                    │
                    │               │                  │ (fail)             │
                    │               │                  ▼                    │
                    │               │           ┌───────────┐               │
                    └───────────────┘───────────│   FAILED  │               │
                                                └───────────┘               │
                                                                            ▼
                                                                ┌───────────────────┐
                                                                │ QUALITY_ANALYSIS  │
                                                                └───────────────────┘
                                                                    │           │
                                                          (pass)    │           │ (fail)
                                                                    ▼           ▼
                                                            ┌───────────┐  ┌──────────┐
                                                            │ COMPLETED │  │ (retry)  │
                                                            └───────────┘  └──────────┘
```

---

## 5. Workflow Runner

**Module**: `backend/app/workflows/execution/runner.py`

### 5.1 WorkflowRunner

```python
class WorkflowRunner:
    """Drives a single workflow instance end-to-end."""
    
    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize runner with database session.
        
        Args:
            db: AsyncSession for persistence
            
        Attributes:
            sm: StateMachine instance
            requirement_agent: RequirementAgent
            procurement_agent: ProcurementAgent
            writer_agent: LeadWriterAgent
            quality_agent: QualityAgent
        """
    
    async def run(
        self,
        workflow_id: str,
        document_type: str,
        initial_input: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute complete workflow.
        
        Args:
            workflow_id: Unique workflow identifier
            document_type: Type of document to generate
            initial_input: User-provided initial data
            
        Returns:
            dict with status and result:
            - {"status": "completed", "quality_score": float}
            - {"status": "failed", "error": str}
            
        Process:
            1. Create WorkflowContext
            2. INIT → BRIEFING: collect requirements
            3. BRIEFING → ENRICHMENT: enrich with standards
            4. ENRICHMENT → VALIDATION: validate completeness
            5. VALIDATION → WRITING (or retry loop)
            6. WRITING → QUALITY_ANALYSIS: review quality
            7. QUALITY_ANALYSIS → COMPLETED (or retry loop)
            8. Persist state changes and emit SSE events
        """
    
    async def _run_agent(
        self,
        workflow_id: str,
        agent_name: str,
        fn: Callable[[], Awaitable[Any]],
    ) -> dict[str, Any]:
        """
        Execute an agent with timing and event emission.
        
        Args:
            workflow_id: Workflow identifier
            agent_name: Name for logging/events
            fn: Async callable to execute
            
        Returns:
            Agent result
            
        Emits:
            agent_start, agent_done events
        """
    
    async def _emit(
        self,
        workflow_id: str,
        event: str,
        data: dict[str, Any],
    ) -> None:
        """
        Emit SSE event to all subscribers.
        
        Args:
            workflow_id: Target workflow
            event: Event type
            data: Event payload
        """
    
    async def _persist_state(
        self,
        workflow_id: str,
        from_state: WorkflowState | str,
        to_state: WorkflowState | str,
        trigger: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """
        Persist workflow state change to database.
        
        Args:
            workflow_id: Workflow identifier
            from_state: Previous state
            to_state: New state
            trigger: Trigger that caused transition
            payload: Additional data
            
        Note:
            Safely no-ops if DB session is unavailable
        """
```

### 5.2 SSE Functions

```python
def subscribe(workflow_id: str) -> asyncio.Queue:
    """
    Subscribe to workflow events.
    
    Args:
        workflow_id: Workflow to subscribe to
        
    Returns:
        asyncio.Queue that receives event messages
        
    Message format:
        {"event": str, "data": dict}
    """

def unsubscribe(workflow_id: str, q: asyncio.Queue) -> None:
    """
    Unsubscribe from workflow events.
    
    Args:
        workflow_id: Workflow to unsubscribe from
        q: Queue to remove
    """
```

---

## 6. MCP Client

**Module**: `backend/app/mcp/client/mcp_client.py`

### 6.1 MCPClient

```python
class MCPClient:
    """
    FastMCP client for nanoRAG knowledge-base server.
    
    Tools exposed by server:
    - nanorag_health
    - nanorag_list_kbs
    - nanorag_list_documents
    - nanorag_get_graph
    - nanorag_get_node_detail
    - nanorag_chat
    - nanorag_upload_document
    - nanorag_delete_document
    
    Caching: In-process TTL cache (15 minutes) for search/chat results
    """
    
    def __init__(self) -> None:
        """
        Initialize MCP client.
        
        Attributes:
            _url: MCP server URL from settings
            _kb_id: Default knowledge base ID
            _client: FastMCP Client instance
            _connected: Connection status flag
            _cache: In-process TTL cache dict
            _cache_ttl: Cache TTL in seconds (900 = 15 min)
        """
    
    # ── Lifecycle ─────────────────────────────────────────────────────
    
    async def connect(self) -> None:
        """
        Open SSE transport to MCP server (idempotent).
        
        Raises:
            MCPError: If connection fails
        """
    
    async def disconnect(self) -> None:
        """Close transport (idempotent)."""
    
    async def _ensure_connected(self) -> Client:
        """
        Ensure client is connected.
        
        Returns:
            Connected FastMCP Client
        """
    
    # ── Public API ────────────────────────────────────────────────────
    
    async def health_check(self) -> dict[str, Any]:
        """
        Check MCP server health.
        
        Returns:
            System status dict from nanorag_health
        """
    
    async def list_kbs(self) -> list[dict[str, Any]]:
        """
        List all knowledge bases.
        
        Returns:
            List of knowledge base dicts
        """
    
    async def list_documents(
        self,
        kb_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List documents in a knowledge base.
        
        Args:
            kb_id: Knowledge base ID (default from settings)
            
        Returns:
            List of document dicts
        """
    
    async def upload_document(
        self,
        file_content: bytes,
        filename: str = "document",
        kb_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Upload a document to knowledge base.
        
        Args:
            file_content: Document content as bytes
            filename: Document filename
            kb_id: Target knowledge base
            
        Returns:
            dict with document_id and chunk_count
        """
    
    async def delete_document(
        self,
        document_id: str,
        kb_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Delete a document from knowledge base.
        
        Args:
            document_id: Document to delete
            kb_id: Knowledge base ID
            
        Returns:
            dict with status
        """
    
    async def get_graph(
        self,
        kb_id: str | None = None,
        limit: int = 18,
        min_weight: int = 1,
    ) -> dict[str, Any]:
        """
        Get knowledge graph snapshot.
        
        Args:
            kb_id: Knowledge base ID
            limit: Max nodes to return
            min_weight: Minimum edge weight
            
        Returns:
            Graph dict with nodes and edges
        """
    
    async def get_node_detail(
        self,
        entity_id: str,
        kb_id: str | None = None,
        evidence_limit: int = 12,
    ) -> dict[str, Any]:
        """
        Get entity detail with relationships.
        
        Args:
            entity_id: Entity to retrieve
            kb_id: Knowledge base ID
            evidence_limit: Max evidence documents
            
        Returns:
            Entity detail dict
        """
    
    async def chat(
        self,
        message: str,
        kb_id: str | None = None,
        top_k: int = 6,
    ) -> dict[str, Any]:
        """
        Grounded chat with knowledge base.
        
        Args:
            message: User message
            kb_id: Knowledge base ID
            top_k: Max sources to retrieve
            
        Returns:
            dict with answer, sources, search_query
            
        Note:
            Results cached for 15 minutes
        """
    
    async def search_documents(
        self,
        query: str,
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search documents (backward-compatible wrapper).
        
        Args:
            query: Search query
            limit: Max results
            filters: Additional filters (unused, for compatibility)
            
        Returns:
            List of result dicts in legacy format:
            [{source, title, excerpt, relevance_score, metadata}, ...]
            
        Note:
            Internally calls nanorag_chat and extracts sources
        """
    
    # ── Internal ──────────────────────────────────────────────────────
    
    async def _call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        cache_key: str | None = None,
    ) -> Any:
        """
        Call MCP tool with caching and logging.
        
        Args:
            tool_name: MCP tool name
            arguments: Tool arguments
            cache_key: Optional cache key
            
        Returns:
            Tool result
            
        Raises:
            MCPError: If tool call fails
        """
    
    @staticmethod
    def _extract_result(result: Any) -> Any:
        """
        Extract text content from CallToolResult.
        
        Args:
            result: FastMCP CallToolResult
            
        Returns:
            Parsed JSON or text content
        """
    
    def _get_cache(self, key: str) -> Any | None:
        """Get cached value if not expired."""
    
    def _set_cache(self, key: str, value: Any) -> None:
        """Set cache value with timestamp."""
```

### 6.2 MCPError

```python
class MCPError(Exception):
    """Raised when MCP server returns an error or is unreachable."""
```

---

## 7. Skills

### 7.1 ExportSkill

**Module**: `backend/app/skills/export/export_skill.py`

```python
class ExportSkill:
    """
    Document export to docx and pdf.
    
    Success: File exists at returned path, size > 0
    Failure: Raises ExportError, does NOT retry
    """
    
    def __init__(self) -> None:
        """
        Initialize export skill.
        
        Creates base_path directory if not exists.
        """
    
    async def export_docx(
        self,
        content: str,
        title: str,
        workflow_id: str,
        doc_type: str = "capitolato",
    ) -> str:
        """
        Export markdown to .docx.
        
        Args:
            content: Markdown content
            title: Document title
            workflow_id: Workflow identifier
            doc_type: Document type for filename
            
        Returns:
            Absolute file path to .docx
            
        Process:
            1. Create output directory
            2. Create Document with corporate styling
            3. Parse markdown and write paragraphs
            4. Save to file
        """
    
    async def export_pdf(
        self,
        content: str,
        title: str,
        workflow_id: str,
        doc_type: str = "capitolato",
    ) -> str:
        """
        Export markdown to .pdf.
        
        Args:
            content: Markdown content
            title: Document title
            workflow_id: Workflow identifier
            doc_type: Document type for filename
            
        Returns:
            Absolute file path to .pdf
        """
    
    def _setup_doc_styles(self, doc: Document) -> None:
        """
        Apply corporate styling to document.
        
        Styles:
        - Normal: Calibri 10pt
        - Title: 18pt bold, dark blue
        - Margins: 1" top/bottom, 1.2" left/right
        """
    
    def _write_markdown_to_doc(
        self,
        doc: Document,
        content: str,
        title: str,
    ) -> None:
        """
        Parse markdown and write to docx.
        
        Handles:
        - Headings (# ## ### ####)
        - Bullet lists (- *)
        - Numbered lists (1. 2. etc.)
        - Blockquotes (>)
        - Inline formatting (**bold** *italic*)
        """
    
    def _add_inline_formatting(
        self,
        paragraph: Any,
        text: str,
    ) -> None:
        """Handle **bold** and *italic* inline markdown."""
    
    def _write_pdf(
        self,
        content: str,
        title: str,
        output_path: str,
    ) -> None:
        """
        Build A4 PDF from markdown.
        
        Styles:
        - Title: 20pt, brand blue
        - H1: 14pt, brand blue
        - H2: 12pt, brand blue
        - H3: 10pt
        - Body: 9pt, 14pt leading
        - Bullet: 9pt, indented
        """
```

---

### 7.2 ValidationSkill

**Module**: `backend/app/skills/validation/validation_skill.py`

#### class ValidationResult

```python
@dataclass
class ValidationResult:
    valid: bool                              # True if all checks pass
    issues: list[str] = field(default_factory=list)       # Issues found
    missing_fields: list[str] = field(default_factory=list) # Missing required fields
    warnings: list[str] = field(default_factory=list)     # Non-critical warnings
    confidence: float = 1.0                 # 0.0–1.0 confidence score
```

#### Functions

```python
def validate_requirements_completeness(
    requirements: dict[str, Any],
    document_type: str = "capitolato",
) -> ValidationResult:
    """
    Check structural completeness of requirements.
    
    Args:
        requirements: Requirements dict from RequirementAgent
        document_type: Type of document
        
    Returns:
        ValidationResult with issues and confidence
        
    Checks:
        - All required fields present (per document type)
        - Minimum functional requirements count (≥3)
        - Minimum technical requirements count (≥1)
        
    Required fields for capitolato:
        - project.title, project.organization
        - scope.objectives
        - functional_requirements, technical_requirements
        - sla.availability
        - security_compliance.standards
        - timeline.go_live
    """

def validate_sla_consistency(
    sla: dict[str, Any],
) -> ValidationResult:
    """
    Validate SLA values are internally consistent.
    
    Args:
        sla: SLA configuration dict
        
    Returns:
        ValidationResult with warnings/issues
        
    Rules:
        - Availability between 95% and 99.999%
        - RTO must be > RPO
        - Response time must be positive
    """

def validate_document_sections(
    content: str,
    document_type: str = "capitolato",
) -> ValidationResult:
    """
    Check required sections present in document.
    
    Args:
        content: Markdown content
        document_type: Type of document
        
    Returns:
        ValidationResult with missing_sections
        
    Required sections for capitolato:
        Oggetto, Requisiti Funzionali, Requisiti Tecnici,
        Sicurezza, SLA, Integrazioni, Piano, Criteri
    """

def detect_placeholder_content(content: str) -> list[str]:
    """
    Detect unfilled placeholders in document.
    
    Args:
        content: Markdown content
        
    Returns:
        List of placeholder strings found
        
    Patterns detected:
        [TBD], [TODO], [PLACEHOLDER], [DA DEFINIRE],
        [INSERIRE], SEZIONE DA COMPLETARE, ...
    """

def score_requirement_richness(
    requirements: dict[str, Any],
) -> float:
    """
    Compute 0.0–1.0 richness score for requirements.
    
    Args:
        requirements: Requirements dict
        
    Returns:
        Richness score (0.0–1.0)
        
    Weights:
        - functional_requirements: 30%
        - technical_requirements: 20%
        - sla_detail: 15%
        - integrations: 10%
        - stakeholders: 10%
        - security_detail: 10%
        - timeline_detail: 5%
    """
```

---

### 7.3 RetrievalSkill

**Module**: `backend/app/skills/retrieval/retrieval_skill.py`

#### class RetrievedContext

```python
@dataclass
class RetrievedContext:
    context_text: str                          # Formatted context for prompts
    sources: list[dict[str, Any]] = field(default_factory=list)  # Source metadata
    query_count: int = 0                       # Number of queries executed
    total_docs: int = 0                        # Total documents retrieved
```

#### class RetrievalSkill

```python
class RetrievalSkill:
    """
    Builds knowledge-base context for document generation.
    
    Success: Returns RetrievedContext with populated context_text
    Failure: Returns RetrievedContext with empty context_text (graceful degradation)
    """
    
    def __init__(self) -> None:
        """Initialize with MCPClient."""
    
    async def build_context(
        self,
        requirements: dict[str, Any],
        document_type: str = "capitolato",
        max_docs: int = 8,
    ) -> RetrievedContext:
        """
        Build KB context from requirements.
        
        Args:
            requirements: Requirements dict
            document_type: Type of document
            max_docs: Maximum documents to include
            
        Returns:
            RetrievedContext with formatted context
            
        Process:
            1. Build targeted queries from requirements
            2. Execute queries concurrently
            3. Deduplicate by source
            4. Sort by relevance score
            5. Format top N docs into context string
        """
    
    def _build_queries(
        self,
        requirements: dict[str, Any],
        document_type: str,
    ) -> list[str]:
        """
        Generate targeted search queries from requirements.
        
        Queries generated for:
        - Document type template
        - Security standards (ISO, GDPR, etc.)
        - Integration systems
        - Sector-specific regulations (PA → AGID, CAD, D.Lgs 36/2023)
        - Data classification requirements
        - SLA benchmarks
        """
    
    async def _safe_search(
        self,
        query: str,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Search with graceful error handling.
        
        Args:
            query: Search query
            limit: Max results
            
        Returns:
            List of results or empty list on failure
        """
    
    def _format_context(
        self,
        docs: list[dict[str, Any]],
    ) -> str:
        """
        Format docs into prompt-injectable context.
        
        Args:
            docs: List of document dicts
            
        Returns:
            Formatted markdown string with:
            - Title
            - Source and relevance score
            - Excerpt (max 500 chars)
        """
```

---

## 8. Database Models

**Module**: `backend/app/db/models.py`

SQLAlchemy 2.0 ORM models with PostgreSQL.

### Base Classes

```python
class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

### 8.1 User

```python
class User(TimestampMixin, Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID]              # PK, UUID, auto-generated
    email: Mapped[str]                 # Unique, indexed
    hashed_password: Mapped[str]       # Bcrypt hash
    full_name: Mapped[str]             # Display name
    role: Mapped[str]                  # "user" | "admin"
    is_active: Mapped[bool]            # Account active flag
    
    # Relationships
    workflows: Mapped[list["Workflow"]]  # One-to-many
```

### 8.2 Workflow

```python
class Workflow(TimestampMixin, Base):
    __tablename__ = "workflows"
    
    id: Mapped[uuid.UUID]              # PK, UUID
    owner_id: Mapped[uuid.UUID | None] # FK → users.id (nullable)
    title: Mapped[str]                 # Document title
    document_type: Mapped[str]         # "capitolato" | "requisiti"
    state: Mapped[str]                 # Current state (indexed)
    retry_count: Mapped[int]           # Total retry count
    metadata_: Mapped[dict[str, Any]]  # JSON metadata
    
    # Relationships
    owner: Mapped["User"]
    states: Mapped[list["WorkflowState"]]      # Audit trail
    agent_outputs: Mapped[list["AgentOutput"]] # Agent results
    documents: Mapped[list["Document"]]        # Generated files
    quality_reports: Mapped[list["QualityReport"]] # Quality scores
    audit_logs: Mapped[list["AuditLog"]]       # Audit logs
```

### 8.3 WorkflowState (DB)

```python
class WorkflowState(TimestampMixin, Base):
    __tablename__ = "workflow_states"
    
    id: Mapped[uuid.UUID]              # PK, UUID
    workflow_id: Mapped[uuid.UUID]     # FK → workflows.id (indexed)
    from_state: Mapped[str]            # Previous state
    to_state: Mapped[str]              # New state
    trigger: Mapped[str]               # Trigger name
    payload: Mapped[dict[str, Any]]    # Additional data
    
    # Relationships
    workflow: Mapped["Workflow"]
```

### 8.4 AgentOutput

```python
class AgentOutput(TimestampMixin, Base):
    __tablename__ = "agent_outputs"
    
    id: Mapped[uuid.UUID]              # PK, UUID
    workflow_id: Mapped[uuid.UUID]     # FK → workflows.id (indexed)
    agent_name: Mapped[str]            # Agent name
    output_type: Mapped[str]           # Output type
    content: Mapped[dict[str, Any]]    # Output content (JSON)
    token_usage: Mapped[dict[str, Any]] # Token usage stats
    duration_ms: Mapped[int]           # Execution time
    
    # Relationships
    workflow: Mapped["Workflow"]
```

### 8.5 Document

```python
class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    
    id: Mapped[uuid.UUID]              # PK, UUID
    workflow_id: Mapped[uuid.UUID]     # FK → workflows.id (indexed)
    name: Mapped[str]                  # Document name
    format: Mapped[str]                # "markdown" | "docx" | "pdf"
    content_md: Mapped[str]            # Markdown content
    file_path: Mapped[str]             # File storage path
    version: Mapped[int]               # Version number
    
    # Relationships
    workflow: Mapped["Workflow"]
```

### 8.6 QualityReport (DB)

```python
class QualityReport(TimestampMixin, Base):
    __tablename__ = "quality_reports"
    
    id: Mapped[uuid.UUID]              # PK, UUID
    workflow_id: Mapped[uuid.UUID]     # FK → workflows.id (indexed)
    score: Mapped[float]               # Quality score (0.0–1.0)
    passed: Mapped[bool]               # Passed threshold
    issues: Mapped[list[dict[str, Any]]] # Issues list
    suggestions: Mapped[list[str]]     # Suggestions list
    section_scores: Mapped[dict[str, Any]] # Per-section scores
    
    # Relationships
    workflow: Mapped["Workflow"]
```

### 8.7 AuditLog

```python
class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"
    
    id: Mapped[uuid.UUID]              # PK, UUID
    workflow_id: Mapped[uuid.UUID]     # FK → workflows.id (indexed)
    user_id: Mapped[uuid.UUID | None]  # User who performed action
    action: Mapped[str]                # Action description
    detail: Mapped[dict[str, Any]]     # Action details (JSON)
    ip_address: Mapped[str]            # Client IP
    
    # Relationships
    workflow: Mapped["Workflow"]
```

### Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────────┐
│     User     │       │     Workflow     │       │  WorkflowState   │
├──────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (PK)      │◄──┐   │ id (PK)          │◄──┐   │ id (PK)          │
│ email        │   └───│ owner_id (FK)    │   └───│ workflow_id (FK) │
│ hashed_pwd   │       │ title            │       │ from_state       │
│ full_name    │       │ document_type    │       │ to_state         │
│ role         │       │ state            │       │ trigger          │
│ is_active    │       │ retry_count      │       │ payload          │
└──────────────┘       │ metadata_        │       └──────────────────┘
                       └────────┬─────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  AgentOutput  │    │    Document      │    │  QualityReport   │
├───────────────┤    ├──────────────────┤    ├──────────────────┤
│ id (PK)       │    │ id (PK)          │    │ id (PK)          │
│ workflow_id   │    │ workflow_id      │    │ workflow_id      │
│ agent_name    │    │ name             │    │ score            │
│ output_type   │    │ format           │    │ passed           │
│ content       │    │ content_md       │    │ issues           │
│ token_usage   │    │ file_path        │    │ suggestions      │
│ duration_ms   │    │ version          │    │ section_scores   │
└───────────────┘    └──────────────────┘    └──────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │    AuditLog      │
                       ├──────────────────┤
                       │ id (PK)          │
                       │ workflow_id      │
                       │ user_id          │
                       │ action           │
                       │ detail           │
                       │ ip_address       │
                       └──────────────────┘
```

---

## 9. API Routes

**Module**: `backend/app/api/routes/workflow.py`

### Request/Response Schemas

```python
class StartWorkflowRequest(BaseModel):
    document_type: str = Field(..., pattern="^(capitolato|requisiti)$")
    title: str = Field(..., min_length=5, max_length=500)
    raw_description: str = Field(..., min_length=20)
    form_data: dict[str, Any] = Field(default_factory=dict)

class WorkflowResponse(BaseModel):
    workflow_id: str
    state: str
    document_type: str
    title: str
    retry_count: int
    quality_score: float | None = None
    created_at: str
    updated_at: str

class ApproveRequest(BaseModel):
    approved: bool
    comment: str = ""

class RetryRequest(BaseModel):
    reason: str = ""
```

### POST /workflow/start

Create and start a new workflow.

```
POST /api/v1/workflow/start
Content-Type: application/json

{
  "document_type": "capitolato",
  "title": "Capitolato Tecnico - Sistema CRM",
  "raw_description": "Fornitura e implementazione di un sistema CRM per...",
  "form_data": {
    "organization": "Comune di Roma",
    "budget": "500000",
    "timeline": "12 mesi"
  }
}
```

**Response** (202 Accepted):
```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "INIT",
  "message": "Workflow started"
}
```

**Process**:
1. Generate UUID for workflow
2. Persist initial Workflow row to DB
3. Start WorkflowRunner in background task
4. Return workflow_id immediately

---

### GET /workflow/{id}

Get current workflow state and metadata.

```
GET /api/v1/workflow/{workflow_id}
```

**Response** (200 OK):
```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "WRITING",
  "document_type": "capitolato",
  "title": "Capitolato Tecnico - Sistema CRM",
  "retry_count": 0,
  "quality_score": null,
  "created_at": "2026-06-21T10:30:00Z",
  "updated_at": "2026-06-21T10:35:00Z"
}
```

**Errors**:
- 404: Workflow not found

---

### POST /workflow/{id}/approve

Human-in-the-loop approval gate.

```
POST /api/v1/workflow/{workflow_id}/approve
Content-Type: application/json

{
  "approved": true,
  "comment": "Looks good, approved for publication"
}
```

**Response** (200 OK):
```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "approved"
}
```

**Errors**:
- 404: Workflow not found
- 400: Workflow not in approvable state (must be QUALITY_ANALYSIS or COMPLETED)

---

### POST /workflow/{id}/retry

Manual retry from FAILED state.

```
POST /api/v1/workflow/{workflow_id}/retry
Content-Type: application/json

{
  "reason": "Retry after fixing requirements"
}
```

**Response** (200 OK):
```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "INIT",
  "message": "Retry started"
}
```

**Process**:
1. Verify workflow is in FAILED state
2. Reset state to INIT
3. Increment retry_count
4. Start new WorkflowRunner in background

**Errors**:
- 404: Workflow not found
- 400: Only FAILED workflows can be retried

---

### GET /workflow/{id}/documents

List generated documents for a workflow.

```
GET /api/v1/workflow/{workflow_id}/documents
```

**Response** (200 OK):
```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "documents": [
    {
      "id": "...",
      "name": "capitolato_abc12345.docx",
      "format": "docx",
      "file_path": "/app/documents/.../capitolato_abc12345.docx"
    },
    {
      "id": "...",
      "name": "capitolato_abc12345.pdf",
      "format": "pdf",
      "file_path": "/app/documents/.../capitolato_abc12345.pdf"
    }
  ]
}
```

---

### GET /workflow/{id}/quality-report

Get latest quality report.

```
GET /api/v1/workflow/{workflow_id}/quality-report
```

**Response** (200 OK):
```json
{
  "score": 0.87,
  "passed": true,
  "issues": [],
  "suggestions": ["Consider adding more detailed SLA metrics"],
  "section_scores": {
    "Requisiti Funzionali": 0.95,
    "Sicurezza": 0.80,
    "SLA": 0.75
  }
}
```

**Errors**:
- 404: Workflow not found
- 404: No quality report available yet

---

## 10. WebSocket Events

**Module**: `backend/app/api/websocket/stream.py`

### Connection

```
WS /ws/workflow/{workflow_id}
```

### Event Types

| Event | Description | Payload |
|-------|-------------|---------|
| `state_change` | Workflow moved to new state | `{"state": "ENRICHMENT"}` |
| `agent_start` | Agent started execution | `{"agent": "requirement"}` |
| `agent_done` | Agent finished | `{"agent": "requirement", "duration_ms": 1234, "summary": "..."}` |
| `validation_failed` | Validation check failed | `{"issues": [...], "missing_fields": [...], "confidence": 0.6}` |
| `quality_report` | Quality analysis completed | `{"score": 0.87, "passed": true, "issues": [], "suggestions": [], "section_scores": {...}, "needs_enrichment": false}` |
| `completed` | Workflow finished successfully | `{"workflow_id": "...", "quality_score": 0.87}` |
| `failed` | Workflow failed | `{"error": "..."}` |
| `heartbeat` | Keep-alive ping | `{}` |

### Message Format

```json
{
  "event": "state_change",
  "data": {
    "state": "WRITING"
  }
}
```

### Client Example (JavaScript)

```javascript
const ws = new WebSocket(`ws://localhost:8001/ws/workflow/${workflowId}`);

ws.onmessage = (event) => {
  const { event: eventType, data } = JSON.parse(event.data);
  
  switch (eventType) {
    case 'state_change':
      updateUI(data.state);
      break;
    case 'agent_start':
      showAgentProgress(data.agent);
      break;
    case 'agent_done':
      hideAgentProgress(data.agent, data.duration_ms);
      break;
    case 'quality_report':
      showQualityReport(data);
      break;
    case 'completed':
      showCompletion(data.quality_score);
      break;
    case 'failed':
      showError(data.error);
      break;
  }
};
```

---

## 11. UML Diagrams

### 11.1 Class Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AI Document Platform                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐      ┌─────────────────┐      ┌──────────────────┐     │
│  │  Settings       │      │ RequirementAgent│      │ ProcurementAgent │     │
│  ├─────────────────┤      ├─────────────────┤      ├──────────────────┤     │
│  │ - all config    │      │ - _agno: Agent  │      │ - _mcp: MCPClient│     │
│  │                 │      │                 │      │ - _agno: Agent   │     │
│  ├─────────────────┤      ├─────────────────┤      ├──────────────────┤     │
│  │ + get_settings()│      │ + collect()     │      │ + enrich()       │     │
│  └─────────────────┘      └─────────────────┘      │ - _fetch_kb()    │     │
│         │                                          └──────────────────┘     │
│         ▼                                                   │               │
│  ┌─────────────────┐      ┌─────────────────┐               │               │
│  │get_model_adapter│      │OrchestratorAgent│◄──────────────┘               │
│  ├─────────────────┤      ├─────────────────┤                               │
│  │ + get_model()   │      │ - sm: StateMach │                               │
│  └─────────────────┘      │ - agents: [...] │                               │
│                           ├─────────────────┤                               │
│                           │ + run()         │                               │
│                           │ - _step()       │      ┌─────────────────┐      │
│                           │ - _run_*()      │────▶│ LeadWriterAgent │      │
│                           └─────────────────┘      ├─────────────────┤      │
│                                    │               │ - _jinja: Env   │      │
│                                    │               │ - _exporter     │      │
│                                    ▼               ├─────────────────┤      │
│                           ┌─────────────────┐      │ + write()       │      │
│                           │  QualityAgent   │      └─────────────────┘      │
│                           ├─────────────────┤              │                │
│                           │ - _agno: Agent  │              ▼                │
│                           ├─────────────────┤      ┌─────────────────┐      │
│                           │ + review()      │      │  ExportSkill    │      │
│                           └─────────────────┘      ├─────────────────┤      │
│                                                    │ + export_docx() │      │
│  ┌─────────────────┐      ┌─────────────────┐      │ + export_pdf()  │      │
│  │ StateMachine    │      │ WorkflowRunner  │      └─────────────────┘      │
│  ├─────────────────┤      ├─────────────────┤                               │
│  │ - transitions   │      │ - sm: StateMach │      ┌─────────────────┐      │
│  │                 │      │ - db: Session   │      │  MCPClient      │      │
│  ├─────────────────┤      ├─────────────────┤      ├─────────────────┤      │
│  │ + trigger()     │      │ + run()         │      │ - _client       │      │
│  │ + can_trigger() │      │ - _run_agent()  │      │ - _cache        │      │
│  └─────────────────┘      │ - _emit()       │      ├─────────────────┤      │
│                           │ - _persist()    │      │ + search_docs() │      │
│                           └─────────────────┘      │ + chat()        │      │
│                                                    │ + health()      │      │
│  ┌─────────────────┐      ┌──────────────────┐     └─────────────────┘      │
│  │ValidationSkill  │      │ RetrievalSkill   │                              │
│  ├─────────────────┤      ├──────────────────┤                              │
│  │ + validate_*()  │      │ - _mcp: MCPClient│                              │
│  │ + detect_*()    │      ├──────────────────┤                              │
│  │ + score_*()     │      │ + build_context()│                              │
│  └─────────────────┘      └──────────────────┘                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Sequence Diagram — Workflow Execution

```
┌──────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│Client│      │WorkflowRunner│      │   Agents     │      │   Database   │
└──┬───┘      └──────┬───────┘      └──────┬───────┘      └──────┬───────┘
   │                 │                     │                     │
   │  POST /start    │                     │                     │
   │───────────────▶│                     │                     │
   │                 │  Persist Workflow   │                     │
   │                 │─────────────────────────────────────────▶│
   │  202 {id}       │                     │                     │
   │◀───────────────│                     │                     │
   │                 │                     │                     │
   │  (background)   │  INIT → BRIEFING    │                     │
   │                 │─────────────────────────────────────────▶│
   │                 │                     │                     │
   │                 │  RequirementAgent   │                     │
   │                 │───────────────────▶│                     │
   │                 │                     │  LLM call           │
   │                 │  RequirementResult  │                     │
   │                 │◀───────────────────│                     │
   │                 │                     │                     │
   │                 │  BRIEFING → ENRICHMENT                    │
   │                 │─────────────────────────────────────────▶│
   │                 │                     │                     │
   │                 │  ProcurementAgent   │                     │
   │                 │───────────────────▶│                     │
   │                 │                     │  MCP search         │
   │                 │                     │  LLM call           │
   │                 │  ProcurementResult  │                     │
   │                 │◀───────────────────│                     │
   │                 │                     │                     │
   │                 │  ENRICHMENT → VALIDATION                  │
   │                 │─────────────────────────────────────────▶│
   │                 │                     │                     │
   │                 │  ValidationSkill    │                     │
   │                 │───────────────────▶│                     │
   │                 │  ValidationResult   │                     │
   │                 │◀───────────────────│                     │
   │                 │                     │                     │
   │                 │  VALIDATION → WRITING                     │
   │                 │─────────────────────────────────────────▶│
   │                 │                     │                     │
   │                 │  LeadWriterAgent    │                     │
   │                 │───────────────────▶│                     │
   │                 │                     │  LLM call           │
   │                 │                     │  ExportSkill        │
   │                 │  WriterResult       │                     │
   │                 │◀───────────────────│                     │
   │                 │                     │                     │
   │                 │  WRITING → QUALITY_ANALYSIS               │
   │                 │────────────────────────────────────────────▶│
   │                 │                     │                     │
   │                 │  QualityAgent       │                     │
   │                 │───────────────────▶│                     │
   │                 │                     │  LLM call           │
   │                 │  QualityReport      │                     │
   │                 │◀───────────────────│                     │
   │                 │                     │                     │
   │                 │  QUALITY → COMPLETED│                     │
   │                 │─────────────────────────────────────────▶│
   │                 │                     │                     │
   │  WS: completed  │                     │                     │
   │◀───────────────│                     │                     │
   │                 │                     │                     │
```

### 11.3 State Diagram — Detailed

```
                                    ┌─────────────────────────────────────────┐
                                    │              WORKFLOW STATES             │
                                    └─────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────────────────────────────────────┐
    │                                                                                          │
    │   ┌──────────┐                                                                           │
    │   │   INIT   │                                                                           │
    │   └────┬─────┘                                                                           │
    │        │ START                                                                           │
    │        ▼                                                                                 │
    │   ┌──────────┐      REQUIREMENTS_COLLECTED        ┌──────────────┐                       │
    │   │ BRIEFING │ ─────────────────────────────────▶│  ENRICHMENT  │                       │
    │   └────▲─────┘                                    └──────┬───────┘                       │
    │        │                                                │ ENRICHMENT_DONE                │
    │        │ VALIDATION_FAILED                              ▼                                │
    │        │ (retries < max)                          ┌──────────────┐                       │
    │        └──────────────────────────────────────────│  VALIDATION  │                       │
    │                                                   └──────┬───────┘                       │
    │                                                          │                               │
    │                              ┌───────────────────────────┼───────────────────┐           │
    │                              │ VALIDATION_PASSED         │ VALIDATION_FAILED │           │
    │                              │                           │ (retries >= max)  │           │
    │                              ▼                           ▼                   │           │
    │                        ┌──────────┐              ┌──────────┐                │           │
    │                        │ WRITING  │              │  FAILED  │                │           │
    │                        └────┬─────┘              └──────────┘                │           │
    │                             │ WRITING_DONE                                   │           │
    │                             ▼                                                │           │
    │                   ┌───────────────────┐                                      │           │
    │                   │ QUALITY_ANALYSIS  │                                      │           │
    │                   └─────────┬─────────┘                                      │           │
    │                             │                                                │           │
    │         ┌───────────────────┼───────────────────┬───────────────────┐        │           │
    │         │ QUALITY_PASSED    │ QUALITY_FAILED    │ QUALITY_FAILED    │        │           │
    │         │                   │ _WRITING          │ _ENRICHMENT       │        │           │
    │         ▼                   │ (retries < max)   │ (retries < max)   │        │           │
    │   ┌───────────┐             │                   │                   │        │           │
    │   │ COMPLETED │             ▼                   ▼                   │        │           │
    │   └───────────┘      ┌──────────┐      ┌──────────────┐             │        │           │
    │                      │ WRITING  │      │  ENRICHMENT  │             │        │           │
    │                      └──────────┘      └──────────────┘             │        │           │
    │                                                                     │        │           │
    │                      QUALITY_FAILED_*                               │        │           │
    │                      (retries >= max)                               │        │           │
    │                              │                                      │        │           │
    │                              └──────────────────────────────────────┼────────┘           │
    │                                                                     │                    │
    │                                                                     ▼                    │
    │                                                              ┌──────────┐                │
    │                                                              │  FAILED  │                │
    │                                                              └──────────┘                │
    │                                                                                          │
    │   ─────────────────────────────────────────────────────────────────────────────────      │
    │   FATAL_ERROR: Any non-terminal state → FAILED                                           │
    │   ─────────────────────────────────────────────────────────────────────────────────      │
    │                                                                                          │
    └──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix: Error Handling

### MCPClient Errors

| Error | Cause | Handling |
|-------|-------|----------|
| `MCPError` | MCP server unreachable | Returns empty context, agent proceeds without KB |
| Connection timeout | Network issues | Auto-retry up to `mcp_max_retries` |
| Invalid response | Malformed data | Raises `MCPError` |

### Workflow Errors

| Error | Cause | Handling |
|-------|-------|----------|
| `RequirementError` | LLM non-JSON response | Triggers validation failure, retry |
| `RuntimeError` | Retry budget exhausted | Transitions to FAILED state |
| `ValueError` | Invalid state transition | Caught by Orchestrator, triggers FATAL_ERROR |

### Export Errors

| Error | Cause | Handling |
|-------|-------|----------|
| `ExportError` | File write failure | Does NOT retry, caller decides |
| Permission denied | Storage path issues | Raises exception |

---

*End of API Reference*
