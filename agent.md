# CF-StealthSub Agent Notes

## What This Project Is

自托管 Cloudflare IP 优选与订阅生成工具。

用户流程：

1. 访问伪装文章页
2. 三击齿轮图标进入隐藏终端
3. 输入 TOTP 验证码
4. 下载 `CloudflareSpeedTest`
5. 在本地测速得到 `result.csv`
6. 上传 CSV
7. 服务端生成完整 Clash YAML 并给出订阅链接

## Stack

- Backend: FastAPI + Uvicorn
- Package manager: `uv`
- Frontend: Vanilla JS modules + raw CSS
- Runtime state: in-memory session / rate-limit + file-based subscription storage

## Important Files

- `server/main.py`: app entry
- `server/config.py`: config models and loader
- `server/routes/auth.py`: TOTP login, secure cookie session
- `server/routes/api.py`: CSV upload, parsing, YAML generation
- `server/routes/sub.py`: subscription download
- `server/utils/subscription.py`: complete Clash config generator
- `server/utils/store.py`: YAML persistence and subscription index
- `public/index.html`: disguised article + hidden terminal
- `public/js/auth.js`: auth flow
- `public/js/upload.js`: upload/result rendering
- `public/js/ui.js`: terminal output helpers

## Rules For AI Changes

- Do not introduce frontend frameworks, bundlers, or npm build tooling.
- Do not hardcode UUIDs, secrets, `door_key`, or deployment domains.
- Preserve the disguised-entry + terminal-style interaction model.
- Keep the output a complete Clash YAML, not a partial `proxies` snippet.
- Prefer small, local, readable changes over abstraction-heavy rewrites.

## Security Assumptions

- This project is designed for self-use or a very small trusted group.
- `server.trusted_proxies` controls whether proxy headers are trusted.
- Auth now uses HttpOnly cookie sessions; avoid reintroducing token storage in browser JS.
- Upload size and content-type restrictions are intentional; keep them unless explicitly changed.

## Human Deployment Reference

For human-facing setup and deployment instructions, read `README.md`.

Short version:

```bash
uv sync
cp config.example.yaml config.yaml
uv run python scripts/setup_totp.py
uv run uvicorn server.main:app --host 127.0.0.1 --port 3001
```

Production usually means:

- HTTPS reverse proxy in front
- correct `server.base_url`
- correct `server.trusted_proxies`
- `auth.cookie_secure: true`

## Validation

Use:

```bash
uv run ty check
uv run ruff check
```
