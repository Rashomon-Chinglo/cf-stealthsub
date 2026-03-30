# CF-StealthSub

CF-StealthSub is a stealthy, self-hosted Cloudflare IP speed testing & VLESS subscription generator. It combines a disguised web interface (hidden behind an innocent-looking blog) with seamless generation of dynamic Clash/VLESS subscription nodes based on local terminal speed test results.

## ✨ Features
- **Stealth Mode UI**: Access to the optimizer requires a secret interaction on an innocuous "blog" page.
- **TOTP Authentication**: Secured by Google Authenticator / Authy time-based tokens.
- **Offline IP Scanner**: Provides direct downloads to CloudflareSpeedTest native binaries (for Windows, Linux AMD/ARM).
- **Automated Clash Subscription**: Upload your `result.csv`, and the system will automatically parse latency and speed data to dynamically generate a Clash-compatible VLESS subscription URL.
- **Advanced Security**: Dynamic Session Tokens prevent API abuse. Fully configurable CDN Door Key to securely bypass target Nginx server blocks.
- **Auto-Expiration**: Subscriptions are cached securely and auto-expire to reduce trace footprints.

## 🚀 Getting Started

### 1. Requirements
- Python 3.12+
- Node.js (for PM2 management, recommended)
- `uv` (Fast Python package installer and resolver)

### 2. Installation
Clone the repository and install dependencies using `uv`:

```bash
git clone https://github.com/yourusername/cf-stealthsub.git
cd cf-stealthsub
uv sync
```

### 3. Configuration
Copy the example config and generate your TOTP secret.

```bash
cp config.example.yaml config.yaml
uv run python scripts/setup_totp.py
```

Follow the instructions in the terminal to copy the `Secret` output into your `config.yaml` under `auth.totp_secret`. You can scan the generated URL to add it to your Authenticator App.

Fill in the rest of `config.yaml`:
- `server.base_url`: Your public-facing domain (for subscription links).
- `proxy.uuid`: Your VLESS UUID.
- `proxy.domain`: Your CDN Sni domain.
- `proxy.door_key`: Custom request header value to bypass WAF / Nginx (optional).

### 4. Running the Server

Using PM2 (Recommended for production):
```bash
pm2 start "uv run uvicorn server.main:app --host 127.0.0.1 --port 3001" --name cf-stealthsub
```

## 🛡️ Architecture & Security
- **No Database Needed**: Built securely without SQLite/PostgreSQL requirements. State is handled efficiently in memory and files.
- **Zero Config Leaks**: `.gitignore` strictly protects `.env`, `.yaml`, and `csv` data files, ensuring no inadvertent git commits of tokens.

---
*Disclaimer: This is a personal project used to optimize routing paths. Do not use for illegal activities.*
