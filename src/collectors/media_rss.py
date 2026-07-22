"""Collector: 英文技术媒体 RSS"""
from __future__ import annotations

import feedparser
import requests
from datetime import datetime, timezone
from src.models import HotItem


SOURCE_LABEL = "Tech Media"


def collect(cfg: dict) -> list[HotItem]:
    enabled = cfg.get("sources", {}).get("media_rss", {}).get("enabled", True)
    if not enabled:
        return []

    media_cfg = cfg["sources"]["media_rss"]
    feeds = media_cfg.get("feeds", [])
    max_items = media_cfg.get("max_items", 15)

    items: list[HotItem] = []
    seen_urls: set[str] = set()

    for feed_info in feeds:
        if len(items) >= max_items * 2:
            break
        name = feed_info.get("name", "Unknown")
        url = feed_info.get("url", "")
        if not url:
            continue
        try:
            r = requests.get(url, timeout=15,
                             headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            feed = feedparser.parse(r.content)
        except Exception:
            continue

        for entry in feed.entries[:10]:
            link = entry.get("link", "")
            if not link or link in seen_urls:
                continue
            seen_urls.add(link)

            title = entry.get("title", "").strip()
            if not title:
                continue

            summary = (entry.get("summary", "") or entry.get("description", ""))[:300]
            summary = summary.strip()

            # 发布时间
            published = None
            for field in ["published_parsed", "updated_parsed"]:
                tp = entry.get(field)
                if tp:
                    try:
                        from time import mktime
                        published = datetime.fromtimestamp(mktime(tp), tz=timezone.utc)
                    except Exception:
                        pass
                    break

            # 热度: RSS 没有评分,用关键词判断
            text_lower = (title + " " + summary).lower()
            score = 30
            if any(kw in text_lower for kw in ["gpt", "claude", "llama", "gemini", "sora"]):
                score += 20
            if any(kw in text_lower for kw in ["agent", "framework", "release", "launch"]):
                score += 10

            items.append(HotItem(
                title=title,
                url=link,
                source="media_rss",
                source_label=SOURCE_LABEL,
                summary=summary,
                score=min(score, 100),
                author=entry.get("author", name),
                published_at=published,
                tags=[],
                extra={"source_name": name},
            ))

    items.sort(key=lambda x: x.score, reverse=True)
    return items[:max_items]
