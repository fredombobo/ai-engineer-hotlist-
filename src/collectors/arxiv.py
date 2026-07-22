"""Collector: arXiv (HTTP + feedparser,不依赖 arxiv 库)"""
from __future__ import annotations

import requests
import feedparser
from datetime import datetime, timezone, timedelta
from src.models import HotItem

SOURCE_LABEL = "arXiv"
API = "http://export.arxiv.org/api/query"


def collect(cfg: dict) -> list[HotItem]:
    enabled = cfg.get("sources", {}).get("arxiv", {}).get("enabled", True)
    if not enabled:
        return []

    a_cfg = cfg["sources"]["arxiv"]
    cats = a_cfg.get("categories", ["cs.AI", "cs.LG", "cs.CL"])
    max_items = a_cfg.get("max_items", 20)
    recent_days = a_cfg.get("recent_days", 3)

    items: list[HotItem] = []
    seen: set[str] = set()

    for cat in cats:
        if len(items) >= max_items:
            break
        try:
            params = {
                "search_query": f"cat:{cat}",
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "max_results": 30,
            }
            r = requests.get(API, params=params, timeout=30)
            if r.status_code != 200:
                continue

            feed = feedparser.parse(r.content)
            if feed.bozo:
                continue

            for entry in feed.entries:
                aid = entry.get("id", "")
                if aid in seen:
                    continue
                seen.add(aid)

                title = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()[:500]
                link = entry.get("link", aid)

                pub_tup = entry.get("published_parsed")
                published = None
                if pub_tup:
                    from time import mktime
                    try:
                        published = datetime.fromtimestamp(mktime(pub_tup), tz=timezone.utc)
                    except:
                        pass

                if published:
                    age = datetime.now(timezone.utc) - published
                    if age > timedelta(days=recent_days):
                        continue

                authors = ", ".join(a.get("name", "") for a in entry.get("authors", [])[:5])
                text_lower = (title + " " + summary).lower()
                score = 30
                for kw in ["llm", "gpt", "agent", "rag", "transformer", "foundation model"]:
                    if kw in text_lower:
                        score += 8
                score = min(score, 100)

                tags = []
                if "survey" in title.lower() or "review" in title.lower():
                    tags.append("Survey")
                if "benchmark" in title.lower():
                    tags.append("Benchmark")

                items.append(HotItem(
                    title=title, url=link, source="arxiv",
                    source_label=SOURCE_LABEL, summary=summary,
                    score=score, author=authors, published_at=published,
                    tags=tags,
                    extra={"categories": entry.get("tags", [])},
                ))
        except Exception:
            continue

    items.sort(key=lambda x: x.score, reverse=True)
    return items[:max_items]
