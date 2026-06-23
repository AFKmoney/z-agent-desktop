#!/bin/bash
# Package Z.AGENT into downloadable artifacts.
set -e

PROJECT=/home/z/my-project
DL=$PROJECT/download
mkdir -p "$DL"

echo "==> Cleaning previous packages"
rm -rf "$DL/z-agent-desktop-agent" "$DL/z-agent-dashboard" "$DL/INSTALLATION.md"
rm -f "$DL/z-agent-desktop-agent.zip" "$DL/z-agent-dashboard.zip"

echo "==> Packaging desktop-agent Python code"
# Copy without venv, data folders, caches, __pycache__
mkdir -p "$DL/z-agent-desktop-agent"
# Explicit list of dirs/files to copy (avoid venv, .git, etc.)
for item in core modules interfaces utils config main.py requirements.txt README.md .env.example start.sh start.bat; do
    if [ -e "$PROJECT/desktop-agent/$item" ]; then
        cp -r "$PROJECT/desktop-agent/$item" "$DL/z-agent-desktop-agent/"
    fi
done
# Clean any pycache that snuck in
find "$DL/z-agent-desktop-agent" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$DL/z-agent-desktop-agent" -name "*.pyc" -delete 2>/dev/null || true
# Remove any data folder
rm -rf "$DL/z-agent-desktop-agent/data" 2>/dev/null || true

# Add .env.example
cat > "$DL/z-agent-desktop-agent/.env.example" << 'EOF'
# Z.AGENT - Environment variables
# Copy this file to .env and fill in your values

# Required: get at https://z.ai/
ZAI_API_KEY=

# Required for Telegram control: get from @BotFather
TELEGRAM_BOT_TOKEN=

# Required for email module: use an app password, NOT your real password
EMAIL_USER=
EMAIL_APP_PASSWORD=
EOF

# Add run scripts
cat > "$DL/z-agent-desktop-agent/start.sh" << 'EOF'
#!/bin/bash
# Z.AGENT quick start script
set -e
cd "$(dirname "$0")"

if [ ! -d venv ]; then
    echo "First run: creating virtualenv..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt -q
playwright install chromium 2>/dev/null || true

if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copy .env.example to .env and fill in your keys."
    echo "   Read the documentation for details."
    exit 1
fi

python main.py "$@"
EOF
chmod +x "$DL/z-agent-desktop-agent/start.sh"

cat > "$DL/z-agent-desktop-agent/start.bat" << 'EOF'
@echo off
REM Z.AGENT quick start script for Windows
cd /d "%~dp0"

if not exist venv (
    echo First run: creating virtualenv...
    python -m venv venv
)

call venv\Scripts\activate
pip install -r requirements.txt -q
playwright install chromium

if not exist .env (
    echo WARNING: .env file not found. Copy .env.example to .env and fill in your keys.
    exit /b 1
)

python main.py %*
EOF

# Zip the desktop-agent
cd "$DL"
zip -qr z-agent-desktop-agent.zip z-agent-desktop-agent
rm -rf z-agent-desktop-agent
echo "   Created: z-agent-desktop-agent.zip"

echo "==> Packaging dashboard Next.js code"
mkdir -p "$DL/z-agent-dashboard"
# Copy only the source, not node_modules or .next
cp -r "$PROJECT/src" "$DL/z-agent-dashboard/src"
cp "$PROJECT/package.json" "$DL/z-agent-dashboard/"
cp "$PROJECT/tsconfig.json" "$DL/z-agent-dashboard/"
cp "$PROJECT/tailwind.config.ts" "$DL/z-agent-dashboard/"
cp "$PROJECT/postcss.config.mjs" "$DL/z-agent-dashboard/"
cp "$PROJECT/next.config.ts" "$DL/z-agent-dashboard/"
cp "$PROJECT/components.json" "$DL/z-agent-dashboard/"
cp "$PROJECT/eslint.config.mjs" "$DL/z-agent-dashboard/"

# Dashboard README
cat > "$DL/z-agent-dashboard/README.md" << 'EOF'
# Z.AGENT Dashboard

Interface web Next.js pour surveiller et contrôler l'agent Z.AGENT.

## Installation

```bash
cd z-agent-dashboard
bun install   # ou: npm install
bun run dev   # ou: npm run dev
```

Le dashboard se lance sur http://localhost:3000 et se connecte à l'API agent sur http://localhost:8765.

## Configuration

Si votre API agent est sur une autre machine, définissez :

```bash
export NEXT_PUBLIC_AGENT_API=http://192.168.1.10:8765
```

## Fonctionnalités

- Statut de l'agent en temps réel (WebSocket)
- Soumission de tâches en langage naturel
- Historique des tâches avec plans détaillés
- Logs en streaming
- Galerie de captures d'écran
- Contrôle pause / reprendre / stop
EOF

# Zip the dashboard
cd "$DL"
zip -qr z-agent-dashboard.zip z-agent-dashboard
rm -rf z-agent-dashboard
echo "   Created: z-agent-dashboard.zip"

echo "==> Creating master installation README"
cat > "$DL/INSTALLATION.md" << 'EOF'
# Z.AGENT — Installation complète

Ce dossier contient :

| Fichier | Description |
|---------|-------------|
| `Z-AGENT-Documentation.pdf` | Documentation complète (22 pages) — à lire en premier |
| `z-agent-desktop-agent.zip` | Code Python de l'agent (backend) |
| `z-agent-dashboard.zip` | Dashboard Next.js (frontend web) |

## Installation rapide (5 minutes)

### 1. Agent Python

```bash
unzip z-agent-desktop-agent.zip
cd z-agent-desktop-agent

# Configuration
cp .env.example .env
# Éditez .env avec vos clés (ZAI_API_KEY, TELEGRAM_BOT_TOKEN, etc.)

# Installation (le script crée le venv, installe les deps, lance l'agent)
./start.sh

# Ou en manuel :
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python main.py --check      # Vérification
python main.py              # Lancement
```

### 2. Dashboard Web (optionnel)

```bash
unzip z-agent-dashboard.zip
cd z-agent-dashboard
bun install   # ou: npm install
bun run dev
```

Ouvrez http://localhost:3000

### 3. Telegram

1. Parlez à @BotFather sur Telegram
2. Créez un bot avec /newbot
3. Récupérez le token et mettez-le dans .env
4. Récupérez votre user ID via @userinfobot
5. Ajoutez-le dans config/config.yaml (telegram.allowed_user_ids)
6. Démarrez l'agent et parlez à votre bot !

## Obtenir les clés

| Clé | Où l'obtenir |
|-----|--------------|
| `ZAI_API_KEY` | https://z.ai/ → tableau de bord développeur |
| `TELEGRAM_BOT_TOKEN` | @BotFather sur Telegram |
| `EMAIL_USER` | Votre adresse email |
| `EMAIL_APP_PASSWORD` | Gmail: myaccount.google.com/apppasswords (2FA requise) |

## Documentation complète

Tous les détails (architecture, modules, sécurité, exemples, FAQ) sont dans :
**`Z-AGENT-Documentation.pdf`**

## Support

- Vérifiez les logs : `~/.zda-agent/logs/agent.log`
- Mode CLI : `python main.py --cli`
- Vérification config : `python main.py --check`

---

Z.AGENT v1.0.0 — Propulsé par z.ai GLM-4.6 / GLM-4V / GLM-4.5 (et GLM-5.x quand disponible)
EOF

echo ""
echo "==> Final contents of $DL:"
ls -lh "$DL"

echo ""
echo "✅ Packaging complete!"
