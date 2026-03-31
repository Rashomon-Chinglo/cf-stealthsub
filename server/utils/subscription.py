"""Clash YAML subscription generator."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, TypedDict

import yaml

if TYPE_CHECKING:
    from server.config import AppConfig
    from server.schemas import ParsedIPResult


ProxyHeaders = TypedDict(
    "ProxyHeaders",
    {
        "Host": str,
        "x-door-key": str,
    },
    total=False,
)


WSOptions = TypedDict(
    "WSOptions",
    {
        "path": str,
        "headers": ProxyHeaders,
    },
)

ClashProxy = TypedDict(
    "ClashProxy",
    {
        "name": str,
        "type": str,
        "server": str,
        "port": int,
        "uuid": str,
        "network": str,
        "tls": bool,
        "udp": bool,
        "servername": str,
        "ws-opts": WSOptions,
    },
)


class NoAliasSafeDumper(yaml.SafeDumper):
    """YAML dumper that expands repeated lists instead of anchors."""

    def ignore_aliases(self, data: object) -> bool:
        return True


def generate_clash_yaml(
    ips: Sequence[ParsedIPResult],
    config: AppConfig,
    expires_at: int | None = None,
) -> str:
    """Generate a complete Clash-compatible YAML profile.

    Args:
        ips: List of dicts with keys: ip, avg_latency, loss_rate, speed_kbps, score
        config: Application config for proxy settings
        expires_at: Optional expiry timestamp for the header comment

    Returns:
        Complete YAML string with comment header + Clash profile
    """
    proxies = build_proxies(ips, config)
    proxy_names = [proxy["name"] for proxy in proxies]

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
        "# 策略组: 手动选择、自动测速、总入口选择",
        "# 使用说明: 将此配置作为完整 Clash 配置文件直接导入",
        "",
    ])
    header = "\n".join(header_lines) + "\n"

    body_dict = {
        "port": 7890,
        "socks-port": 7891,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "info",
        "ipv6": False,
        "unified-delay": True,
        "tcp-concurrent": True,
        "find-process-mode": "strict",
        "dns": {
            "enable": True,
            "ipv6": False,
            "listen": "0.0.0.0:1053",
            "enhanced-mode": "fake-ip",
            "fake-ip-range": "198.18.0.1/16",
            "default-nameserver": [
                "223.5.5.5",
                "119.29.29.29",
                "1.1.1.1",
            ],
            "nameserver": [
                "https://dns.alidns.com/dns-query",
                "https://doh.pub/dns-query",
                "https://cloudflare-dns.com/dns-query",
            ],
        },
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "🚀 节点选择",
                "type": "select",
                "proxies": [
                    "⚡ 自动测速",
                    "🎯 手动选择",
                    "DIRECT",
                ],
            },
            {
                "name": "🎯 手动选择",
                "type": "select",
                "proxies": proxy_names,
            },
            {
                "name": "⚡ 自动测速",
                "type": "url-test",
                "url": "https://www.gstatic.com/generate_204",
                "interval": 300,
                "tolerance": 50,
                "proxies": proxy_names,
            },
        ],
        "rules": [
            "GEOIP,CN,DIRECT",
            "MATCH,🚀 节点选择",
        ],
    }

    body = yaml.dump(
        body_dict,
        Dumper=NoAliasSafeDumper,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )

    return header + body


def build_proxies(
    ips: Sequence[ParsedIPResult],
    config: AppConfig,
) -> list[ClashProxy]:
    """Build Clash proxy node list from IP results."""
    proxies: list[ClashProxy] = []
    for i, item in enumerate(ips):
        colo = item.get("colo", "").strip()
        if colo:
            name = f"CF-{i + 1:02d}-{colo}"
        else:
            name = f"CF-{i + 1:02d}"

        headers = {"Host": config.proxy.domain}
        if config.proxy.door_key:
            headers["x-door-key"] = config.proxy.door_key

        proxy: ClashProxy = {
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
