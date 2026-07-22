"""Collector: GitHub Trending"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import requests
from github import Github, GithubException

from src.models import HotItem


SOURCE_LABEL = "GitHub"
TRENDING_API = "https://api.github.com/search/repositories"


def collect(cfg: dict) -> list[HotItem]:
    """从 GitHub Trending 收集热门 AI 仓库"""
    enabled = cfg.get("sources", {}).get("github", {}).get("enabled", True)
    if not enabled:
        return []

    gh_cfg = cfg["sources"]["github"]
    languages = gh_cfg.get("languages", [])
    max_items = gh_cfg.get("max_items", 15)

    items: list[HotItem] = []

    # 备选: 用 GitHub Search API 搜 AI 相关高星仓库
    token = cfg.get("github_token", "") or ""
    if token:
        from github import Auth
        auth = Auth.Token(token)
        g = Github(auth=auth)
    else:
        g = Github()

    # 综合搜索: AI/ML/LLM 关键词,按 stars 降序,最近一周
    queries = [
        'topic:artificial-intelligence',
        'topic:machine-learning',
        'topic:deep-learning',
        'topic:llm',
        'topic:large-language-model',
        'topic:generative-ai',
        'topic:rag',
        'topic:ai-agent',
        'topic:gpt',
    ]

    seen_urls: set[str] = set()
    for query in queries:
        if len(items) >= max_items * 2:
            break
        try:
            repos = g.search_repositories(
                query=query,
                sort="stars",
                order="desc",
            )
            for repo in repos[:max_items]:
                url = repo.html_url
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # 语言过滤
                lang = repo.language
                if languages and lang and lang.lower() not in [l.lower() for l in languages]:
                    # 不过滤太严格,留一些
                    pass

                items.append(HotItem(
                    title=repo.full_name,
                    url=url,
                    source="github",
                    source_label=SOURCE_LABEL,
                    summary=(repo.description or "")[:200],
                    score=min(repo.stargazers_count / 10, 100),  # 归一化
                    author=repo.owner.login if repo.owner else "",
                    published_at=repo.pushed_at if repo.pushed_at else datetime.now(timezone.utc),
                    tags=["AI"] if "ai" in (repo.description or "").lower() else [],
                    extra={
                        "stars": repo.stargazers_count,
                        "forks": repo.forks_count,
                        "language": repo.language or "unknown",
                        "topics": repo.get_topics() if hasattr(repo, 'get_topics') else [],
                    }
                ))
        except GithubException as e:
            # API rate limit 或无结果时静默处理
            continue

    # 按 score 排序后截取
    items.sort(key=lambda x: x.score, reverse=True)
    return items[:max_items]
