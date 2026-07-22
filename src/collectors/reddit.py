"""Collector: Reddit (通过公开 JSON API,无需凭证)"""
from __future__ import annotations

import requests
from datetime import datetime, timezone
from src.models import HotItem


SOURCE_LABEL = "Reddit"
USER_AGENT = "Mozilla/5.0 (compatible; AI-Engineer-Hotlist/1.0)"


def collect(cfg: dict) -> list[HotItem]:
    enabled = cfg.get("sources", {}).get("reddit", {}).get("enabled", True)
    if not enabled:
        return []

    reddit_cfg = cfg["sources"]["reddit"]
    subreddits = reddit_cfg.get("subreddits", [])
    max_items = reddit_cfg.get("max_items", 20)
    min_score = reddit_cfg.get("min_score", 10)

    items: list[HotItem] = []
    seen_urls: set[str] = set()

    for sub_name in subreddits:
        if len(items) >= max_items * 2:
            break
        try:
            # Reddit 公开 JSON: 不需要 API key
            url = f"https://www.reddit.com/r/{sub_name}/hot.json?limit=25"
            r = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )
            if r.status_code != 200:
                continue
            data = r.json()
        except Exception:
            continue

        for post in data.get("data", {}).get("children", []):
            pdata = post.get("data", {})
            score = pdata.get("score", 0) or 0
            if score < min_score:
                continue

            post_url = pdata.get("url", "")
            permalink = pdata.get("permalink", "")
            full_url = post_url or f"https://reddit.com{permalink}"
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            title = pdata.get("title", "").strip()
            if not title:
                continue

            ts = pdata.get("created_utc", 0)
            published = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None

            # 自动打标签
            title_lower = title.lower()
            tags = []
            if any(kw in title_lower for kw in ["llm", "gpt", "claude", "chatgpt", "gemini", "llama"]):
                tags.append("LLM")
            if "agent" in title_lower:
                tags.append("Agent")
            if "open source" in title_lower or "opensource" in title_lower:
                tags.append("Open Source")
            if any(kw in title_lower for kw in ["rag", "retrieval"]):
                tags.append("RAG")
            if any(kw in title_lower for kw in ["train", "fine-tune", "fine tune"]):
                tags.append("Training")

            items.append(HotItem(
                title=title,
                url=full_url,
                source="reddit",
                source_label=SOURCE_LABEL,
                summary=(pdata.get("selftext", "") or "")[:300],
                score=min(score / 10, 100),
                author=pdata.get("author", ""),
                published_at=published,
                tags=tags,
                extra={
                    "subreddit": sub_name,
                    "comments": pdata.get("num_comments", 0),
                    "upvotes": score,
                },
            ))

    items.sort(key=lambda x: x.score, reverse=True)
    return items[:max_items]
