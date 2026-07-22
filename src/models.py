"""
AI Engineer Hotlist — 数据模型 & 配置加载
"""
from __future__ import annotations

import os
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class HotItem:
    """一条热点条目"""
    title: str
    url: str
    source: str                     # 数据源标识: github/hackernews/reddit/...
    source_label: str               # 显示用: GitHub / Hacker News / Reddit / ...
    summary: str = ""
    score: float = 0.0              # 热度评分
    author: str = ""
    published_at: Optional[datetime] = None
    tags: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)   # 源特有信息

    @property
    def age_hours(self) -> float:
        """距离现在的小时数"""
        if not self.published_at:
            return 0.0
        delta = datetime.now(self.published_at.tzinfo) - self.published_at
        return max(0, delta.total_seconds() / 3600)


def load_config(path: str = "config.yaml") -> dict:
    """加载 YAML 配置,环境变量覆盖"""
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 企业微信 key 优先走环境变量
    wecom_key = os.environ.get("WECOM_WEBHOOK_KEY", "")
    if wecom_key:
        cfg["wecom"]["webhook_url"] = (
            f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={wecom_key}"
        )

    # GitHub Token 优先走环境变量
    gh_token = os.environ.get("GH_PAT", "")
    if gh_token:
        cfg["github_token"] = gh_token

    return cfg
