#!/usr/bin/env python3
"""Fix all hardcoded lang === 'fr' ternaries in sections.tsx with 5-language support."""
import re

FILE = "/home/z/my-project/src/components/agent/sections.tsx"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

# Define replacements: (old_pattern, new_pattern)
# Using exact string matching
replacements = [
    # Overview section
    ('title={lang === "fr" ? "Aperçu" : "Overview"}',
     'title={L(lang, { en: "Overview", fr: "Aperçu", es: "Resumen", de: "Übersicht", pt: "Visão Geral" })}'),
    ('subtitle={lang === "fr" ? "\u00c9tat de l\'agent et actions rapides" : "Agent status and quick actions"}',
     'subtitle={L(lang, { en: "Agent status and quick actions", fr: "\u00c9tat de l\'agent et actions rapides", es: "Estado del agente y acciones r\u00e1pidas", de: "Agent-Status und Schnellaktionen", pt: "Status do agente e a\u00e7\u00f5es r\u00e1pidas" })}'),
    ('{lang === "fr" ? "agent actif" : "agent busy"}',
     '{L(lang, { en: "agent busy", fr: "agent actif", es: "agente activo", de: "Agent besch\u00e4ftigt", pt: "agente ativo" })}'),
    ('{submitting ? (lang === "fr" ? "Envoi..." : "Sending...") : tr("dash.send")}',
     '{submitting ? L(lang, { en: "Sending...", fr: "Envoi...", es: "Enviando...", de: "Senden...", pt: "Enviando..." }) : tr("dash.send")}'),
    ('{lang === "fr" ? "Modules" : "Modules"} ({MODULES_LIST.length})',
     '{L(lang, { en: "Modules", fr: "Modules", es: "M\u00f3dulos", de: "Module", pt: "M\u00f3dulos" })} ({MODULES_LIST.length})'),
    ('{lang === "fr" ? "Capacit\u00e9s" : "Capabilities"} ({CAPABILITIES.length})',
     '{L(lang, { en: "Capabilities", fr: "Capacit\u00e9s", es: "Capacidades", de: "F\u00e4higkeiten", pt: "Capacidades" })} ({CAPABILITIES.length})'),

    # Tasks section
    ('title={lang === "fr" ? "T\u00e2ches" : "Tasks"}',
     'title={L(lang, { en: "Tasks", fr: "T\u00e2ches", es: "Tareas", de: "Aufgaben", pt: "Tarefas" })}'),
    ('subtitle={lang === "fr" ? "Soumettez des t\u00e2ches et consultez l\'historique" : "Submit tasks and view history"}',
     'subtitle={L(lang, { en: "Submit tasks and view history", fr: "Soumettez des t\u00e2ches et consultez l\'historique", es: "Enviar tareas y ver historial", de: "Aufgaben senden und Verlauf anzeigen", pt: "Enviar tarefas e ver hist\u00f3rico" })}'),
    ('{lang === "fr" ? "Nouvelle t\u00e2che" : "New Task"}',
     '{L(lang, { en: "New Task", fr: "Nouvelle t\u00e2che", es: "Nueva Tarea", de: "Neue Aufgabe", pt: "Nova Tarefa" })}'),
    ('{lang === "fr" ? "Annuler" : "Cancel"}',
     '{L(lang, { en: "Cancel", fr: "Annuler", es: "Cancelar", de: "Abbrechen", pt: "Cancelar" })}'),
    ('{lang === "fr" ? "Raisonnement en direct" : "Live Reasoning"}',
     '{L(lang, { en: "Live Reasoning", fr: "Raisonnement en direct", es: "Razonamiento en vivo", de: "Live-Denken", pt: "Racioc\u00ednio ao vivo" })}'),
    ('{lang === "fr" ? "Historique" : "History"} ({tasks.length})',
     '{L(lang, { en: "History", fr: "Historique", es: "Historial", de: "Verlauf", pt: "Hist\u00f3rico" })} ({tasks.length})'),

    # Monitor section
    ('title={lang === "fr" ? "Moniteur" : "Monitor"}',
     'title={L(lang, { en: "Monitor", fr: "Moniteur", es: "Monitor", de: "Monitor", pt: "Monitor" })}'),
    ('subtitle={lang === "fr" ? "Logs, captures d\'\u00e9cran et audit" : "Logs, screenshots, and audit trail"}',
     'subtitle={L(lang, { en: "Logs, screenshots, and audit trail", fr: "Logs, captures d\'\u00e9cran et audit", es: "Registros, capturas y auditor\u00eda", de: "Protokolle, Screenshots und Audit-Trail", pt: "Logs, capturas e auditoria" })}'),
    ('{lang === "fr" ? "Aucun log. Connectez l\'agent Python." : "No logs. Connect the Python agent."}',
     '{L(lang, { en: "No logs. Connect the Python agent.", fr: "Aucun log. Connectez l\'agent Python.", es: "Sin registros. Conecta el agente Python.", de: "Keine Protokolle. Verbinde den Python-Agenten.", pt: "Sem logs. Conecte o agente Python." })}'),
    ('{lang === "fr" ? "Capturer" : "Capture"}',
     '{L(lang, { en: "Capture", fr: "Capturer", es: "Capturar", de: "Aufnehmen", pt: "Capturar" })}'),

    # Analytics section
    ('title={lang === "fr" ? "Analytique" : "Analytics"}',
     'title={L(lang, { en: "Analytics", fr: "Analytique", es: "Anal\u00edtica", de: "Analytik", pt: "An\u00e1lises" })}'),
    ('subtitle={lang === "fr" ? "Co\u00fbts, activit\u00e9 et statistiques" : "Costs, activity, and statistics"}',
     'subtitle={L(lang, { en: "Costs, activity, and statistics", fr: "Co\u00fbts, activit\u00e9 et statistiques", es: "Costos, actividad y estad\u00edsticas", de: "Kosten, Aktivit\u00e4t und Statistiken", pt: "Custos, atividade e estat\u00edsticas" })}'),

    # Automation section
    ('title={lang === "fr" ? "Automatisation" : "Automation"}',
     'title={L(lang, { en: "Automation", fr: "Automatisation", es: "Automatizaci\u00f3n", de: "Automatisierung", pt: "Automa\u00e7\u00e3o" })}'),
    ('subtitle={lang === "fr" ? "T\u00e2ches planifi\u00e9es, watchers, webhooks, templates" : "Scheduled tasks, watchers, webhooks, templates"}',
     'subtitle={L(lang, { en: "Scheduled tasks, watchers, webhooks, templates", fr: "T\u00e2ches planifi\u00e9es, watchers, webhooks, templates", es: "Tareas programadas, watchers, webhooks, plantillas", de: "Geplante Aufgaben, Watcher, Webhooks, Vorlagen", pt: "Tarefas agendadas, watchers, webhooks, modelos" })}'),

    # Knowledge section
    ('title={lang === "fr" ? "Connaissance" : "Knowledge"}',
     'title={L(lang, { en: "Knowledge", fr: "Connaissance", es: "Conocimiento", de: "Wissen", pt: "Conhecimento" })}'),
    ('subtitle={lang === "fr" ? "Base de connaissances RAG et m\u00e9moire vectorielle" : "RAG knowledge base and vector memory"}',
     'subtitle={L(lang, { en: "RAG knowledge base and vector memory", fr: "Base de connaissances RAG et m\u00e9moire vectorielle", es: "Base de conocimiento RAG y memoria vectorial", de: "RAG-Wissensbasis und Vektorspeicher", pt: "Base de conhecimento RAG e mem\u00f3ria vetorial" })}'),
    ('{lang === "fr" ? "M\u00e9moire vectorielle" : "Vector Memory"}',
     '{L(lang, { en: "Vector Memory", fr: "M\u00e9moire vectorielle", es: "Memoria vectorial", de: "Vektorspeicher", pt: "Mem\u00f3ria vetorial" })}'),
    ('{lang === "fr" ? "M\u00e9moire s\u00e9mantique longue dur\u00e9e" : "Long-term semantic memory"}',
     '{L(lang, { en: "Long-term semantic memory", fr: "M\u00e9moire s\u00e9mantique longue dur\u00e9e", es: "Memoria sem\u00e1ntica a largo plazo", de: "Langzeit-Semantikspeicher", pt: "Mem\u00f3ria sem\u00e2ntica de longo prazo" })}'),

    # Toast messages (both occurrences)
    ('toast({ title: lang === "fr" ? "T\u00e2che envoy\u00e9e" : "Task sent" });',
     'toast({ title: L(lang, { en: "Task sent", fr: "T\u00e2che envoy\u00e9e", es: "Tarea enviada", de: "Aufgabe gesendet", pt: "Tarefa enviada" }) });'),

    # Monitor tab labels
    ('label: lang === "fr" ? "Logs" : "Logs"', 'label: L(lang, { en: "Logs", fr: "Logs", es: "Registros", de: "Protokolle", pt: "Logs" })'),
    ('label: lang === "fr" ? "Captures" : "Screenshots"', 'label: L(lang, { en: "Screenshots", fr: "Captures", es: "Capturas", de: "Screenshots", pt: "Capturas" })'),
    ('label: lang === "fr" ? "Audit" : "Audit"', 'label: L(lang, { en: "Audit", fr: "Audit", es: "Auditor\u00eda", de: "Audit", pt: "Auditoria" })'),
]

count = 0
for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        count += 1
    else:
        # Try with different quote styles
        print(f"  NOT FOUND: {old[:80]}...")

# Also fix the two remaining "Sending..." in the Tasks section
content = content.replace(
    '{submitting ? (lang === "fr" ? "Envoi..." : "Sending...") : tr("dash.send")}',
    '{submitting ? L(lang, { en: "Sending...", fr: "Envoi...", es: "Enviando...", de: "Senden...", pt: "Enviando..." }) : tr("dash.send")}'
)

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\n✅ {count} replacements made")

# Verify no more lang === "fr" remain
remaining = content.count('lang === "fr"')
print(f"Remaining 'lang === \"fr\"' occurrences: {remaining}")
