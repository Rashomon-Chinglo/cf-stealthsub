# CF-StealthSub

CF-StealthSub 是一个自托管的 Cloudflare IP 优选与订阅生成工具。

它解决的是一个很具体的问题：浏览器里做伪测速不稳定、结果失真、可控性差，所以这个项目改成让用户先在本地运行原生 `CloudflareSpeedTest`，拿到 `result.csv` 之后，再上传到服务端生成可直接导入 Clash/Mihomo 的完整 YAML 配置。

整个交互面会伪装成一篇普通技术文章。只有触发隐藏入口并通过 TOTP 验证后，才会进入终端风格界面，下载测速工具、上传 CSV、查看优选 IP 和获取订阅链接。

## 适用场景

- 你自己维护一个或少量亲友共享的 VLESS / WS / TLS 节点
- 你想周期性筛选更优的 Cloudflare IP
- 你希望生成的是完整 Clash 配置，而不是只包含 `proxies` 的残片
- 你不想引入数据库、消息队列、前端构建链路

## 核心能力

- 隐藏入口：默认展示伪装文章，不直接暴露管理界面
- TOTP 验证：通过 Google Authenticator / Authy 等生成的一次性验证码登录
- 原生测速工作流：提供 `CloudflareSpeedTest` 二进制下载链接，由用户在本地执行
- CSV 上传解析：服务端解析 `result.csv`，提取 IP、延迟、丢包、速度、地区码
- 订阅生成：动态生成完整 Clash YAML，内含手动选择组和自动测速组
- 临时订阅：订阅文件按时效缓存，过期后自动清理
- 基础安全控制：受信代理校验、登录限流、上传大小限制、HttpOnly Cookie 会话

## 工作流

1. 用户访问伪装页面
2. 三击页面中的齿轮图标，进入隐藏终端
3. 输入 TOTP 验证码
4. 登录后下载 `CloudflareSpeedTest`
5. 在本地运行测速工具，得到 `result.csv`
6. 把 CSV 拖入网页终端
7. 服务端生成完整 YAML，并返回可下载的订阅链接

## 技术栈

- 后端：FastAPI
- 运行：Uvicorn
- 包管理：`uv`
- 前端：原生 ES Modules + 原生 CSS
- 部署方式：手动部署 / PM2 / 反向代理
- 数据存储：文件 + 进程内索引，无数据库

## 快速开始

### 环境要求

- Python 3.12+
- `uv`
- 可选：Node.js 和 PM2，用于常驻进程管理

### 安装依赖

```bash
git clone <your-repo-url>
cd cf-ip-optimizer
uv sync
```

### 初始化配置

```bash
cp config.example.yaml config.yaml
uv run python scripts/setup_totp.py
```

执行后终端会输出：

- TOTP Secret
- Provisioning URI

把 Secret 填进 `config.yaml` 的 `auth.totp_secret`，或者用 Authenticator 扫描 URI 对应的二维码内容。

## 配置说明

`config.yaml` 的主要字段：

### `server`

- `host`：服务监听地址
- `port`：服务监听端口
- `base_url`：生成订阅链接时使用的外部访问地址
- `trusted_proxies`：只有请求来自这些 IP / CIDR 时，才信任 `CF-Connecting-IP` 和 `X-Forwarded-For`

### `auth`

- `totp_secret`：TOTP 密钥
- `session_duration_hours`：登录会话有效期
- `session_cookie_name`：会话 Cookie 名称
- `cookie_secure`：生产环境 HTTPS 必须为 `true`；仅本地 HTTP 调试时设为 `false`
- `cookie_samesite`：默认 `strict`

### `proxy`

- `protocol`：当前默认 `vless`
- `uuid`：你的 VLESS UUID
- `domain`：SNI / Host 对应域名
- `port`：节点端口，默认 `443`
- `path`：WebSocket 路径
- `network`：默认 `ws`
- `tls`：是否启用 TLS
- `door_key`：可选，自定义请求头值，用于穿透你的 CDN / WAF 校验逻辑

### `subscription`

- `top_n`：从 CSV 中取前多少个 IP 生成节点
- `cache_duration_hours`：订阅缓存多久
- `storage_path`：YAML 文件存放目录
- `max_upload_size_mb`：上传 CSV 的大小限制

## 手动部署

下面是一套最直接的手动部署方式。

### 1. 准备服务器

确保服务器已安装：

- Python 3.12+
- `uv`
- 可选：`pm2`
- 可选：Nginx / Caddy 之类反向代理

### 2. 拉取代码并安装

```bash
git clone <your-repo-url>
cd cf-ip-optimizer
uv sync
cp config.example.yaml config.yaml
```

### 3. 配置 `config.yaml`

至少填这几个值：

- `server.base_url`
- `auth.totp_secret`
- `proxy.uuid`
- `proxy.domain`
- `proxy.path`

如果你的服务前面挂了 Nginx / Cloudflare Tunnel / 其他反代，把对应反代出口 IP 或本机回环地址配置到 `server.trusted_proxies`。

### 4. 本地直接运行

```bash
uv run uvicorn server.main:app --host 127.0.0.1 --port 3001
```

### 5. 用 PM2 常驻

```bash
pm2 start "uv run uvicorn server.main:app --host 127.0.0.1 --port 3001" --name cf-stealthsub
pm2 save
```

### 6. 反向代理

建议外面再挂一层 Nginx 或其他反向代理：

- 对外只开放 80 / 443
- 反代到 `127.0.0.1:3001`
- 打开 HTTPS
- 如使用 Cloudflare，确认真实来源链路和 `trusted_proxies` 配置匹配

## 目录结构

```text
.
├── config.example.yaml        # 配置样例
├── pyproject.toml             # Python 项目定义与开发工具配置
├── README.md                  # 面向人类的项目说明
├── agent.md                   # 面向 AI / 维护代理的项目说明
├── public/                    # 前端静态资源
│   ├── index.html             # 伪装文章 + 隐藏终端入口
│   ├── css/style.css          # 终端与伪装页样式
│   ├── js/app.js              # 首屏最小入口
│   ├── js/auth.js             # 登录与会话恢复逻辑
│   ├── js/upload.js           # CSV 上传与结果展示
│   ├── js/ui.js               # 终端 UI 输出封装
│   └── downloads/             # CloudflareSpeedTest 二进制文件
├── scripts/
│   └── setup_totp.py          # 生成 TOTP Secret
└── server/
    ├── main.py                # FastAPI 入口
    ├── config.py              # 配置模型与加载
    ├── dependencies.py        # 鉴权与真实 IP 提取
    ├── schemas.py             # 共享 Pydantic / TypedDict 模型
    ├── middleware/
    │   ├── rate_limit.py      # 登录限流
    │   └── security.py        # 安全响应头
    ├── routes/
    │   ├── auth.py            # 登录与会话校验
    │   ├── api.py             # CSV 上传与订阅生成
    │   └── sub.py             # 订阅下发
    └── utils/
        ├── session.py         # 会话存储
        ├── store.py           # 订阅文件存储与索引
        ├── subscription.py    # Clash YAML 生成
        └── totp.py            # TOTP 校验
```

## 开发与校验

项目默认带 `dev` 依赖组，执行 `uv sync` 后可直接运行：

```bash
uv run ty check
uv run ruff check
```

如果要做基础语法检查：

```bash
python3 -m compileall server scripts
```

## 当前限制

- 会话和登录限流是进程内内存存储，不适合多实例共享状态
- 订阅模板目前是固定 Clash 风格，不是通用配置工厂
- 前端是纯静态原生实现，没有组件化和构建链路
- 设计目标是小规模、自用、可信人群共享，不是公网多租户 SaaS

## 安全建议

- 生产环境务必启用 HTTPS
- 生产环境务必保持 `auth.cookie_secure: true`
- 不要把 `config.yaml`、生成的订阅文件、测速结果 CSV 提交到仓库
- 如果你的服务不是只跑在本机后面，请认真配置 `server.trusted_proxies`
- `proxy.door_key` 这种敏感值只能放配置，不要写死在代码里

## 免责声明

本项目是一个个人使用的路由优选工具。
请仅在合法、合规和你有权控制的网络环境中使用。
