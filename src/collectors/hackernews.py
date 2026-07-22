"""Collector: Hacker News (通过 Algolia Search API,一次请求批量获取)"""
from __future__ import annotations

import requests
from datetime import datetime, timezone
from src.models import HotItem


SOURCE_LABEL = "Hacker News"
ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"


def collect(cfg: dict) -> list[HotItem]:
    enabled = cfg.get("sources", {}).get("hackernews", {}).get("enabled", True)
    if not enabled:
        return []

    hn_cfg = cfg["sources"]["hackernews"]
    keywords = hn_cfg.get("keywords", [])
    max_items = hn_cfg.get("max_items", 20)
    min_score = hn_cfg.get("min_score", 10)

    items: list[HotItem] = []

    for keyword in keywords[:5]:  # 最多搜 5 个关键词
        if len(items) >= max_items * 2:
            break
        try:
            params = {
                "query": keyword,
                "tags": "story",
                "hitsPerPage": 30,
                "numericFilters": f"points>={min_score}",
            }
            r = requests.get(ALGOLIA_URL, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception:
            continue

        for hit in data.get("hits", []):
            title = hit.get("title", "")
            if not title:
                continue

            url = hit.get("url") or hit.get("story_url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
            points = hit.get("points", 0) or 0
            ts = hit.get("created_at_i", 0)
            published = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None

            items.append(HotItem(
                title=title,
                url=url,
                source="hackernews",
                source_label=SOURCE_LABEL,
                summary=(hit.get("story_text", "") or "")[:300],
                score=min(points, 100),
                author=hit.get("author", ""),
                published_at=published,
                tags=[],
                extra={"hn_id": hit.get("objectID", ""), "comments": hit.get("num_comments", 0)},
            ))

    # 去重
    seen: set[str] = set()
    unique: list[HotItem] = []
    for item in sorted(items, key=lambda x: x.score, reverse=True):
        key = item.title.lower()[:60]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    return unique[:max_items]
