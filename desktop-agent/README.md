# Z.AI Desktop Agent

Un agent de bureau autonome propulsé par les modèles GLM de z.ai, contrôlable à distance via Telegram.

## Aperçu

`z.ai coding plan` → **agent de bureau 100% autonome** qui pilote votre ordinateur quand vous êtes absent.

### Capacités

| Module | Description |
|--------|-------------|
| 🖱️ **Screen Control** | Curseur, clavier, fenêtres — pilotage générique d'applications via PyAutoGUI + VLM |
| 👁️ **Perception VLM** | GLM-4V analyse votre écran en temps réel pour comprendre l'UI |
| 📁 **Files** | Organiser, déplacer, renommer, chercher, lire/écrire des fichiers |
| 📧 **Emails** | IMAP/SMTP — lire, envoyer, répondre, trier (Gmail, Outlook, etc.) |
| 📅 **Calendar** | ICS — lister, créer, supprimer des événements, rappels |
| 🌐 **Browser** | Playwright — ouvrir, cliquer, remplir, extraire du contenu |
| ⚙️ **System** | Lancer apps, gérer processus, notifications, presse-papier |

### Architecture

```
┌─────────────────────────────────────────────┐
│              Telegram / Dashboard            │  ← Vous êtes ici
└────────────────┬────────────────────────────┘
                 │ tâches (langage naturel)
                 ▼
┌─────────────────────────────────────────────┐
│                  AGENT LOOP                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Planner  │→ │ Executor │→ │ Memory   │  │
│  │ GLM-4.6  │  │          │  │          │  │
│  └──────────┘  └────┬─────┘  └──────────┘  │
│                     │                        │
│       ┌─────────────┼─────────────┐         │
│       ▼             ▼             ▼         │
│  ┌────────┐   ┌──────────┐  ┌────────┐    │
│  │ Screen │   │  Files   │  │ Email  │    │
│  │ + VLM  │   │          │  │        │    │
│  └────────┘   └──────────┘  └────────┘    │
│  ┌────────┐   ┌──────────┐  ┌────────┐    │
│  │Calendar│   │ Browser  │  │ System │    │
│  └────────┘   └──────────┘  └────────┘    │
└─────────────────────────────────────────────┘
```

## Installation

### 1. Prérequis

```bash
Python 3.10+
```

### 2. Clone et dépendances

```bash
cd desktop-agent
pip install -r requirements.txt
playwright install chromium
```

### 3. Configuration

Créez un fichier `.env` (ou exportez les variables) :

```bash
export ZAI_API_KEY="votre-clé-z.ai"           # https://z.ai/
export TELEGRAM_BOT_TOKEN="votre-token-bot"    # @BotFather
export EMAIL_USER="vous@gmail.com"
export EMAIL_APP_PASSWORD="votre-app-password" # https://myaccount.google.com/apppasswords
```

Éditez `config/config.yaml` pour personnaliser les dossiers surveillés, règles d'organisation, etc.

### 4. Vérification

```bash
python main.py --check
```

## Utilisation

### Mode serveur (Telegram + Dashboard)

```bash
python main.py
```

L'agent écoute alors sur :
- **Telegram** : envoyez vos tâches en message
- **Web API** : `http://127.0.0.1:8765` (pour le dashboard Next.js)

### Mode CLI interactif

```bash
python main.py --cli
```

### Tâche unique

```bash
python main.py --task "Organise mon dossier Téléchargements"
```

## Commandes Telegram

| Commande | Action |
|----------|--------|
| `/start` | Vérifier le statut |
| `/status` | État détaillé de l'agent |
| `/help` | Aide complète |
| `/screenshot` | Capture d'écran instantanée |
| `/pause` `/resume` | Contrôler l'agent |
| `/files organize` | Trier le dossier Téléchargements |
| `/email unread` | Lire les emails non lus |
| `/calendar list` | Prochains événements |
| `/system info` | Infos système |
| `/browser open <url>` | Ouvrir un site |

**Mode libre** : écrivez simplement votre demande en langage naturel.

## Dashboard Web

Le dashboard Next.js fournit une interface visuelle pour :
- Voir l'état de l'agent en temps réel
- Suivre les tâches en cours et l'historique
- Consulter les logs live (WebSocket)
- Visualiser les captures d'écran
- Soumettre des tâches directement

Voir `dashboard/README.md` pour l'installation.

## Sécurité

- **Plein contrôle** : l'agent peut exécuter toutes les actions sans confirmation (configurable)
- **Chemins protégés** : `~/.ssh`, `~/.aws`, fichiers système — jamais touchés
- **Suppressions sécurisées** : corbeille au lieu de suppression permanente
- **Limite de taille fichier** : 100 Mo par défaut
- **Whitelist apps** : lancement d'apps restreint à une liste

⚠️ **Avertissement** : le mode "plein contrôle" est puissant. Assurez-vous de comprendre les risques avant de l'activer en production.

## Modèles Z.AI utilisés

- **GLM-4.6** : planification et raisonnement complexe
- **GLM-4V** : perception visuelle de l'écran
- **GLM-4.5** : exécution rapide d'actions simples
- **GLM-5.1 / 5.2** : lorsque disponibles (décommenter dans `config.yaml`)

## Licence

MIT
