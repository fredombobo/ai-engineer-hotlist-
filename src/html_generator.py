"""
HTML 页面生成器 — 用 Jinja2 渲染模板
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.models import HotItem
from src.translator import translate


def generate(cfg: dict, items: list[HotItem]):
    """生成 index.html"""
    output_path = cfg.get("output", {}).get("html", "docs/index.html")
    json_path = cfg.get("output", {}).get("json", "docs/data.json")

    # 批量翻译标题和摘要 (英→中)
    cn_sources = {"cn_social"}  # 中文源跳过翻译
    for item in items:
        if item.source not in cn_sources:
            item.extra = item.extra or {}
            item.extra["title_en"] = item.title
            item.extra["summary_en"] = item.summary
            item.title = translate(item.title)
            if item.summary and len(item.summary) < 500:
                item.summary = translate(item.summary)

    # 数据统计
    source_stats: dict[str, int] = {}
    tag_stats: dict[str, int] = {}
    for item in items:
        source_stats[item.source] = source_stats.get(item.source, 0) + 1
        for tag in item.tags:
            tag_stats[tag] = tag_stats.get(tag, 0) + 1

    # 按来源分组
    sources_order = ["github", "hackernews", "reddit", "twitter", "arxiv", "media_rss", "cn_social"]
    source_meta = {
        "github":     {"label": "GitHub",       "icon": "📦"},
        "hackernews": {"label": "Hacker News",  "icon": "💬"},
        "reddit":     {"label": "Reddit",       "icon": "👽"},
        "twitter":    {"label": "Twitter / X",  "icon": "🐦"},
        "arxiv":      {"label": "arXiv",        "icon": "📄"},
        "media_rss":  {"label": "Tech Media",   "icon": "📰"},
        "cn_social":  {"label": "中文社区",     "icon": "🇨🇳"},
    }
    sections = []
    for s in sources_order:
        section_items = [it for it in items if it.source == s]
        if not section_items:
            continue
        meta = source_meta.get(s, {"label": s, "icon": "🔗"})
        sections.append({
            "source": s,
            "label": meta["label"],
            "icon": meta["icon"],
            "articles": section_items,
        })

    # 统计列表
    stats_list = []
    for s in sources_order:
        cnt = source_stats.get(s, 0)
        if cnt:
            meta = source_meta.get(s, {"label": s})
            stats_list.append({"label": meta["label"], "count": cnt})

    now = datetime.now(timezone.utc)

    # 渲染
    env = Environment(
        loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("index.html.j2")

    html = template.render(
        sections=sections,
        source_stats=stats_list,
        total_items=len(items),
        sources_active=len(sections),
        generated_at=now.strftime("%Y-%m-%d %H:%M"),
    )

    # 写入
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    # 同时写 JSON 快照
    import json
    data = []
    for item in items:
        data.append({
            "title": item.title,
            "url": item.url,
            "source": item.source,
            "source_label": item.source_label,
            "summary": item.summary,
            "score": round(item.score, 1),
            "author": item.author,
            "published_at": item.published_at.isoformat() if item.published_at else None,
            "tags": item.tags,
            "extra": item.extra,
        })
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now.isoformat(),
            "total": len(data),
            "items": data,
        }, f, ensure_ascii=False, indent=2)

    print(f"✅ HTML generated → {output_path}")
    print(f"✅ JSON snapshot → {json_path}")
