"""Collector: Twitter/X (通过 nitter.net 爬取,免 API)"""
from __future__ import annotations

import re
import time
import requests
from datetime import datetime, timezone
from typing import Optional
from src.models import HotItem


SOURCE_LABEL = "Twitter / X"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}


def _try_instance(instances: list[str], path: str) -> Optional[str]:
    """尝试多个 nitter 实例,返回第一个成功的 HTML"""
    for base in instances:
        url = f"{base.rstrip('/')}{path}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                return r.text
        except Exception:
            continue
    return None


def _parse_nitter_tweets(html: str, account: str) -> list[dict]:
    """从 nitter HTML 中提取推文"""
    items = []
    # 查找推文卡片
    tweet_blocks = re.findall(
        r'<div class="timeline-item[^"]*".*?>(.*?)</div>\s*</div>\s*</div>',
        html, re.DOTALL
    )
    if not tweet_blocks:
        # 备用: 按更宽泛的模式匹配
        tweet_blocks = re.findall(
            r'class="tweet-content[^"]*"[^>]*>(.*?)</div>',
            html, re.DOTALL
        )
        for content in tweet_blocks[:10]:
            text = re.sub(r'<[^>]+>', '', content).strip()[:300]
            if text:
                items.append({
                    "text": text,
                    "url": f"https://x.com/{account}",
                    "time": None,
                })
        return items

    for block in tweet_blocks[:15]:
        # 提取文本
        content_match = re.search(r'class="tweet-content[^"]*"[^>]*>(.*?)</div>', block, re.DOTALL)
        if not content_match:
            continue
        text = re.sub(r'<[^>]+>', '', content_match.group(1)).strip()

        # 提取时间
        time_match = re.search(r'datetime="([^"]+)"', block)
        dt = None
        if time_match:
            try:
                dt = datetime.fromisoformat(time_match.group(1).replace("Z", "+00:00"))
            except ValueError:
                pass

        # 提取推文链接
        link_match = re.search(r'href="(/[^"]+/status/\d+)"', block)
        tweet_url = f"https://x.com{link_match.group(1)}" if link_match else f"https://x.com/{account}"

        # 提取交互数据
        stats = {}
        for stat in ["reply", "retweet", "like"]:
            m = re.search(rf'class="icon-{stat}[^"]*"[^>]*>.*?<span[^>]*>(\d+)</span>', block, re.DOTALL)
            if m:
                stats[stat] = int(m.group(1))

        items.append({
            "text": text,
            "url": tweet_url,
            "time": dt,
            "stats": stats,
        })

    return items


def collect(cfg: dict) -> list[HotItem]:
    enabled = cfg.get("sources", {}).get("twitter", {}).get("enabled", True)
    if not enabled:
        return []

    tw_cfg = cfg["sources"]["twitter"]
    accounts = tw_cfg.get("accounts", [])
    instances = tw_cfg.get("nitter_instances", ["https://nitter.net"])
    max_items = tw_cfg.get("max_items", 30)

    items: list[HotItem] = []
    for account in accounts:
        if len(items) >= max_items:
            break
        try:
            html = _try_instance(instances, f"/{account}")
            if not html:
                continue
            tweets = _parse_nitter_tweets(html, account)
            for tw in tweets:
                text = tw.get("text", "")
                if not text or len(text) < 10:
                    continue
                stats = tw.get("stats", {})
                score = stats.get("like", 0) + stats.get("retweet", 0) * 2
                score = min(score, 100)

                # 检查是否跟 AI 相关
                tags = []
                text_lower = text.lower()
                if any(kw in text_lower for kw in ["gpt", "llm", "claude", "gemini", "llama"]):
                    tags.append("LLM")
                if "agent" in text_lower:
                    tags.append("Agent")
                if "open source" in text_lower:
                    tags.append("Open Source")

                items.append(HotItem(
                    title=text[:120] + ("..." if len(text) > 120 else ""),
                    url=tw.get("url", f"https://x.com/{account}"),
                    source="twitter",
                    source_label=SOURCE_LABEL,
                    summary=text[:300],
                    score=score,
                    author=account,
                    published_at=tw.get("time"),
                    tags=tags,
                    extra={"account": account, "stats": stats},
                ))
            time.sleep(1)  # 礼貌延时
        except Exception:
            continue

    items.sort(key=lambda x: x.score, reverse=True)
    return items[:max_items]
