"""
企业微信机器人推送 (自动绕过代理)
"""
from __future__ import annotations

import os
import json
import requests
from src.models import HotItem


def _no_proxy_session() -> requests.Session:
    """创建不经过代理的 session（企业微信 API 需要在公司网络直连）"""
    sess = requests.Session()
    sess.trust_env = False  # 忽略 HTTP_PROXY / HTTPS_PROXY 环境变量
    return sess


def push(cfg: dict, items: list[HotItem]):
    """将热点摘要推送到企业微信机器人"""
    webhook_url = cfg.get("wecom", {}).get("webhook_url", "")
    if not webhook_url:
        return

    if not items:
        return

    # 取 Top 10 生成推送内容
    top = items[:10]
    lines = [f"🔥 **AI Engineer 热点日报** ({len(items)} 条)"]
    for i, item in enumerate(top, 1):
        source_icon = {
            "github": "📦",
            "hackernews": "💬",
            "reddit": "👽",
            "twitter": "🐦",
            "arxiv": "📄",
            "media_rss": "📰",
            "cn_social": "🇨🇳",
        }.get(item.source, "🔗")
        score_str = f"⭐{item.score:.0f}" if item.score else ""
        lines.append(f"\n{i}. {source_icon} **[{item.source_label}]** {item.title[:80]}")
        lines.append(f"   {score_str}  {item.url}")

    content = "\n".join(lines)

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": content,
        }
    }

    try:
        sess = _no_proxy_session()
        r = sess.post(webhook_url, json=payload, timeout=15)
        r.raise_for_status()
    except Exception:
        pass


def push_daily_summary(cfg: dict, items: list[HotItem]):
    """推送精简版日报摘要（用于每日定时）"""
    webhook_url = cfg.get("wecom", {}).get("webhook_url", "")
    if not webhook_url:
        return

    if not items:
        return

    top5 = items[:5]
    source_counts = {}
    for item in items:
        source_counts[item.source_label] = source_counts.get(item.source_label, 0) + 1
    source_summary = " | ".join(f"{k} {v}" for k, v in sorted(source_counts.items(), key=lambda x: -x[1]))

    lines = [
        f"📡 **AI Engineer 日报**\n",
        f"共 {len(items)} 条热点 | {source_summary}\n",
    ]
    for i, item in enumerate(top5, 1):
        lines.append(f"{i}. [{item.source_label}] {item.title[:100]}")
        lines.append(f"   {item.url}")

    lines.append(f"\n查看完整页面: https://你的github用户名.github.io/ai-engineer-hotlist/")

    payload = {
        "msgtype": "markdown",
        "markdown": {"content": "\n".join(lines)}
    }

    try:
        sess = _no_proxy_session()
        r = sess.post(webhook_url, json=payload, timeout=15)
        r.raise_for_status()
    except Exception:
        pass
