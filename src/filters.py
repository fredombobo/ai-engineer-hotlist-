"""
热点过滤 & 去重引擎
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from src.models import HotItem


class HotFilter:
    """热度评分增强 + 去重"""

    def __init__(self, cfg: dict):
        filter_cfg = cfg.get("filter", {})

        # 关键词加分规则
        boost_rules = filter_cfg.get("boost_rules", {})
        self.keyword_boost = [kw.lower() for kw in boost_rules.get("keyword_boost", [])]
        self.keyword_boost_factor = boost_rules.get("keyword_boost_factor", 0.5)
        self.keyword_medium = [kw.lower() for kw in boost_rules.get("keyword_medium", [])]
        self.keyword_medium_factor = boost_rules.get("keyword_medium_factor", 0.2)

        # 去重
        self.dedup_hours = filter_cfg.get("dedup_hours", 48)
        self.max_total = filter_cfg.get("max_total", 80)

        # 时效性: 只保留过去 N 小时
        self.recent_hours = filter_cfg.get("recent_hours", 24)

    def _filter_fresh(self, items: list[HotItem]) -> list[HotItem]:
        """只保留过去 recent_hours 小时内的条目"""
        if self.recent_hours <= 0:
            return items
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.recent_hours)
        result = []
        for item in items:
            if item.published_at and item.published_at >= cutoff:
                result.append(item)
        return result

    def apply_boost(self, items: list[HotItem]) -> list[HotItem]:
        """根据关键词给热度加分"""
        for item in items:
            text = (item.title + " " + item.summary).lower()

            # 强关键词 +50%
            if any(kw in text for kw in self.keyword_boost):
                item.score *= (1 + self.keyword_boost_factor)

            # 中等关键词 +20%
            if any(kw in text for kw in self.keyword_medium):
                item.score *= (1 + self.keyword_medium_factor)

            # 时间衰减: 超过 24 小时的,每多 12 小时扣 5%
            if item.published_at:
                age = (datetime.now(timezone.utc) - item.published_at).total_seconds() / 3600
                if age > 24:
                    decay = 1.0 - (age - 24) / 240  # 10天后衰减到 0
                    item.score *= max(decay, 0.1)

            # 四舍五入保留1位
            item.score = round(item.score, 1)

        return items

    def deduplicate(self, items: list[HotItem]) -> list[HotItem]:
        """去重: 相同 URL 或高度相似标题只保留一条"""
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        deduped: list[HotItem] = []

        for item in sorted(items, key=lambda x: x.score, reverse=True):
            # URL 去重
            if item.url in seen_urls:
                continue
            seen_urls.add(item.url)

            # 标题相似度去重 (前 60 个字符)
            title_key = item.title.lower()[:60]
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            deduped.append(item)

        return deduped

    def filter_and_rank(self, items: list[HotItem]) -> list[HotItem]:
        """完整流水线: 时效过滤 → 加分 → 去重 → 排序 → 截取"""
        items = self._filter_fresh(items)
        items = self.apply_boost(items)
        items = self.deduplicate(items)
        items.sort(key=lambda x: x.score, reverse=True)
        return items[:self.max_total]


def run_filter(items: list[HotItem], cfg: dict) -> list[HotItem]:
    """便捷入口"""
    hf = HotFilter(cfg)
    return hf.filter_and_rank(items)
