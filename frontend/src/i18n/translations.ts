export type Locale = 'it' | 'en';

export const translations: Record<Locale, Record<string, string>> = {
  it: {
    // App
    'app.title': 'AI Document Platform',
    'app.subtitle': 'Enterprise Document Generator',

    // Navigation
    'nav.new': 'Nuovo',
    'nav.monitor': 'Monitor',
    'nav.document': 'Documento',
    'nav.knowledge': 'Knowledge',

    // Form - New Document
    'form.newDocument': 'Nuovo Documento',
    'form.newDocumentDesc': 'Avvia la generazione automatica tramite workflow multi-agente',
    'form.documentType': 'Tipo Documento',
    'form.capitolato': 'Capitolato di Gara',
    'form.capitolatoDesc': 'Documento procurement IT completo',
    'form.requisiti': 'Requisiti Funzionali',
    'form.requisitiDesc': 'Specifica requisiti tecnici e funzionali',
    'form.projectTitle': 'Titolo Progetto',
    'form.projectTitlePlaceholder': 'es. Sistema ERP Cloud per PA',
    'form.description': 'Descrizione Requisiti',
    'form.descriptionPlaceholder': 'Descrivi il progetto IT, gli obiettivi, i requisiti principali, le integrazioni necessarie, i vincoli di sicurezza e compliance…',
    'form.knowledgeSource': 'Knowledge Source (opzionale)',
    'form.noKnowledge': 'Nessuno (documenti standalone)',
    'form.knowledgeHint': '✓ Il documento verrà arricchito con la knowledge base selezionata',
    'form.startWorkflow': 'Avvia Workflow AI',

    // States
    'state.INIT': 'Inizializzazione',
    'state.BRIEFING': 'Raccolta Requisiti',
    'state.ENRICHMENT': 'Arricchimento KB',
    'state.VALIDATION': 'Validazione',
    'state.WRITING': 'Generazione Doc.',
    'state.QUALITY_ANALYSIS': 'Quality Review',
    'state.COMPLETED': 'Completato',
    'state.FAILED': 'Errore',

    // Monitor
    'monitor.title': 'Stato Workflow',
    'monitor.agents': 'Agenti AI',
    'monitor.qualityScore': 'Quality Score',
    'monitor.eventLog': 'Event Log',
    'monitor.noEvents': 'Nessun evento ancora…',
    'monitor.live': 'LIVE',
    'monitor.viewDocument': 'Visualizza Documento',
    'monitor.newWorkflow': 'Nuovo Workflow',

    // Agents
    'agent.orchestrator': 'Orchestrator',
    'agent.requirement': 'Requirement',
    'agent.procurement': 'Procurement',
    'agent.leadWriter': 'Lead Writer',
    'agent.quality': 'Quality Agent',
    'agent.running': 'In esecuzione…',
    'agent.completed': 'Completato in',
    'agent.waiting': 'In attesa',
    'agent.error': 'Errore',

    // Quality
    'quality.approved': '✓ APPROVATO',
    'quality.revision': '✗ REVISIONE',

    // Document
    'document.title': 'Documento Generato',
    'document.downloadDocx': 'DOCX',
    'document.downloadPdf': 'PDF',
    'document.noDocument': 'Nessun documento disponibile.',
    'document.completeWorkflow': 'Completa un workflow per generare un documento.',

    // MCP Settings
    'mcp.title': 'Knowledge Sources (MCP)',
    'mcp.subtitle': 'Connetti server MCP per arricchire la generazione documenti con conoscenza esterna',
    'mcp.addConnection': 'Aggiungi Connessione',
    'mcp.newConnection': 'Nuova Connessione MCP',
    'mcp.name': 'Nome',
    'mcp.namePlaceholder': 'es. LLMBase Wiki',
    'mcp.url': 'URL',
    'mcp.urlPlaceholder': 'http://localhost:8000/mcp',
    'mcp.transport': 'Transport',
    'mcp.apiKey': 'API Key',
    'mcp.apiKeyPlaceholder': 'Opzionale',
    'mcp.description': 'Descrizione',
    'mcp.descriptionPlaceholder': 'Descrizione opzionale',
    'mcp.cancel': 'Annulla',
    'mcp.testSave': 'Test & Salva',
    'mcp.connecting': 'Connessione…',
    'mcp.tools': 'Tools',
    'mcp.resources': 'Resources',
    'mcp.prompts': 'Prompts',
    'mcp.status': 'Stato',
    'mcp.lastCheck': 'Ultimo controllo',
    'mcp.transportLabel': 'Transport',
    'mcp.noConnections': 'Nessuna connessione configurata',
    'mcp.noConnectionsDesc': 'Aggiungi un server MCP per arricchire i documenti con conoscenza esterna',
    'mcp.deleteConfirm': 'Eliminare questa connessione?',
    'mcp.inactive': 'INATTIVO',
    'mcp.refresh': 'Aggiorna capabilities',
    'mcp.delete': 'Elimina',
    'mcp.testKb': 'Test & Scopri KB',
    'mcp.testingKb': 'Test in corso...',
    'mcp.knowledgeBase': 'Knowledge Base',
    'mcp.kbSelected': 'KB selezionata:',
    'mcp.selectKb': 'Seleziona una KB da interrogare',

    // Theme
    'theme.light': 'Chiaro',
    'theme.dark': 'Scuro',
    'theme.system': 'Sistema',

    // Language
    'lang.it': 'Italiano',
    'lang.en': 'English',

    // General
    'general.cancel': 'Annulla',
    'general.save': 'Salva',
    'general.delete': 'Elimina',
    'general.edit': 'Modifica',
    'general.close': 'Chiudi',
    'general.loading': 'Caricamento…',
    'general.error': 'Errore',
    'general.success': 'Successo',
  },

  en: {
    // App
    'app.title': 'AI Document Platform',
    'app.subtitle': 'Enterprise Document Generator',

    // Navigation
    'nav.new': 'New',
    'nav.monitor': 'Monitor',
    'nav.document': 'Document',
    'nav.knowledge': 'Knowledge',

    // Form - New Document
    'form.newDocument': 'New Document',
    'form.newDocumentDesc': 'Start automatic generation via multi-agent workflow',
    'form.documentType': 'Document Type',
    'form.capitolato': 'Tender Specifications',
    'form.capitolatoDesc': 'Complete IT procurement document',
    'form.requisiti': 'Functional Requirements',
    'form.requisitiDesc': 'Technical and functional requirements specification',
    'form.projectTitle': 'Project Title',
    'form.projectTitlePlaceholder': 'e.g. Cloud ERP System for Government',
    'form.description': 'Requirements Description',
    'form.descriptionPlaceholder': 'Describe the IT project, objectives, main requirements, integrations needed, security and compliance constraints…',
    'form.knowledgeSource': 'Knowledge Source (optional)',
    'form.noKnowledge': 'None (standalone documents)',
    'form.knowledgeHint': '✓ The document will be enriched with the selected knowledge base',
    'form.startWorkflow': 'Start AI Workflow',

    // States
    'state.INIT': 'Initialization',
    'state.BRIEFING': 'Requirements Gathering',
    'state.ENRICHMENT': 'KB Enrichment',
    'state.VALIDATION': 'Validation',
    'state.WRITING': 'Document Generation',
    'state.QUALITY_ANALYSIS': 'Quality Review',
    'state.COMPLETED': 'Completed',
    'state.FAILED': 'Error',

    // Monitor
    'monitor.title': 'Workflow Status',
    'monitor.agents': 'AI Agents',
    'monitor.qualityScore': 'Quality Score',
    'monitor.eventLog': 'Event Log',
    'monitor.noEvents': 'No events yet…',
    'monitor.live': 'LIVE',
    'monitor.viewDocument': 'View Document',
    'monitor.newWorkflow': 'New Workflow',

    // Agents
    'agent.orchestrator': 'Orchestrator',
    'agent.requirement': 'Requirement',
    'agent.procurement': 'Procurement',
    'agent.leadWriter': 'Lead Writer',
    'agent.quality': 'Quality Agent',
    'agent.running': 'Running…',
    'agent.completed': 'Completed in',
    'agent.waiting': 'Waiting',
    'agent.error': 'Error',

    // Quality
    'quality.approved': '✓ APPROVED',
    'quality.revision': '✗ REVISION',

    // Document
    'document.title': 'Generated Document',
    'document.downloadDocx': 'DOCX',
    'document.downloadPdf': 'PDF',
    'document.noDocument': 'No document available.',
    'document.completeWorkflow': 'Complete a workflow to generate a document.',

    // MCP Settings
    'mcp.title': 'Knowledge Sources (MCP)',
    'mcp.subtitle': 'Connect MCP servers to enrich document generation with external knowledge',
    'mcp.addConnection': 'Add Connection',
    'mcp.newConnection': 'New MCP Connection',
    'mcp.name': 'Name',
    'mcp.namePlaceholder': 'e.g. LLMBase Wiki',
    'mcp.url': 'URL',
    'mcp.urlPlaceholder': 'http://localhost:8000/mcp',
    'mcp.transport': 'Transport',
    'mcp.apiKey': 'API Key',
    'mcp.apiKeyPlaceholder': 'Optional',
    'mcp.description': 'Description',
    'mcp.descriptionPlaceholder': 'Optional description',
    'mcp.cancel': 'Cancel',
    'mcp.testSave': 'Test & Save',
    'mcp.connecting': 'Connecting…',
    'mcp.tools': 'Tools',
    'mcp.resources': 'Resources',
    'mcp.prompts': 'Prompts',
    'mcp.status': 'Status',
    'mcp.lastCheck': 'Last check',
    'mcp.transportLabel': 'Transport',
    'mcp.noConnections': 'No connections configured',
    'mcp.noConnectionsDesc': 'Add an MCP server to enrich documents with external knowledge',
    'mcp.deleteConfirm': 'Delete this connection?',
    'mcp.inactive': 'INACTIVE',
    'mcp.refresh': 'Refresh capabilities',
    'mcp.delete': 'Delete',
    'mcp.testKb': 'Test & Discover KBs',
    'mcp.testingKb': 'Testing...',
    'mcp.knowledgeBase': 'Knowledge Base',
    'mcp.kbSelected': 'Selected KB:',
    'mcp.selectKb': 'Select a KB to query',

    // Theme
    'theme.light': 'Light',
    'theme.dark': 'Dark',
    'theme.system': 'System',

    // Language
    'lang.it': 'Italiano',
    'lang.en': 'English',

    // General
    'general.cancel': 'Cancel',
    'general.save': 'Save',
    'general.delete': 'Delete',
    'general.edit': 'Edit',
    'general.close': 'Close',
    'general.loading': 'Loading…',
    'general.error': 'Error',
    'general.success': 'Success',
  }
};

export function getTranslation(locale: Locale, key: string): string {
  return translations[locale]?.[key] ?? key;
}
