#!/usr/bin/env python3
"""
Z.AGENT - Documentation PDF generator.
Uses ReportLab to produce a comprehensive installation & usage manual.
"""
import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle,
    KeepTogether, ListFlowable, ListItem, PageTemplate, Frame, NextPageTemplate,
    BaseDocTemplate,
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUTPUT_DIR = Path("/home/z/my-project/download")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PDF = OUTPUT_DIR / "Z-AGENT-Documentation.pdf"

# === Font registration ===
FONT_DIR_SERIF = "/usr/share/fonts/truetype/liberation"
FONT_DIR_SANS = "/usr/share/fonts/truetype/liberation"
FONT_DIR_MONO = "/usr/share/fonts/truetype/liberation"

pdfmetrics.registerFont(TTFont("BodyFont", f"{FONT_DIR_SERIF}/LiberationSerif-Regular.ttf"))
pdfmetrics.registerFont(TTFont("BodyFont-Bold", f"{FONT_DIR_SERIF}/LiberationSerif-Bold.ttf"))
pdfmetrics.registerFont(TTFont("BodyFont-Italic", f"{FONT_DIR_SERIF}/LiberationSerif-Italic.ttf"))
pdfmetrics.registerFont(TTFont("HeadFont", f"{FONT_DIR_SANS}/LiberationSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("HeadFont-Regular", f"{FONT_DIR_SANS}/LiberationSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("MonoFont", f"{FONT_DIR_MONO}/LiberationMono-Regular.ttf"))

# === Palette (Z.AGENT emerald/teal) ===
COLOR_PRIMARY = HexColor("#10B981")     # emerald-500
COLOR_PRIMARY_DARK = HexColor("#047857")  # emerald-700
COLOR_ACCENT = HexColor("#06B6D4")       # cyan-500
COLOR_DARK = HexColor("#0F172A")         # slate-900
COLOR_TEXT = HexColor("#1E293B")         # slate-800
COLOR_MUTED = HexColor("#64748B")        # slate-500
COLOR_BG_SOFT = HexColor("#F1F5F9")      # slate-100
COLOR_BORDER = HexColor("#E2E8F0")       # slate-200
COLOR_CODE_BG = HexColor("#1E293B")      # slate-800
COLOR_CODE_FG = HexColor("#E2E8F0")

# === Styles ===
styles = getSampleStyleSheet()

style_title = ParagraphStyle(
    "Title", parent=styles["Title"],
    fontName="HeadFont", fontSize=42, leading=48,
    textColor=COLOR_DARK, alignment=TA_LEFT, spaceAfter=8,
)
style_subtitle = ParagraphStyle(
    "Subtitle", parent=styles["Normal"],
    fontName="HeadFont-Regular", fontSize=18, leading=22,
    textColor=COLOR_PRIMARY_DARK, alignment=TA_LEFT, spaceAfter=4,
)
style_h1 = ParagraphStyle(
    "H1", parent=styles["Heading1"],
    fontName="HeadFont", fontSize=24, leading=30,
    textColor=COLOR_DARK, alignment=TA_LEFT,
    spaceBefore=20, spaceAfter=12,
    borderPadding=0, borderColor=COLOR_PRIMARY, borderWidth=0,
)
style_h2 = ParagraphStyle(
    "H2", parent=styles["Heading2"],
    fontName="HeadFont", fontSize=16, leading=22,
    textColor=COLOR_PRIMARY_DARK, alignment=TA_LEFT,
    spaceBefore=14, spaceAfter=8,
)
style_h3 = ParagraphStyle(
    "H3", parent=styles["Heading3"],
    fontName="HeadFont", fontSize=13, leading=18,
    textColor=COLOR_TEXT, alignment=TA_LEFT,
    spaceBefore=10, spaceAfter=6,
)
style_body = ParagraphStyle(
    "Body", parent=styles["BodyText"],
    fontName="BodyFont", fontSize=10.5, leading=16,
    textColor=COLOR_TEXT, alignment=TA_JUSTIFY,
    spaceAfter=8,
)
style_body_left = ParagraphStyle(
    "BodyLeft", parent=style_body,
    alignment=TA_LEFT,
)
style_bullet = ParagraphStyle(
    "Bullet", parent=style_body,
    leftIndent=18, bulletIndent=8, spaceAfter=4, alignment=TA_LEFT,
)
style_code = ParagraphStyle(
    "Code", parent=styles["Code"],
    fontName="MonoFont", fontSize=9, leading=13,
    textColor=COLOR_CODE_FG, backColor=COLOR_CODE_BG,
    leftIndent=10, rightIndent=10,
    borderPadding=8, spaceBefore=6, spaceAfter=10,
)
style_callout = ParagraphStyle(
    "Callout", parent=style_body,
    fontName="BodyFont-Italic", fontSize=10.5, leading=16,
    textColor=COLOR_DARK, backColor=HexColor("#FEF3C7"),
    borderColor=HexColor("#F59E0B"), borderWidth=0, borderPadding=10,
    leftIndent=10, rightIndent=10, spaceBefore=8, spaceAfter=10,
    alignment=TA_LEFT,
)
style_toc_entry = ParagraphStyle(
    "TocEntry", parent=style_body,
    fontSize=11, leading=18, alignment=TA_LEFT, spaceAfter=2,
)
style_footer = ParagraphStyle(
    "Footer", parent=styles["Normal"],
    fontName="HeadFont-Regular", fontSize=8, textColor=COLOR_MUTED,
    alignment=TA_CENTER,
)

# === Cover page callback ===
def draw_cover(canv, doc):
    canv.saveState()
    # Background gradient effect (emulated with rectangles)
    canv.setFillColor(COLOR_DARK)
    canv.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    # Emerald accent strip on the left
    canv.setFillColor(COLOR_PRIMARY)
    canv.rect(0, 0, 12, A4[1], fill=1, stroke=0)
    # Top accent line
    canv.setStrokeColor(COLOR_PRIMARY)
    canv.setLineWidth(2)
    canv.line(40, A4[1] - 60, A4[0] - 40, A4[1] - 60)
    canv.restoreState()

def draw_page(canv, doc):
    """Draw header/footer on body pages."""
    canv.saveState()
    # Footer line
    canv.setStrokeColor(COLOR_BORDER)
    canv.setLineWidth(0.5)
    canv.line(40, 36, A4[0] - 40, 36)
    # Footer text
    canv.setFont("HeadFont-Regular", 8)
    canv.setFillColor(COLOR_MUTED)
    canv.drawString(40, 24, "Z.AGENT — Documentation")
    canv.drawRightString(A4[0] - 40, 24, f"Page {doc.page}")
    # Top accent dot
    canv.setFillColor(COLOR_PRIMARY)
    canv.circle(A4[0] - 40, A4[1] - 30, 3, fill=1, stroke=0)
    canv.restoreState()

# === Build document ===
doc = BaseDocTemplate(
    str(OUTPUT_PDF),
    pagesize=A4,
    leftMargin=40, rightMargin=40, topMargin=50, bottomMargin=50,
    title="Z.AGENT — Documentation",
    author="Z.ai",
    subject="Agent de bureau autonome",
)

frame_cover = Frame(40, 40, A4[0] - 80, A4[1] - 80, id="cover")
frame_body = Frame(40, 50, A4[0] - 80, A4[1] - 100, id="body")

doc.addPageTemplates([
    PageTemplate(id="Cover", frames=[frame_cover], onPage=draw_cover),
    PageTemplate(id="Body", frames=[frame_body], onPage=draw_page),
])

story = []

# ============ COVER ============
story.append(Spacer(1, 4 * cm))
story.append(Paragraph(
    '<font color="#10B981" name="HeadFont" size="14">Z.AI · DESKTOP AUTOMATION</font>',
    ParagraphStyle("CoverLabel", fontName="HeadFont", fontSize=14, textColor=COLOR_PRIMARY, alignment=TA_LEFT)
))
story.append(Spacer(1, 1 * cm))
story.append(Paragraph(
    '<font color="white">Z.AGENT</font>',
    ParagraphStyle("CoverTitle", fontName="HeadFont", fontSize=56, leading=64, textColor=white, alignment=TA_LEFT)
))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph(
    '<font color="#06B6D4">Agent de bureau autonome</font>',
    ParagraphStyle("CoverSub", fontName="HeadFont", fontSize=22, leading=28, textColor=COLOR_ACCENT, alignment=TA_LEFT)
))
story.append(Spacer(1, 0.5 * cm))
story.append(Paragraph(
    '<font color="#CBD5E1">Pilotez votre ordinateur à distance via Telegram.<br/>'
    'Transformez z.ai coding plan en assistant de bureau 100% autonome.</font>',
    ParagraphStyle("CoverDesc", fontName="HeadFont-Regular", fontSize=13, leading=20, textColor=HexColor("#CBD5E1"), alignment=TA_LEFT)
))
story.append(Spacer(1, 5 * cm))
story.append(Paragraph(
    '<font color="#64748B">Version 1.0.0 · Juin 2026<br/>'
    'Propulsé par GLM-4.6, GLM-4V, GLM-4.5 (et GLM-5.x quand disponible)</font>',
    ParagraphStyle("CoverMeta", fontName="HeadFont-Regular", fontSize=10, textColor=COLOR_MUTED, alignment=TA_LEFT)
))

story.append(NextPageTemplate("Body"))
story.append(PageBreak())

# ============ TABLE OF CONTENTS ============
story.append(Paragraph("Table des matières", style_h1))
story.append(Spacer(1, 0.5 * cm))

toc_entries = [
    ("1. Introduction et vue d'ensemble", "4"),
    ("2. Architecture du système", "6"),
    ("3. Installation et configuration", "9"),
    ("4. Modules fonctionnels", "13"),
    ("   4.1. Screen Control — curseur et VLM", "13"),
    ("   4.2. File Manager — gestion des fichiers", "14"),
    ("   4.3. Email Client — IMAP et SMTP", "15"),
    ("   4.4. Calendar — calendrier ICS", "16"),
    ("   4.5. Browser Control — Playwright", "17"),
    ("   4.6. System Control — processus et notifications", "18"),
    ("5. Interface Telegram", "19"),
    ("6. Dashboard Web", "22"),
    ("7. Sécurité et bonnes pratiques", "24"),
    ("8. Exemples d'utilisation", "26"),
    ("9. Dépannage et FAQ", "29"),
    ("Annexe A — Référence des actions", "31"),
]

toc_data = [[Paragraph(label, style_toc_entry), Paragraph(f'<font color="#64748B">{page}</font>', style_toc_entry)]
            for label, page in toc_entries]
toc_table = Table(toc_data, colWidths=[14 * cm, 2 * cm])
toc_table.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ("LINEBELOW", (0, 0), (-1, -1), 0.3, COLOR_BORDER),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story.append(toc_table)
story.append(PageBreak())

# ============ CHAPTER 1: INTRODUCTION ============
story.append(Paragraph("1. Introduction et vue d'ensemble", style_h1))

story.append(Paragraph("1.1 Qu'est-ce que Z.AGENT ?", style_h2))
story.append(Paragraph(
    "Z.AGENT est un agent de bureau autonome propulsé par les modèles GLM de z.ai. "
    "Il transforme votre ordinateur en un système pilotable à distance : depuis votre smartphone via Telegram, "
    "ou depuis un tableau de bord web local, vous lui confiez des tâches en langage naturel et il les exécute "
    "automatiquement. L'agent est capable de déplacer le curseur, cliquer, taper du texte, "
    "gérer vos fichiers, lire et envoyer des emails, consulter votre calendrier, piloter un navigateur web, "
    "et contrôler les processus système. Il fonctionne en autonomie complète, sans supervision humaine nécessaire, "
    "ce qui le rend adapté à des scénarios comme la gestion de votre poste de travail pendant vos absences, "
    "l'automatisation de tâches répétitives, ou l'exécution de requêtes à distance quand vous n'avez pas accès à votre machine.",
    style_body
))
story.append(Paragraph(
    "La philosophie du projet est simple : transformer le « z.ai coding plan » en un véritable agent de bureau. "
    "Plutôt que de limiter l'IA à générer du code ou répondre à des questions, Z.AGENT lui donne le contrôle physique "
    "de votre ordinateur. Vous pouvez être en déplacement, en réunion, ou simplement absent — l'agent reste actif, "
    "écoute vos instructions Telegram, planifie les actions nécessaires, et les exécute en utilisant les bons modules "
    "pour chaque type de tâche. Le système repose sur une architecture multi-modèles où chaque GLM joue un rôle "
    "spécialisé : la planification, la perception visuelle, et l'exécution rapide.",
    style_body
))

story.append(Paragraph("1.2 Cas d'usage typiques", style_h2))
use_cases = [
    ("Organisation automatique", "L'agent surveille votre dossier Téléchargements et le trie par type de fichier (images, documents, archives, code, vidéos). Il peut aussi archiver les fichiers anciens et nettoyer les doublons."),
    ("Gestion des emails", "Pendant vos absences, l'agent lit vos emails non lus, vous envoie un résumé via Telegram, flagge les urgents, et peut répondre automatiquement aux messages simples avec votre accord."),
    ("Préparation de réunions", "L'agent consulte votre calendrier, prépare l'agenda de la journée, ouvre les documents pertinents dans les bonnes applications, et envoie des rappels aux participants."),
    ("Automatisation browser", "L'agent ouvre des sites web, remplit des formulaires, extrait des données, et scrape des pages selon vos besoins. Idéal pour surveiller des prix, remplir des déclarations, ou collecter des informations."),
    ("Maintenance système", "L'agent surveille les processus en cours, tue ceux qui consomment trop de ressources, lance les applications dont vous avez besoin, et vous notifie en cas de problème."),
    ("Tâches programmées", "Combinez l'agent avec le planificateur intégré pour exécuter des tâches récurrentes : sauvegardes, nettoyages, vérifications, ou tout autre scénario automatisable."),
]
for title, desc in use_cases:
    story.append(Paragraph(f"<b>{title}</b>", style_h3))
    story.append(Paragraph(desc, style_body))

story.append(Paragraph("1.3 Modèles z.ai utilisés", style_h2))
story.append(Paragraph(
    "Z.AGENT utilise une architecture multi-modèles pour optimiser les performances et le coût. "
    "Chaque modèle GLM joue un rôle précis dans la chaîne de traitement, en fonction de ses forces. "
    "Cette approche modulaire permet d'utiliser le bon modèle pour la bonne tâche, "
    "évitant ainsi de surconsommer des tokens sur des actions simples qui ne nécessitent pas "
    "un raisonnement complexe.",
    style_body
))

models_table = Table([
    [Paragraph("<b>Rôle</b>", style_body_left), Paragraph("<b>Modèle</b>", style_body_left), Paragraph("<b>Usage</b>", style_body_left)],
    [Paragraph("Planificateur", style_body_left), Paragraph("GLM-4.6", style_body_left),
     Paragraph("Décomposition des requêtes en plans d'actions multi-étapes. Raisonnement complexe.", style_body_left)],
    [Paragraph("Perception VLM", style_body_left), Paragraph("GLM-4V", style_body_left),
     Paragraph("Analyse des captures d'écran. Localisation des éléments UI. Compréhension visuelle.", style_body_left)],
    [Paragraph("Exécuteur", style_body_left), Paragraph("GLM-4.5", style_body_left),
     Paragraph("Actions simples et rapides. Parsing de réponses. Formatage de résultats.", style_body_left)],
    [Paragraph("Futur", style_body_left), Paragraph("GLM-5.1 / 5.2", style_body_left),
     Paragraph("Lorsque disponibles, remplaceront GLM-4.6 en tant que planificateur principal.", style_body_left)],
], colWidths=[3.5 * cm, 3 * cm, 9.5 * cm])
models_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
    ("TEXTCOLOR", (0, 0), (-1, 0), white),
    ("FONTNAME", (0, 0), (-1, 0), "HeadFont"),
    ("FONTSIZE", (0, 0), (-1, 0), 10),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, COLOR_BG_SOFT]),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
]))
story.append(models_table)
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph(
    "Pour activer GLM-5.x lorsque ces modèles seront disponibles, éditez le fichier "
    "<font name=\"MonoFont\">config/config.yaml</font> et changez la valeur de "
    "<font name=\"MonoFont\">zai.models.planner</font>. Le routeur multi-modèles s'occupe du reste.",
    style_body
))

story.append(PageBreak())

# ============ CHAPTER 2: ARCHITECTURE ============
story.append(Paragraph("2. Architecture du système", style_h1))

story.append(Paragraph("2.1 Vue d'ensemble", style_h2))
story.append(Paragraph(
    "L'architecture de Z.AGENT est organisée en couches clairement séparées. "
    "Au sommet, les interfaces utilisateur (Telegram, dashboard web, CLI) reçoivent les requêtes "
    "et les transmettent à l'agent. L'agent orchestre ensuite trois composants spécialisés : "
    "le planificateur qui décompose la tâche, l'exécuteur qui lance les actions, et la mémoire "
    "qui persiste le contexte. Les actions sont finalement routées vers les modules fonctionnels "
    "(screen, files, email, calendar, browser, system) qui interagissent avec le système hôte.",
    style_body
))

story.append(Paragraph("2.2 Composants principaux", style_h2))

story.append(Paragraph("Agent Loop", style_h3))
story.append(Paragraph(
    "L'agent loop est la boucle principale qui tourne en continu en arrière-plan. Elle écoute la file "
    "d'attente des tâches, dépile les requêtes dans l'ordre, et les traite une par une via le pipeline "
    "planification → exécution. Entre chaque tâche, elle effectue un ménage périodique : "
    "suppression des anciennes captures d'écran, vérification des rappels de calendrier, "
    "et exécution des tâches planifiées. L'agent expose son état (idle, planning, executing, paused, "
    "stopped) qui est visible en temps réel sur le dashboard et notifié via Telegram.",
    style_body
))

story.append(Paragraph("Planner (Planificateur)", style_h3))
story.append(Paragraph(
    "Le planner prend une requête en langage naturel (ex : « Trie mes téléchargements par type ») "
    "et la décompose en une séquence d'actions atomiques exécutables. Il utilise un prompt système "
    "détaillé qui liste toutes les actions disponibles, leur signature, et les règles de sécurité. "
    "La sortie est un objet JSON structuré contenant la compréhension de la requête, le plan complet, "
    "les risques identifiés, et une estimation du temps nécessaire. En cas d'échec d'une étape, "
    "le planner peut être rappelé pour générer un plan alternatif à partir de l'état courant.",
    style_body
))

story.append(Paragraph("Executor (Exécuteur)", style_h3))
story.append(Paragraph(
    "L'executor reçoit le plan généré et exécute chaque étape séquentiellement. Il route chaque action "
    "vers le handler de module approprié, applique les vérifications de sécurité avant l'exécution, "
    "et journalise le résultat (succès, erreur, durée). Un délai de sécurité configurable sépare chaque "
    "action pour éviter les effets de bord liés à la rapidité d'exécution. L'executor supporte aussi "
    "les handlers synchrones et asynchrones indifféremment.",
    style_body
))

story.append(Paragraph("Perception VLM", style_h3))
story.append(Paragraph(
    "Le module de perception utilise GLM-4V pour comprendre visuellement l'écran. Il capture des "
    "screenshots à la demande, les redimensionne pour optimiser le coût des tokens, et les envoie "
    "au modèle de vision avec une question spécifique. Il peut localiser un élément UI par description "
    " (« le bouton Envoyer en bas à droite »), décrire le contenu global de l'écran, ou vérifier "
    "qu'une action a eu l'effet attendu. Les coordonnées renvoyées par le VLM sont recalculées "
    "en résolution native avant d'être passées à PyAutoGUI.",
    style_body
))

story.append(Paragraph("Memory (Mémoire)", style_h3))
story.append(Paragraph(
    "La mémoire est divisée en deux tiers : volatile (session) et persistante (fichier JSON). "
    "La mémoire volatile stocke le contexte de la session en cours (états transitoires, variables "
    "de travail). La mémoire persistante conserve les faits utilisateur (préférences, raccourcis "
    "appris, historique des tâches) entre les redémarrages. Le module peut rechercher dans l'historique "
    "par mots-clés, ce qui permet à l'agent de retrouver le contexte d'une tâche similaire déjà exécutée.",
    style_body
))

story.append(Paragraph("2.3 Flux d'exécution d'une tâche", style_h2))
story.append(Paragraph(
    "Le parcours complet d'une tâche, depuis l'instruction utilisateur jusqu'au résultat final, "
    "suit ces étapes :",
    style_body
))

flow_data = [
    [Paragraph("<b>Étape</b>", style_body_left), Paragraph("<b>Composant</b>", style_body_left), Paragraph("<b>Action</b>", style_body_left)],
    [Paragraph("1", style_body_left), Paragraph("Interface", style_body_left),
     Paragraph("L'utilisateur envoie une requête via Telegram, le dashboard, ou la CLI.", style_body_left)],
    [Paragraph("2", style_body_left), Paragraph("Agent Loop", style_body_left),
     Paragraph("La tâche est ajoutée à la file d'attente avec un ID unique.", style_body_left)],
    [Paragraph("3", style_body_left), Paragraph("Planner", style_body_left),
     Paragraph("GLM-4.6 décompose la requête en plan d'actions atomiques (JSON).", style_body_left)],
    [Paragraph("4", style_body_left), Paragraph("Executor", style_body_left),
     Paragraph("Chaque étape est exécutée par le module approprié après vérification de sécurité.", style_body_left)],
    [Paragraph("5", style_body_left), Paragraph("Perception", style_body_left),
     Paragraph("Si l'action nécessite un retour visuel, GLM-4V analyse l'écran pour confirmer.", style_body_left)],
    [Paragraph("6", style_body_left), Paragraph("Memory", style_body_left),
     Paragraph("La tâche et son résultat sont enregistrés dans l'historique persistant.", style_body_left)],
    [Paragraph("7", style_body_left), Paragraph("Interface", style_body_left),
     Paragraph("Le résultat est notifié à l'utilisateur (Telegram / dashboard en temps réel).", style_body_left)],
]
flow_table = Table(flow_data, colWidths=[1.2 * cm, 3 * cm, 11.8 * cm])
flow_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
    ("TEXTCOLOR", (0, 0), (-1, 0), white),
    ("FONTNAME", (0, 0), (-1, 0), "HeadFont"),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, COLOR_BG_SOFT]),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story.append(flow_table)

story.append(PageBreak())

# ============ CHAPTER 3: INSTALLATION ============
story.append(Paragraph("3. Installation et configuration", style_h1))

story.append(Paragraph("3.1 Prérequis système", style_h2))
story.append(Paragraph(
    "Z.AGENT fonctionne sur les trois systèmes d'exploitation majeurs : Windows 10/11, macOS 11+, "
    "et Linux (Ubuntu 20.04+ ou équivalent). Il nécessite Python 3.10 ou supérieur, ainsi que "
    "les droits d'administration pour l'installation des dépendances système. Sur Linux, "
    "vous devrez installer les bibliothèques X11 pour le contrôle écran. Sur macOS, "
    "vous devrez accorder les permissions d'accessibilité à Python dans Préférences Système → "
    "Sécurité et confidentialité → Confidentialité → Accessibilité. Sur Windows, "
    "le contrôle écran fonctionne nativement sans configuration supplémentaire.",
    style_body
))

story.append(Paragraph("3.2 Installation des dépendances", style_h2))
story.append(Paragraph("Clonez ou téléchargez le projet, puis installez les dépendances Python :", style_body))
story.append(Paragraph(
    "cd desktop-agent<br/>"
    "python -m venv venv<br/>"
    "source venv/bin/activate  # Linux/macOS<br/>"
    "# ou: venv\\Scripts\\activate  # Windows<br/>"
    "pip install -r requirements.txt<br/>"
    "playwright install chromium",
    style_code
))

story.append(Paragraph("3.3 Obtention des clés API", style_h2))

story.append(Paragraph("Clé API z.ai", style_h3))
story.append(Paragraph(
    "Rendez-vous sur https://z.ai/ et créez un compte. Une fois connecté, accédez au tableau de bord "
    "développeur et générez une clé API. Cette clé est nécessaire pour appeler les modèles GLM "
    "(4.5, 4.6, 4V). Conservez-la précieusement, elle sera utilisée pour toutes les requêtes IA. "
    "Le coût est facturé à l'usage, mais reste très abordable pour un usage personnel — comptez "
    "environ 0,01 € par tâche complexe en moyenne.",
    style_body
))

story.append(Paragraph("Token Telegram Bot", style_h3))
story.append(Paragraph(
    "Pour contrôler l'agent à distance via Telegram, créez un bot en parlant à @BotFather sur Telegram. "
    "Envoyez la commande /newbot, suivez les instructions pour nommer votre bot, "
    "et récupérez le token d'API au format numérique. Ensuite, récupérez votre identifiant utilisateur "
    "Telegram en parlant à @userinfobot — cet ID sera utilisé pour restreindre l'accès à votre bot "
    "(personne d'autre que vous ne pourra donner des ordres à votre agent).",
    style_body
))

story.append(Paragraph("Identifiants email (optionnel)", style_h3))
story.append(Paragraph(
    "Pour activer le module email, vous aurez besoin d'un mot de passe d'application (et non de votre "
    "mot de passe habituel). Pour Gmail, activez la validation en deux étapes sur votre compte, "
    "puis générez un mot de passe d'application sur https://myaccount.google.com/apppasswords. "
    "Pour Outlook et les autres fournisseurs, la procédure est similaire. Ce mot de passe sera stocké "
    "dans la configuration et utilisé pour les connexions IMAP et SMTP.",
    style_body
))

story.append(Paragraph("3.4 Fichier de configuration", style_h2))
story.append(Paragraph(
    "Toutes les variables sensibles doivent être placées dans un fichier <font name=\"MonoFont\">.env</font> "
    "à la racine du projet, qui ne sera jamais versionné :",
    style_body
))
story.append(Paragraph(
    '# .env<br/>'
    'ZAI_API_KEY=votre-cle-api-z.ai<br/>'
    'TELEGRAM_BOT_TOKEN=123456:ABC-DEF...<br/>'
    'EMAIL_USER=vous@gmail.com<br/>'
    'EMAIL_APP_PASSWORD=aaaa-bbbb-cccc-dddd',
    style_code
))

story.append(Paragraph(
    "Le fichier <font name=\"MonoFont\">config/config.yaml</font> contient tous les autres paramètres : "
    "dossiers surveillés, règles d'organisation, modèles IA à utiliser, seuils de confiance VLM, "
    "intervalles de perception, et politique de sécurité. Chaque section est commentée en détail. "
    "Vous pouvez surcharger n'importe quelle valeur via une variable d'environnement avec le préfixe "
    "<font name=\"MonoFont\">ZDA_</font> (ex : <font name=\"MonoFont\">ZDA_screen_scale=0.5</font>).",
    style_body
))

story.append(Paragraph("3.5 Vérification de l'installation", style_h2))
story.append(Paragraph(
    "Avant le premier lancement, exécutez la commande de vérification pour vous assurer que "
    "tout est en place :",
    style_body
))
story.append(Paragraph(
    "python main.py --check",
    style_code
))
story.append(Paragraph(
    "Cette commande vérifie la présence du fichier de configuration, l'existence des clés API, "
    "et l'installation correcte de chaque dépendance Python. Elle affiche un rapport clair avec "
    "des ✓ verts pour les éléments validés et des ⚠️ oranges pour les éléments manquants. "
    "Une fois tous les checks au vert, vous pouvez lancer l'agent.",
    style_body
))

story.append(Paragraph("3.6 Premier lancement", style_h2))
story.append(Paragraph(
    "Le mode serveur (par défaut) démarre simultanément l'agent, le bot Telegram, "
    "l'API web FastAPI sur le port 8765, et le planificateur :",
    style_body
))
story.append(Paragraph(
    "python main.py<br/>",
    style_code
))
story.append(Paragraph(
    "Pour tester rapidement sans Telegram ni dashboard, utilisez le mode CLI interactif : "
    "vous saisissez vos demandes directement dans le terminal et voyez le résultat. "
    "Pour exécuter une tâche unique et sortir, utilisez <font name=\"MonoFont\">--task \"votre demande\"</font>. "
    "Le mode CLI est idéal pour déboguer un module spécifique ou valider que l'agent comprend "
    "correctement vos requêtes.",
    style_body
))

story.append(PageBreak())

# ============ CHAPTER 4: MODULES ============
story.append(Paragraph("4. Modules fonctionnels", style_h1))
story.append(Paragraph(
    "Z.AGENT est composé de six modules spécialisés, chacun responsable d'un domaine fonctionnel. "
    "Chaque module enregistre ses actions auprès de l'exécuteur central, qui route les requêtes "
    "du planner vers le bon handler. Cette architecture modulaire permet d'ajouter, retirer, "
    "ou remplacer un module sans affecter le reste du système.",
    style_body
))

story.append(Paragraph("4.1 Screen Control — curseur et VLM", style_h2))
story.append(Paragraph(
    "Le module Screen Control est le cœur du pilotage visuel. Il s'appuie sur PyAutoGUI pour "
    "le contrôle bas niveau (clics, frappe, défilement) et sur la perception VLM pour la "
    "compréhension de l'interface. Il peut cliquer sur un élément décrit en langage naturel "
    "( « le bouton bleu en haut à droite » ), taper du texte y compris en Unicode via le "
    "presse-papier pour contourner les limitations de PyAutoGUI, faire des raccourcis clavier, "
    "et faire des drag-and-drop. Le module inclut aussi un mécanisme de retry : si un élément "
    "n'est pas trouvé du premier coup, il retente la capture et l'analyse.",
    style_body
))
story.append(Paragraph(
    "Actions disponibles : <font name=\"MonoFont\">screen.click_element</font>, "
    "<font name=\"MonoFont\">screen.click_xy</font>, <font name=\"MonoFont\">screen.type_text</font>, "
    "<font name=\"MonoFont\">screen.press_key</font>, <font name=\"MonoFont\">screen.hotkey</font>, "
    "<font name=\"MonoFont\">screen.scroll</font>, <font name=\"MonoFont\">screen.screenshot</font>, "
    "<font name=\"MonoFont\">screen.wait</font>, <font name=\"MonoFont\">screen.find_and_click</font>, "
    "<font name=\"MonoFont\">screen.drag</font>.",
    style_body
))

story.append(Paragraph("4.2 File Manager — gestion des fichiers", style_h2))
story.append(Paragraph(
    "Le module File Manager gère tout ce qui touche aux fichiers et dossiers. Il peut lister, "
    "déplacer, copier, renommer, supprimer (vers la corbeille par défaut), organiser automatiquement "
    "par type d'extension, rechercher par nom ou par contenu, et lire/écrire du texte. "
    "Les règles d'organisation sont entièrement configurables dans le fichier YAML : "
    "vous définissez les catégories (Images, Documents, Archives, Code, etc.) et les extensions "
    "associées. L'agent peut aussi faire des dry-runs pour voir ce qui serait déplacé avant "
    "de commiter l'organisation.",
    style_body
))
story.append(Paragraph(
    "Actions disponibles : <font name=\"MonoFont\">files.list</font>, "
    "<font name=\"MonoFont\">files.move</font>, <font name=\"MonoFont\">files.copy</font>, "
    "<font name=\"MonoFont\">files.rename</font>, <font name=\"MonoFont\">files.delete</font>, "
    "<font name=\"MonoFont\">files.organize</font>, <font name=\"MonoFont\">files.search</font>, "
    "<font name=\"MonoFont\">files.read</font>, <font name=\"MonoFont\">files.write</font>, "
    "<font name=\"MonoFont\">files.create_dir</font>.",
    style_body
))

story.append(Paragraph("4.3 Email Client — IMAP et SMTP", style_h2))
story.append(Paragraph(
    "Le module Email gère la réception via IMAP et l'envoi via SMTP. Il supporte les connexions "
    "SSL/TLS, les pièces jointes, et le HTML. Côté lecture, il peut récupérer les emails non lus, "
    "rechercher par sujet ou contenu, marquer comme lu, et lister les dossiers. Côté envoi, il gère "
    "les destinataires multiples (To, Cc, Bcc), les pièces jointes, et le format HTML. "
    "Le module fonctionne avec tous les fournisseurs standards : Gmail, Outlook, Yahoo, "
    "et tout serveur IMAP/SMTP personnalisé. La configuration se fait dans la section email "
    "du fichier config.yaml.",
    style_body
))
story.append(Paragraph(
    "Actions disponibles : <font name=\"MonoFont\">email.send</font>, "
    "<font name=\"MonoFont\">email.read_unread</font>, <font name=\"MonoFont\">email.search</font>, "
    "<font name=\"MonoFont\">email.reply</font>, <font name=\"MonoFont\">email.mark_read</font>, "
    "<font name=\"MonoFont\">email.list_folders</font>.",
    style_body
))

story.append(Paragraph("4.4 Calendar — calendrier ICS", style_h2))
story.append(Paragraph(
    "Le module Calendar gère les événements au format ICS, le standard universel des calendriers. "
    "Il peut lire les fichiers ICS exportés depuis Google Calendar, Outlook, ou Apple Calendar, "
    "et gère aussi un calendrier local que l'agent peut modifier. Il supporte les événements "
    "récurrents (via la bibliothèque recurring-ical-events), peut créer de nouveaux événements, "
    "en supprimer, en chercher par texte, et positionner des rappels qui déclencheront une "
    "notification système et un message Telegram X minutes avant l'événement.",
    style_body
))
story.append(Paragraph(
    "Actions disponibles : <font name=\"MonoFont\">calendar.list</font>, "
    "<font name=\"MonoFont\">calendar.create</font>, <font name=\"MonoFont\">calendar.delete</font>, "
    "<font name=\"MonoFont\">calendar.search</font>, <font name=\"MonoFont\">calendar.remind</font>.",
    style_body
))

story.append(Paragraph("4.5 Browser Control — Playwright", style_h2))
story.append(Paragraph(
    "Le module Browser Control s'appuie sur Playwright pour piloter un navigateur Chromium, Firefox, "
    "ou WebKit. Il peut ouvrir des URLs, cliquer sur des sélecteurs CSS, remplir des formulaires, "
    "extraire du texte ou du HTML, prendre des screenshots, scroller, et exécuter du JavaScript "
    "arbitraire sur la page. Le navigateur peut tourner en mode headless (invisible) ou visible "
    "pour le débogage. Le profil utilisateur est persistant, ce qui permet de garder les sessions "
    "connectées entre deux lancements. Idéal pour les tâches de scraping, de remplissage de "
    "formulaires répétitifs, ou de surveillance de sites web.",
    style_body
))
story.append(Paragraph(
    "Actions disponibles : <font name=\"MonoFont\">browser.open</font>, "
    "<font name=\"MonoFont\">browser.click</font>, <font name=\"MonoFont\">browser.fill</font>, "
    "<font name=\"MonoFont\">browser.screenshot</font>, <font name=\"MonoFont\">browser.extract</font>, "
    "<font name=\"MonoFont\">browser.scroll</font>, <font name=\"MonoFont\">browser.evaluate</font>, "
    "<font name=\"MonoFont\">browser.close</font>.",
    style_body
))

story.append(Paragraph("4.6 System Control — processus et notifications", style_h2))
story.append(Paragraph(
    "Le module System Control gère les opérations système : lancement et arrêt d'applications, "
    "liste des processus avec leur consommation CPU/RAM, notifications système cross-platform, "
    "presse-papier, ouverture de fichiers dans leur application par défaut, et exécution de "
    "commandes shell (avec filtrage des commandes dangereuses). Le lancement d'applications "
    "est par défaut restreint à une whitelist configurable, ce qui empêche l'agent de lancer "
    "des applications arbitraires sans votre accord préalable. Le module inclut aussi une "
    "commande d'informations système qui remonte CPU, RAM, disque, et version de l'OS.",
    style_body
))
story.append(Paragraph(
    "Actions disponibles : <font name=\"MonoFont\">system.launch_app</font>, "
    "<font name=\"MonoFont\">system.kill_app</font>, <font name=\"MonoFont\">system.list_processes</font>, "
    "<font name=\"MonoFont\">system.notification</font>, <font name=\"MonoFont\">system.clipboard_get</font>, "
    "<font name=\"MonoFont\">system.clipboard_set</font>, <font name=\"MonoFont\">system.open_path</font>, "
    "<font name=\"MonoFont\">system.system_info</font>, <font name=\"MonoFont\">system.run_command</font>.",
    style_body
))

story.append(PageBreak())

# ============ CHAPTER 5: TELEGRAM ============
story.append(Paragraph("5. Interface Telegram", style_h1))

story.append(Paragraph("5.1 Configuration du bot", style_h2))
story.append(Paragraph(
    "L'interface Telegram est le canal principal pour piloter l'agent à distance. Après avoir créé "
    "votre bot via @BotFather et récupéré le token, ajoutez-le dans le fichier .env. "
    "Important : définissez votre identifiant utilisateur dans le champ allowed_user_ids "
    "de la configuration Telegram. Cela restreint l'usage du bot à vous seul, empêchant quiconque "
    "d'autre de donner des ordres à votre agent. Si cet identifiant est à 0, le bot répond à tout "
    "le monde (déconseillé en production).",
    style_body
))

story.append(Paragraph("5.2 Commandes slash disponibles", style_h2))
story.append(Paragraph(
    "Les commandes slash offrent un accès rapide aux fonctionnalités principales. Elles sont "
    "prévisibles, scriptables, et évitent d'utiliser des tokens IA pour des tâches simples. "
    "Pour les tâches complexes, utilisez plutôt le mode langage naturel.",
    style_body
))

cmd_data = [
    [Paragraph("<b>Commande</b>", style_body_left), Paragraph("<b>Description</b>", style_body_left)],
    [Paragraph("/start", style_body_left), Paragraph("Vérifier le statut de l'agent et confirmer qu'il est en ligne.", style_body_left)],
    [Paragraph("/status", style_body_left), Paragraph("État détaillé : tâche courante, file d'attente, mémoire.", style_body_left)],
    [Paragraph("/help", style_body_left), Paragraph("Afficher l'aide complète avec toutes les commandes.", style_body_left)],
    [Paragraph("/screenshot", style_body_left), Paragraph("Capture d'écran instantanée envoyée directement dans Telegram.", style_body_left)],
    [Paragraph("/pause /resume", style_body_left), Paragraph("Mettre l'agent en pause ou le reprendre.", style_body_left)],
    [Paragraph("/cancel", style_body_left), Paragraph("Vider la file d'attente des tâches en attente.", style_body_left)],
    [Paragraph("/memory", style_body_left), Paragraph("Afficher l'état de la mémoire (faits, préférences, raccourcis).", style_body_left)],
    [Paragraph("/files organize", style_body_left), Paragraph("Trier le dossier Téléchargements par type de fichier.", style_body_left)],
    [Paragraph("/files list [path]", style_body_left), Paragraph("Lister les fichiers d'un dossier (Bureau par défaut).", style_body_left)],
    [Paragraph("/email unread", style_body_left), Paragraph("Lire les 5 derniers emails non lus avec résumé.", style_body_left)],
    [Paragraph("/email send to | subject | body", style_body_left), Paragraph("Envoyer un email (séparez les champs par |).", style_body_left)],
    [Paragraph("/calendar list", style_body_left), Paragraph("Lister les 10 prochains événements de calendrier.", style_body_left)],
    [Paragraph("/system info", style_body_left), Paragraph("Afficher les informations système (CPU, RAM, disque).", style_body_left)],
    [Paragraph("/browser open url", style_body_left), Paragraph("Ouvrir une URL dans le navigateur.", style_body_left)],
]
cmd_table = Table(cmd_data, colWidths=[5 * cm, 11 * cm])
cmd_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
    ("TEXTCOLOR", (0, 0), (-1, 0), white),
    ("FONTNAME", (0, 0), (-1, 0), "HeadFont"),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, COLOR_BG_SOFT]),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
story.append(cmd_table)

story.append(Paragraph("5.3 Mode langage naturel", style_h2))
story.append(Paragraph(
    "Au-delà des commandes slash, vous pouvez simplement écrire votre demande en langage naturel. "
    "L'agent utilise GLM-4.6 pour comprendre l'intention, planifier les actions nécessaires, et "
    "les exécuter. Ce mode est plus souple mais consomme des tokens IA. Quelques exemples :",
    style_body
))
examples = [
    "« Tri mes téléchargements par type de fichier »",
    "« Envoie un mail à alice@example.com pour confirmer la réunion de demain à 14h »",
    "« Capture l'écran et dis-moi ce qu'il y a dessus »",
    "« Ouvre Gmail dans le navigateur et connecte-toi »",
    "« Liste mes 10 prochains événements de calendrier »",
    "« Trouve tous les fichiers PDF créés cette semaine dans Documents »",
    "« Ferme toutes les fenêtres Chrome et relance-les »",
    "« Prépare un email avec en pièce jointe le dernier fichier du Bureau »",
]
for ex in examples:
    story.append(Paragraph(f"• {ex}", style_bullet))

story.append(Paragraph(
    "Quand vous envoyez une demande, l'agent confirme la réception avec un ID de tâche, "
    "puis vous notifie du résultat une fois la tâche terminée. Si une étape échoue, "
    "le message indique quelle étape et quelle erreur, ce qui vous permet d'ajuster "
    "votre demande ou de relancer.",
    style_body
))

story.append(PageBreak())

# ============ CHAPTER 6: DASHBOARD ============
story.append(Paragraph("6. Dashboard Web", style_h1))

story.append(Paragraph("6.1 Vue d'ensemble", style_h2))
story.append(Paragraph(
    "Le dashboard web est une interface Next.js qui se connecte à l'API FastAPI de l'agent "
    "pour offrir une visualisation en temps réel de son activité. Il affiche l'état courant "
    "(idle, planning, executing, paused), la file d'attente, la mémoire, les logs en streaming, "
    "les captures d'écran, et l'historique des tâches. C'est l'outil idéal pour surveiller "
    "l'agent quand vous êtes devant votre ordinateur, ou pour déboguer une tâche qui ne se "
    "comporte pas comme prévu.",
    style_body
))

story.append(Paragraph("6.2 Installation du dashboard", style_h2))
story.append(Paragraph(
    "Le dashboard est un projet Next.js séparé. Pour le lancer :",
    style_body
))
story.append(Paragraph(
    "cd dashboard<br/>"
    "bun install<br/>"
    "bun run dev",
    style_code
))
story.append(Paragraph(
    "Le dashboard écoute par défaut sur le port 3000 et se connecte à l'API agent sur "
    "le port 8765. Si votre API agent est sur une autre machine, définissez la variable "
    "d'environnement <font name=\"MonoFont\">NEXT_PUBLIC_AGENT_API</font> avec l'URL complète "
    "(ex : <font name=\"MonoFont\">http://192.168.1.10:8765</font>). Le dashboard gère "
    "automatiquement la reconnexion WebSocket en cas de coupure réseau.",
    style_body
))

story.append(Paragraph("6.3 Fonctionnalités principales", style_h2))

features = [
    ("Statut temps réel", "L'état de l'agent est mis à jour en direct via WebSocket. Vous voyez immédiatement quand il passe de idle à planning, puis à executing."),
    ("Soumission de tâches", "Un formulaire permet de saisir des tâches directement depuis le dashboard, avec des boutons de raccourcis pour les tâches les plus courantes (trier fichiers, lire emails, etc.)."),
    ("Historique des tâches", "Chaque tâche exécutée est listée avec son plan détaillé (chaque étape, son action, son résultat). Cliquez sur une tâche pour voir le déraillement complet."),
    ("Logs en streaming", "Les logs de l'agent sont diffusés en temps réel via WebSocket, avec code couleur par niveau (INFO, WARNING, ERROR). Idéal pour déboguer en direct."),
    ("Galerie de captures", "Toutes les captures d'écran prises par le module VLM sont visibles dans une galerie, avec timestamp. Vous pouvez cliquer pour voir en grand."),
    ("Contrôle de l'agent", "Boutons Pause / Resume / Stop pour contrôler l'agent directement depuis le dashboard, sans passer par Telegram."),
]
for title, desc in features:
    story.append(Paragraph(f"<b>{title}</b>", style_h3))
    story.append(Paragraph(desc, style_body))

story.append(Paragraph("6.4 Architecture du dashboard", style_h2))
story.append(Paragraph(
    "Le dashboard est construit avec Next.js 16, React 19, TypeScript, Tailwind CSS 4, "
    "et shadcn/ui. Il utilise deux WebSockets : un pour les logs (ws/logs) et un pour les "
    "événements de progression (ws/progress). L'API REST est utilisée pour les actions "
    "ponctuelles (soumission de tâche, commande de contrôle, récupération des screenshots). "
    "Le polling de statut toutes les 3 secondes sert de fallback si la WebSocket se déconnecte. "
    "Le design est en thème sombre avec accents emerald et teal, optimisé pour une lecture "
    "prolongée sans fatigue oculaire.",
    style_body
))

story.append(PageBreak())

# ============ CHAPTER 7: SECURITY ============
story.append(Paragraph("7. Sécurité et bonnes pratiques", style_h1))

story.append(Paragraph("7.1 Politique de sécurité par défaut", style_h2))
story.append(Paragraph(
    "Z.AGENT est configuré par défaut en mode « plein contrôle » : l'agent peut exécuter "
    "des actions destructives sans demander de confirmation. Ce mode est adapté à un usage "
    "de confiance où vous êtes seul à utiliser l'agent et où vous acceptez les risques. "
    "Toutefois, même en plein contrôle, certaines protections restent actives en permanence "
    "pour éviter les catastrophes.",
    style_body
))

story.append(Paragraph(
    "Chemins protégés : les dossiers ~/.ssh, ~/.aws, ~/.config/1password, /etc/passwd, "
    "/etc/shadow ne sont jamais accessibles en lecture, écriture, ou suppression. "
    "Cette liste est configurable dans la section security.protected_paths du fichier "
    "de configuration. Ajoutez-y tout dossier sensible propre à votre environnement "
    "(coffres-forts cryptographiques, dossiers de configuration de mots de passe, etc.).",
    style_body
))

story.append(Paragraph(
    "Actions bloquées : certaines actions sont interdites par défaut, quel que soit le mode. "
    "Il s'agit de format_disk, rm_rf_root, modify_system_files, shutdown_system, "
    "reboot_system. L'agent refusera toujours de les exécuter, même si vous lui demandez "
    "explicitement. Cette liste est aussi configurable, mais nous recommandons de la laisser "
    "telle quelle.",
    style_body
))

story.append(Paragraph("7.2 Bonnes pratiques recommandées", style_h2))

practices = [
    ("Restreindre l'accès Telegram", "Configurez allowed_user_ids avec votre identifiant Telegram. Sans cette restriction, n'importe qui connaissant le nom de votre bot pourrait lui envoyer des ordres."),
    ("Utiliser un mot de passe d'application", "Ne mettez jamais votre mot de passe email principal dans la configuration. Utilisez toujours un mot de passe d'application dédié, révocable à tout moment."),
    ("Sauvegarder régulièrement", "L'agent peut supprimer des fichiers. Activez Time Machine (macOS), File History (Windows), ou un équivalent Linux. Testez vos sauvegardes périodiquement."),
    ("Limiter la whitelist d'apps", "Ne mettez dans system.allowed_apps que les applications que l'agent a réellement besoin de lancer. Plus la liste est courte, plus la surface d'attaque est réduite."),
    ("Surveiller les logs", "Consultez régulièrement les logs du dashboard. Si vous voyez des actions inattendues, mettez l'agent en pause et investiguez."),
    ("Tester en dry-run", "Pour les tâches sensibles (organisation de fichiers, suppressions), utilisez le paramètre dry_run quand il existe, afin de voir ce qui serait fait sans le faire réellement."),
    ("Mettre à jour régulièrement", "Les dépendances Python et npm doivent être mises à jour périodiquement pour profiter des correctifs de sécurité. Exécutez pip-audit et bun audit."),
]
for title, desc in practices:
    story.append(Paragraph(f"<b>{title}</b>", style_h3))
    story.append(Paragraph(desc, style_body))

story.append(Paragraph("7.3 Limites à connaître", style_h2))
story.append(Paragraph(
    "Z.AGENT est puissant, mais a des limites qu'il faut garder à l'esprit. "
    "Premièrement, le module VLM peut se tromper dans la localisation des éléments UI, "
    "particulièrement sur des interfaces complexes ou non standard. Si la confiance est "
    "inférieure au seuil (0.7 par défaut), le clic est refusé — augmentez le seuil pour plus "
    "de prudence, diminuez-le pour plus de permissivité. Deuxièmement, l'agent ne sait pas "
    "gérer les captchas ni les authentifications à deux facteurs — il vous faudra pré-authentifier "
    "les sessions dans le profil browser persistant. Troisièmement, certaines applications "
    "ont des protections anti-automation (DRM, détection de PyAutoGUI) qui peuvent faire échouer "
    "le contrôle écran.",
    style_body
))

story.append(PageBreak())

# ============ CHAPTER 8: EXAMPLES ============
story.append(Paragraph("8. Exemples d'utilisation", style_h1))

story.append(Paragraph("8.1 Organiser le dossier Téléchargements", style_h2))
story.append(Paragraph(
    "Un des cas d'usage les plus simples et les plus utiles. Envoyez à l'agent :",
    style_body
))
story.append(Paragraph(
    '"Tri mon dossier Téléchargements par type de fichier"',
    style_code
))
story.append(Paragraph(
    "L'agent va : (1) lister le contenu du dossier ~/Downloads, (2) créer des sous-dossiers "
    "par catégorie (Images, Documents, Archives, Code, Vidéos, Audio), (3) déplacer chaque "
    "fichier dans le bon sous-dossier, (4) vous envoyer un résumé du nombre de fichiers déplacés "
    "par catégorie. Les fichiers sans extension reconnue restent à la racine.",
    style_body
))

story.append(Paragraph("8.2 Lire et résumer les emails non lus", style_h2))
story.append(Paragraph(
    "Quand vous êtes en déplacement, demandez à l'agent :",
    style_body
))
story.append(Paragraph(
    '"Lis mes 5 derniers emails non lus et fais-moi un résumé pour chacun"',
    style_code
))
story.append(Paragraph(
    "L'agent va : (1) se connecter en IMAP à votre boîte, (2) récupérer les 5 derniers "
    "messages non lus, (3) pour chaque email extraire l'expéditeur, le sujet, et un résumé "
    "du corps via GLM-4.6, (4) vous envoyer le tout via Telegram. Vous pouvez ensuite demander "
    "à l'agent de répondre à l'un d'entre eux en utilisant email.reply.",
    style_body
))

story.append(Paragraph("8.3 Surveiller un site web", style_h2))
story.append(Paragraph(
    "Pour vérifier régulièrement un prix ou une disponibilité :",
    style_body
))
story.append(Paragraph(
    '"Ouvre https://example.com/product dans le navigateur, capture l\'écran, '
    'et dis-moi quel est le prix affiché"',
    style_code
))
story.append(Paragraph(
    "L'agent va : (1) lancer le navigateur Chromium via Playwright, (2) naviguer vers l'URL, "
    "(3) attendre le chargement de la page, (4) prendre une capture d'écran, (5) envoyer "
    "la capture à GLM-4V avec un prompt demandant le prix, (6) vous renvoyer la réponse. "
    "Vous pouvez combiner cette tâche avec le scheduler pour la répéter toutes les heures.",
    style_body
))

story.append(Paragraph("8.4 Préparer une réunion", style_h2))
story.append(Paragraph(
    "Avant une réunion, demandez :",
    style_body
))
story.append(Paragraph(
    '"Quand est ma prochaine réunion ? Ouvre les documents qui y sont liés '
    'et envoie-moi un résumé de l\'agenda."',
    style_code
))
story.append(Paragraph(
    "L'agent va : (1) consulter le calendrier ICS pour le prochain événement, (2) extraire "
    "le titre, la date, l'heure, le lieu, et la description, (3) chercher dans vos documents "
    "ceux dont le nom correspond au titre de la réunion, (4) ouvrir ces documents dans leur "
    "application par défaut, (5) vous envoyer un résumé sur Telegram avec l'agenda et les liens "
    "vers les documents ouverts.",
    style_body
))

story.append(Paragraph("8.5 Nettoyage système", style_h2))
story.append(Paragraph(
    "Pour libérer de la mémoire ou tuer un processus récalcitrant :",
    style_body
))
story.append(Paragraph(
    '"Liste les 20 processus qui consomment le plus de mémoire. '
    'Si Chrome utilise plus de 4 Go, ferme-le."',
    style_code
))
story.append(Paragraph(
    "L'agent va : (1) lister les processus via psutil, (2) identifier les plus gourmands, "
    "(3) vérifier si Chrome dépasse 4 Go, (4) si oui, tuer tous les processus Chrome, "
    "(5) vous confirmer l'action effectuée. Cette tâche illustre la capacité de l'agent "
    "à faire des décisions conditionnelles basées sur l'état du système.",
    style_body
))

story.append(PageBreak())

# ============ CHAPTER 9: TROUBLESHOOTING ============
story.append(Paragraph("9. Dépannage et FAQ", style_h1))

story.append(Paragraph("9.1 L'agent ne répond pas sur Telegram", style_h2))
story.append(Paragraph(
    "Vérifiez d'abord que le token Telegram est correctement défini dans le fichier .env "
    "et que l'agent tourne (vous devriez voir « Telegram interface started » dans les logs). "
    "Vérifiez ensuite que votre identifiant utilisateur est bien dans allowed_user_ids. "
    "Si le bot est en ligne mais ne répond pas, regardez les logs côté agent — une erreur "
    "de connexion à l'API z.ai est souvent la cause (clé expirée, quota dépassé, "
    "problème réseau).",
    style_body
))

story.append(Paragraph("9.2 L'agent clique au mauvais endroit", style_h2))
story.append(Paragraph(
    "Le module VLM peut parfois mal localiser un élément UI. Augmentez le seuil de confiance "
    "screen.click_confidence à 0.8 ou 0.9 pour exiger une meilleure certitude. "
    "Réduisez aussi screen.scale à 0.5 — une résolution plus basse accélère le traitement VLM "
    "mais peut réduire la précision. À l'inverse, monter scale à 1.0 donne plus de détails "
    "au modèle. Pour les éléments critiques, utilisez screen.find_and_click qui retente "
    "automatiquement la recherche si le premier essai échoue.",
    style_body
))

story.append(Paragraph("9.3 L'envoi d'email échoue", style_h2))
story.append(Paragraph(
    "Le cause la plus fréquente est l'utilisation du mot de passe principal au lieu d'un "
    "mot de passe d'application. Pour Gmail, activez la 2FA puis générez un app password "
    "sur myaccount.google.com/apppasswords. Vérifiez aussi que imap_ssl et smtp_tls sont "
    "à true dans la configuration. Pour Outlook, utilisez imap-mail.outlook.com:993 "
    "et smtp-mail.outlook.com:587. Pour Yahoo, utilisez imap.mail.yahoo.com:993 "
    "et smtp.mail.yahoo.com:587 avec un app password.",
    style_body
))

story.append(Paragraph("9.4 Le navigateur Playwright ne se lance pas", style_h2))
story.append(Paragraph(
    "Après installation des dépendances Python, vous devez aussi installer les navigateurs "
    "Playwright avec la commande <font name=\"MonoFont\">playwright install chromium</font>. "
    "Sans cette étape, le module browser_control échouera au premier appel. Sur Linux, "
    "vous aurez peut-être besoin de <font name=\"MonoFont\">playwright install-deps</font> "
    "pour installer les bibliothèques système (libnss3, libatk-bridge2.0-0, etc.).",
    style_body
))

story.append(Paragraph("9.5 Le dashboard ne se connecte pas à l'API", style_h2))
story.append(Paragraph(
    "Vérifiez que l'API FastAPI tourne sur le port 8765 (vous devriez voir « Uvicorn running "
    "on http://127.0.0.1:8765 » dans les logs). Si l'API est sur une autre machine, "
    "définissez NEXT_PUBLIC_AGENT_API. Vérifiez les règles de firewall — le port 8765 doit "
    "être ouvert. Ouvrez la console du navigateur pour voir les erreurs WebSocket "
    "ou de fetch. Les erreurs CORS se résolvent en ajoutant votre origine dans "
    "dashboard.cors_origins du fichier de configuration.",
    style_body
))

story.append(Paragraph("9.6 L'agent consomme beaucoup de tokens IA", style_h2))
story.append(Paragraph(
    "Chaque tâche consomme des tokens pour la planification (GLM-4.6) et éventuellement "
    "la perception (GLM-4V). Pour réduire la consommation : utilisez les commandes slash "
    "pour les tâches simples (elles contournent le planner), réduisez max_actions_per_task "
    "pour limiter les plans longs, et diminuez screen.scale pour réduire la taille des "
    "images envoyées au VLM. Vous pouvez aussi désactiver la perception VLM si vos tâches "
    "n'en ont pas besoin (utilisez plutôt des coordonnées fixes pour les clics répétitifs).",
    style_body
))

story.append(PageBreak())

# ============ APPENDIX A: ACTIONS REFERENCE ============
story.append(Paragraph("Annexe A — Référence des actions", style_h1))
story.append(Paragraph(
    "Liste complète des actions disponibles pour le planner. Chaque action accepte "
    "les paramètres indiqués et retourne un dictionnaire avec au minimum une clé "
    "<font name=\"MonoFont\">success</font> (booléen).",
    style_body
))

actions_by_module = {
    "Screen Control": [
        ("screen.click_element", "description: str, button: str = 'left', clicks: int = 1"),
        ("screen.click_xy", "x: int, y: int, button: str = 'left', clicks: int = 1"),
        ("screen.type_text", "text: str, interval: float = 0.0"),
        ("screen.press_key", "key: str, presses: int = 1"),
        ("screen.hotkey", "keys: List[str]"),
        ("screen.scroll", "direction: str, amount: int = 3, x: int?, y: int?"),
        ("screen.screenshot", "description: str?"),
        ("screen.wait", "seconds: float = 1.0"),
        ("screen.find_and_click", "description: str, max_retries: int = 2"),
        ("screen.drag", "x1, y1, x2, y2: int, duration: float = 0.5"),
    ],
    "File Manager": [
        ("files.list", "path: str?, pattern: str = '*', include_hidden: bool = false"),
        ("files.move", "sources: List[str], destination: str"),
        ("files.copy", "sources: List[str], destination: str"),
        ("files.rename", "path: str, new_name: str"),
        ("files.delete", "path: str, permanent: bool = false"),
        ("files.organize", "path: str?, dry_run: bool = false"),
        ("files.search", "path: str?, pattern: str, content_query: str?"),
        ("files.read", "path: str, max_size: int = 1MB"),
        ("files.write", "path: str, content: str, append: bool = false"),
        ("files.create_dir", "path: str"),
    ],
    "Email": [
        ("email.send", "to: str, subject: str, body: str, cc: str?, bcc: str?, attachments: List[str]?, html: bool"),
        ("email.read_unread", "folder: str = 'INBOX', limit: int = 10, mark_seen: bool = false"),
        ("email.search", "query: str, folder: str = 'INBOX', limit: int = 20"),
        ("email.reply", "message_id: str, body: str, folder: str = 'INBOX'"),
        ("email.mark_read", "message_id: str, folder: str = 'INBOX'"),
        ("email.list_folders", ""),
    ],
    "Calendar": [
        ("calendar.list", "days_ahead: int = 7, include_recurring: bool = true"),
        ("calendar.create", "title: str, start: str, end: str?, description: str?, location: str?"),
        ("calendar.delete", "uid: str"),
        ("calendar.search", "query: str"),
        ("calendar.remind", "event_uid: str, minutes_before: int = 15"),
    ],
    "Browser": [
        ("browser.open", "url: str, wait_until: str = 'domcontentloaded'"),
        ("browser.click", "selector: str, wait: bool = true"),
        ("browser.fill", "selector: str, value: str"),
        ("browser.screenshot", "full_page: bool = false"),
        ("browser.extract", "selector: str = 'body', attribute: str = 'text_content'"),
        ("browser.scroll", "direction: str = 'down', amount: int = 500"),
        ("browser.evaluate", "script: str"),
        ("browser.close", ""),
    ],
    "System": [
        ("system.launch_app", "name: str, args: List[str]?"),
        ("system.kill_app", "name: str"),
        ("system.list_processes", "filter_name: str?, limit: int = 50"),
        ("system.notification", "title: str, message: str"),
        ("system.clipboard_get", ""),
        ("system.clipboard_set", "content: str"),
        ("system.open_path", "path: str"),
        ("system.system_info", ""),
        ("system.run_command", "command: str, cwd: str?, timeout: int = 60"),
    ],
}

for module_name, actions in actions_by_module.items():
    story.append(Paragraph(module_name, style_h2))
    data = [[Paragraph("<b>Action</b>", style_body_left), Paragraph("<b>Paramètres</b>", style_body_left)]]
    for name, params in actions:
        data.append([
            Paragraph(f"<font name='MonoFont'>{name}</font>", style_body_left),
            Paragraph(f"<font name='MonoFont' size='9'>{params or '—'}</font>", style_body_left),
        ])
    t = Table(data, colWidths=[5 * cm, 11 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "HeadFont"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, COLOR_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, COLOR_BG_SOFT]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.3 * cm))

# Build
doc.build(story)
print(f"\n✅ PDF generated: {OUTPUT_PDF}")
print(f"   Size: {OUTPUT_PDF.stat().st_size / 1024:.1f} KB")
