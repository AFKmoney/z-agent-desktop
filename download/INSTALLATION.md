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
