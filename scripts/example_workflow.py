"""
Realistic end-to-end workflow example.

Demonstrates a complete capitolato di gara generation for a
public-sector ERP system — without Docker, using mock agents.

Run:
    cd backend
    python -m scripts.example_workflow
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


# ── Mock agents for demonstration (no API key needed) ─────────────────────────

MOCK_REQUIREMENTS = {
    "project": {
        "title": "Sistema ERP Cloud — Comune di Milano",
        "organization": "Comune di Milano",
        "reference_code": "CAP-2025-MI-001",
        "description": (
            "Fornitura, installazione e configurazione di un sistema ERP cloud-native "
            "per la gestione amministrativa del Comune di Milano. "
            "Il sistema dovrà sostituire l'attuale soluzione legacy on-premise."
        ),
        "document_type": "capitolato",
    },
    "scope": {
        "objectives": [
            "Digitalizzare e automatizzare i processi amministrativi",
            "Ridurre i costi operativi del 30% entro 24 mesi",
            "Garantire piena compliance normativa GDPR e CAD",
            "Migliorare l'esperienza utente per 2.500 dipendenti",
        ],
        "in_scope": [
            "Modulo HR e gestione presenze",
            "Modulo contabilità e bilancio",
            "Modulo protocollo documentale",
            "Modulo acquisti e contratti",
            "Portale self-service dipendenti",
        ],
        "out_of_scope": [
            "Infrastruttura di rete esistente",
            "Sistemi catastali regionali",
            "Applicativi verticali di terze parti già contrattualizzati",
        ],
    },
    "stakeholders": [
        {"role": "CIO Comune di Milano", "responsibilities": "Sponsor tecnico e approvazione finale"},
        {"role": "Responsabile Risorse Umane", "responsibilities": "Owner modulo HR"},
        {"role": "Direttore Finanziario", "responsibilities": "Owner modulo Finance"},
        {"role": "Data Protection Officer", "responsibilities": "Validazione GDPR"},
    ],
    "functional_requirements": [
        {"id": "FR-001", "title": "Single Sign-On SPID/CIE", "description": "Autenticazione tramite SPID livello 2 e CIE per tutti gli utenti", "priority": "MUST"},
        {"id": "FR-002", "title": "Gestione presenze e timbrature", "description": "Registrazione presenze, ferie, permessi con workflow approvazione", "priority": "MUST"},
        {"id": "FR-003", "title": "Contabilità pubblica", "description": "Gestione bilancio preventivo/consuntivo secondo D.Lgs 118/2011", "priority": "MUST"},
        {"id": "FR-004", "title": "Protocollo informatico", "description": "Gestione documenti conforme DPR 445/2000 e CAD", "priority": "MUST"},
        {"id": "FR-005", "title": "Reporting e BI", "description": "Dashboard KPI e report personalizzabili per dirigenza", "priority": "SHOULD"},
        {"id": "FR-006", "title": "Workflow approvazione acquisti", "description": "Gestione iter acquisti con firma digitale e CIG ANAC", "priority": "MUST"},
        {"id": "FR-007", "title": "Portale self-service", "description": "Portale web responsive per richieste dipendenti (ferie, cedolini, etc.)", "priority": "SHOULD"},
    ],
    "technical_requirements": [
        {"id": "TR-001", "category": "Architettura", "description": "Cloud SaaS multi-tenant su infrastruttura certificata CSP Qualificato ACN", "constraint": "Solo provider cloud qualificati ACN tier 3+"},
        {"id": "TR-002", "category": "Performance", "description": "Supporto 2.500 utenti concorrenti con tempi risposta < 2s (p95)", "constraint": ""},
        {"id": "TR-003", "category": "Integrazione", "description": "API REST/SOAP per integrazione con sistemi esterni (ANAC, Agenzia Entrate, INPS)", "constraint": "OpenAPI 3.0 obbligatorio"},
        {"id": "TR-004", "category": "Disaster Recovery", "description": "Architettura multi-AZ con failover automatico entro 15 minuti", "constraint": ""},
        {"id": "TR-005", "category": "Accessibilità", "description": "Conformità WCAG 2.1 livello AA per tutte le interfacce utente", "constraint": "Obbligo di legge per PA"},
    ],
    "sla": {
        "availability": "99.9%",
        "rto": "4h",
        "rpo": "1h",
        "response_time": "< 2s (p95)",
        "custom_kpis": [
            "Supporto H24 7/7 per incidenti critici",
            "Tempo di presa in carico entro 30 minuti",
        ],
    },
    "security_compliance": {
        "standards": ["ISO 27001:2022", "GDPR (UE 2016/679)", "AgID - Misure Minime di Sicurezza ICT"],
        "requirements": [
            "MFA obbligatorio per tutti gli utenti",
            "Crittografia AES-256 per dati at-rest",
            "TLS 1.3 per tutte le comunicazioni",
            "Log di audit immutabili per 10 anni",
            "Vulnerability Assessment trimestrale",
            "Penetration Test annuale con report",
        ],
        "data_classification": "DATI PERSONALI - RISERVATO",
    },
    "integrations": [
        {"system": "ANAC - Banca Dati Appalti", "type": "API", "protocol": "REST/SOAP"},
        {"system": "Agenzia delle Entrate - Fatturazione Elettronica", "type": "API", "protocol": "SDI"},
        {"system": "INPS - Gestione Contributiva", "type": "API", "protocol": "REST"},
        {"system": "Sistema di Firma Digitale Ente", "type": "API", "protocol": "REST"},
    ],
    "timeline": {
        "project_start": "2025-10-01",
        "go_live": "2026-10-01",
        "milestones": [
            "M1 (2025-12-31): Analisi dettagliata e configurazione ambiente",
            "M2 (2026-03-31): Rilascio moduli HR e Presenze",
            "M3 (2026-06-30): Rilascio modulo Contabilità",
            "M4 (2026-09-30): UAT completato e go-live",
        ],
    },
    "budget": {
        "model": "fixed",
        "indicative_value": "1.200.000",
        "currency": "EUR",
    },
    "constraints": [
        "Il fornitore deve essere iscritto al MePA (Mercato Elettronico PA)",
        "Dati residenti esclusivamente in data center italiani od europei",
        "Obbligo di formazione per 100 utenti chiave",
    ],
    "acceptance_criteria": [
        "UAT superato al 95% dei casi di test",
        "Performance test: < 2s per il 95% delle transazioni sotto carico massimo",
        "Zero vulnerabilità critiche nel Penetration Test pre-go-live",
        "Conformità WCAG 2.1 AA certificata da ente terzo",
    ],
    "missing_fields": [],
    "clarification_questions": [],
}


async def run_example() -> None:
    print("=" * 70)
    print("  AI DOCUMENT PLATFORM — Esempio Workflow Capitolato")
    print("=" * 70)
    print()

    from app.workflows.state_machine.machine import (
        StateMachine,
        WorkflowContext,
        WorkflowTrigger,
    )
    from app.skills.validation.validation_skill import (
        validate_requirements_completeness,
        score_requirement_richness,
        detect_placeholder_content,
    )

    workflow_id = "demo-wf-001"
    ctx = WorkflowContext(
        workflow_id=workflow_id,
        document_type="capitolato",
    )
    sm = StateMachine()

    print(f"[1] Stato iniziale: {ctx.state}")

    # INIT → BRIEFING
    sm.trigger(ctx, WorkflowTrigger.START)
    print(f"[2] Trigger START → {ctx.state}")
    print(f"    Documento: {MOCK_REQUIREMENTS['project']['title']}")

    # Validate requirements
    await asyncio.sleep(0.1)
    validation = validate_requirements_completeness(MOCK_REQUIREMENTS, "capitolato")
    print(f"\n[3] Validazione requisiti:")
    print(f"    Valid: {validation.valid}")
    print(f"    Confidence: {validation.confidence:.0%}")
    richness = score_requirement_richness(MOCK_REQUIREMENTS)
    print(f"    Richness score: {richness:.0%}")

    # BRIEFING → ENRICHMENT → VALIDATION
    sm.trigger(ctx, WorkflowTrigger.REQUIREMENTS_COLLECTED)
    print(f"\n[4] Requisiti raccolti → {ctx.state}")

    await asyncio.sleep(0.1)
    sm.trigger(ctx, WorkflowTrigger.ENRICHMENT_DONE)
    print(f"[5] Arricchimento KB → {ctx.state}")

    sm.trigger(ctx, WorkflowTrigger.VALIDATION_PASSED)
    print(f"[6] Validazione passata → {ctx.state}")

    # WRITING
    await asyncio.sleep(0.1)
    sm.trigger(ctx, WorkflowTrigger.WRITING_DONE)
    print(f"\n[7] Documento generato → {ctx.state}")

    # Simulate quality check
    mock_quality = {
        "score": 0.87,
        "passed": True,
        "dimension_scores": {
            "completeness": 9, "consistency": 8, "clarity": 9,
            "technical_accuracy": 8, "legal_compliance": 9,
            "traceability": 8, "formatting": 9,
        },
        "issues": [],
        "missing_sections": [],
        "suggestions": ["Aggiungere riferimento a NIS2 nella sezione sicurezza"],
    }

    print(f"\n[8] Quality Review:")
    print(f"    Score: {mock_quality['score']:.0%}")
    print(f"    Passed: {mock_quality['passed']}")
    for dim, score in mock_quality["dimension_scores"].items():
        bar = "█" * score + "░" * (10 - score)
        print(f"    {dim:<22} {bar} {score}/10")

    sm.trigger(ctx, WorkflowTrigger.QUALITY_PASSED)
    print(f"\n[9] Quality approvata → {ctx.state}")

    print()
    print("=" * 70)
    print(f"  WORKFLOW COMPLETATO CON SUCCESSO")
    print(f"  Documento: {MOCK_REQUIREMENTS['project']['title']}")
    print(f"  Quality Score: {mock_quality['score']:.0%}")
    print(f"  Retry utilizzati: {ctx.retry_count}/{ctx.max_retries}")
    print("=" * 70)

    # Output summary JSON
    summary = {
        "workflow_id": workflow_id,
        "status": "COMPLETED",
        "document_type": "capitolato",
        "title": MOCK_REQUIREMENTS["project"]["title"],
        "quality_score": mock_quality["score"],
        "functional_requirements": len(MOCK_REQUIREMENTS["functional_requirements"]),
        "technical_requirements": len(MOCK_REQUIREMENTS["technical_requirements"]),
        "integrations": len(MOCK_REQUIREMENTS["integrations"]),
        "compliance_standards": MOCK_REQUIREMENTS["security_compliance"]["standards"],
    }
    print()
    print("Summary JSON:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run_example())
