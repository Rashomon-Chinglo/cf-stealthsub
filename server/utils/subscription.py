"""Clash YAML subscription generator — proxies-only format."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from server.config import AppConfig


def generate_clash_yaml(
    ips: list[dict],
    config: AppConfig,
    expires_at: int | None = None,
) -> str:
    """Generate a Clash-compatible YAML with VLESS proxy list.

    Args:
        ips: List of dicts with keys: ip, avg_latency, loss_rate, speed_kbps, score
        config: Application config for proxy settings
        expires_at: Optional expiry timestamp for the header comment

    Returns:
        Complete YAML string with comment header + proxies list
    """
    proxies = _build_proxies(ips, config)

    # Generate informational comment header
    cst = timezone(timedelta(hours=8))
    now_str = datetime.now(cst).strftime("%Y-%m-%d %H:%M CST")

    header_lines = [
        "# CF IP 优选订阅",
        f"# 生成时间: {now_str}",
    ]
    if expires_at:
        exp_str = datetime.fromtimestamp(expires_at, cst).strftime("%Y-%m-%d %H:%M CST")
        header_lines.append(f"# 有效期至: {exp_str}")
    header_lines.extend([
        f"# 节点数量: {len(proxies)}",
        "# 使用说明: 将此订阅导入 Clash，节点将出现在代理列表中",
        "",
    ])
    header = "\n".join(header_lines) + "\n"

    body_dict = {
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "🚀 优选 Fallback",
                "type": "fallback",
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "proxies": [p["name"] for p in proxies],
            }
        ],
    }

    body = yaml.dump(
        body_dict,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )

    return header + body


def _build_proxies(ips: list[dict], config: AppConfig) -> list[dict]:
    """Build Clash proxy node list from IP results."""
    proxies = []
    for i, item in enumerate(ips):
        colo = item.get("colo", "").strip()
        if colo:
            name = f"CF-{i + 1:02d}-{colo}"
        else:
            name = f"CF-{i + 1:02d}"
            
        headers = {"Host": config.proxy.domain}
        if config.proxy.door_key:
            headers["x-door-key"] = config.proxy.door_key

        proxy = {
            "name": name,
            "type": config.proxy.protocol,
            "server": item["ip"],
            "port": config.proxy.port,
            "uuid": config.proxy.uuid,
            "network": config.proxy.network,
            "tls": config.proxy.tls,
            "udp": True,
            "servername": config.proxy.domain,
            "ws-opts": {
                "path": config.proxy.path,
                "headers": headers,
            },
        }
        proxies.append(proxy)
    return proxies
