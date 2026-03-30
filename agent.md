# Agent Context: CF-StealthSub

## Project Purpose
CF-StealthSub is a self-hosted tool enabling users to securely test Cloudflare IPs locally and upload them to a disguised backend to auto-generate Clash/VLESS proxy subscriptions. The primary mechanism replaces fragile "browser side pings" with robust native `cfst` client scans + CSV uploads.

## Tech Stack
- **Backend Model**: FastAPI + Uvicorn
- **Package Manager**: `uv`
- **Frontend**: Vanilla Javascript (ES6 modules), Raw CSS (no React/Vue/Tailwind)
- **Deployment**: PM2 (No Docker or Systemd necessary)

## Core Components
- `/server/routes/api.py`: Core endpoint `POST /results` accepting a multipart `UploadFile` (result.csv).
- `/server/utils/subscription.py`: Generates the resulting YAML config. Note: `x-door-key` header is pulled dynamically from `config.yaml` (`config.proxy.door_key`) to pass CDN verification.
- `/public/`: Contains the stealth front-end. The `index.html` initiates a faux-blog view. The UI unlocks via triple-clicking the settings/gear icon and providing a TOTP code.
- `/data/subscriptions/`: (or whatever `config.yaml` targets globally like `/mnt/gdrive/`): Used for storing the ephemeral Clash subscription YAML blobs before fetching.

## Security Constraints & Rules
1. **Never Hardcode Secrets**: Any token, API key, Header secret (like WAF bypass), or UUID MUST exist only in `config.yaml`.
2. **Git Ignore**: Never let `data/`, `result.csv`, `.venv`, or `config.yaml` to be tracked by Git.
3. **No Heavy Frameworks**: Keep the Frontend architecture raw (`app.js`, `ui.js`, `upload.js`). Do not introduce external libraries or NPM build steps for the frontend.
