"""
MCP Stub Server — local development / testing only.

Simulates a real RAG / knowledge-base server with deterministic responses.
Replace with real vector-DB backed MCP server in production.

Endpoints mirror the real MCP API contract expected by MCPClient.
"""

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any

app = FastAPI(title="MCP Stub Server", version="0.1.0")


# ── Request models ────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    filters: dict[str, Any] = {}


class RetrieveRequest(BaseModel):
    doc_ids: list[str]
    max_tokens: int = 2000


class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    collection: str = "default"


class TemplateRequest(BaseModel):
    name: str


class RegulationsRequest(BaseModel):
    domain: str


# ── Stub data ─────────────────────────────────────────────────────────────────

STUB_DOCUMENTS = [
    {
        "source": "AGID-2023-GL-01",
        "title": "Linee Guida AGID per l'acquisizione di software",
        "excerpt": "Le PA devono privilegiare soluzioni open source o in riuso prima di procedere ad acquisizioni.",
        "relevance_score": 0.92,
        "metadata": {"year": 2023, "authority": "AGID"},
    },
    {
        "source": "CAD-DL82-2005",
        "title": "Codice Amministrazione Digitale — Art. 68",
        "excerpt": "Le pubbliche amministrazioni acquisiscono programmi informatici o parti di essi nel rispetto dei principi di economicità e di efficienza.",
        "relevance_score": 0.88,
        "metadata": {"year": 2005, "authority": "MEF"},
    },
    {
        "source": "ISO27001-2022",
        "title": "ISO/IEC 27001:2022 — Information Security Management",
        "excerpt": "Organizations must establish, implement, maintain and continually improve an information security management system.",
        "relevance_score": 0.85,
        "metadata": {"year": 2022, "authority": "ISO"},
    },
]

STUB_REGULATIONS = [
    {"code": "GDPR Art.5",  "title": "Principi protezione dati", "description": "Liceità, correttezza e trasparenza nel trattamento dei dati personali.", "url": "https://gdpr-info.eu/art-5-gdpr/"},
    {"code": "GDPR Art.32", "title": "Sicurezza trattamento",    "description": "Misure tecniche e organizzative adeguate per garantire un livello di sicurezza adeguato al rischio.", "url": "https://gdpr-info.eu/art-32-gdpr/"},
    {"code": "NIS2 Art.21", "title": "Misure di sicurezza",      "description": "Misure tecniche, operative e organizzative adeguate per gestire i rischi per la sicurezza delle reti.", "url": "https://eur-lex.europa.eu/"},
    {"code": "D.Lgs 36/2023 Art.110", "title": "Requisiti tecnici appalti ICT", "description": "Specifiche tecniche per l'acquisizione di beni e servizi ICT dalla PA.", "url": "https://www.giustizia.it/"},
]

STUB_TEMPLATE = """# Template Capitolato di Gara ICT

## Sezione 1 — Descrizione Fornitura
[Descrivere oggetto e perimetro della fornitura]

## Sezione 2 — Requisiti Tecnici  
[Elenco requisiti tecnici minimi]

## Sezione 3 — SLA
| Parametro | Valore minimo |
|-----------|--------------|
| Disponibilità | 99.5% |
| RTO | 4h |
| RPO | 1h |

## Sezione 4 — Sicurezza
[Requisiti sicurezza e compliance]
"""


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "mcp-stub"}


@app.post("/search")
def search(req: SearchRequest):
    # Return stub docs filtered loosely by query keyword
    results = [
        d for d in STUB_DOCUMENTS
        if any(kw.lower() in d["title"].lower() or kw.lower() in d["excerpt"].lower()
               for kw in req.query.lower().split()[:3])
    ] or STUB_DOCUMENTS[:req.limit]
    return {"results": results[:req.limit]}


@app.post("/retrieve")
def retrieve(req: RetrieveRequest):
    results = [
        {"doc_id": did, "content": f"Full content for {did} (stub)", "metadata": {}}
        for did in req.doc_ids
    ]
    return {"results": results}


@app.post("/semantic-search")
def semantic_search(req: SemanticSearchRequest):
    return {"results": STUB_DOCUMENTS[:req.top_k]}


@app.post("/templates")
def get_template(req: TemplateRequest):
    return {"results": {"name": req.name, "content": STUB_TEMPLATE}}


@app.post("/regulations")
def get_regulations(req: RegulationsRequest):
    return {"results": STUB_REGULATIONS}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
