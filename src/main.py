#!/usr/bin/env python3
"""
AI Engineer Hotlist 主编排器

用法:
    python -m src.main                          # 运行所有 collector
    python -m src.main --dry-run                # 只打印不推送
    python -m src.main --sources github,hn      # 只跑指定源

可验证成功标准:
    1. 每个 collector 返回 list[HotItem]
    2. HotFilter 去重合并 → 最多 max_total 条
    3. 生成 docs/index.html (GitHub Pages 根目录)
    4. 若 WECOM_WEBHOOK_KEY 存在 → 推送到企业微信
"""
from __future__ import annotations

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

# 确保项目根目录在 path 中
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models import load_config, HotItem
from src.filters import HotFilter
from src.html_generator import generate
from src.notifiers import push

# ---- 收集器注册表 ----
COLLECTORS: dict[str, tuple[str, callable]] = {
    "github":      ("src.collectors.github",      None),
    "hackernews":  ("src.collectors.hackernews",   None),
    "reddit":      ("src.collectors.reddit",       None),
    "twitter":     ("src.collectors.twitter",      None),
    "arxiv":       ("src.collectors.arxiv",        None),
    "media_rss":   ("src.collectors.media_rss",    None),
    "cn_social":   ("src.collectors.cn_social",    None),
}


def _import_collector(mod_path: str):
    """动态导入 collector module"""
    import importlib
    mod = importlib.import_module(mod_path)
    return mod.collect


def main():
    # ---- 解析参数 ----
    dry_run = "--dry-run" in sys.argv
    source_filter = None
    for arg in sys.argv[1:]:
        if arg.startswith("--sources="):
            source_filter = [s.strip() for s in arg.split("=", 1)[1].split(",")]
        elif arg == "--dry-run":
            pass
        elif arg.startswith("--sources"):
            # 下一个参数
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv) and not sys.argv[idx+1].startswith("--"):
                source_filter = [s.strip() for s in sys.argv[idx+1].split(",")]

    # ---- 加载配置 ----
    config_path = project_root / "config.yaml"
    cfg = load_config(str(config_path))

    # ---- 运行收集器 ----
    all_items: list[HotItem] = []
    enabled_sources = [
        name for name, (mod_path, _) in COLLECTORS.items()
        if cfg.get("sources", {}).get(name, {}).get("enabled", True)
    ]

    # 如果指定了源过滤,只跑指定的
    if source_filter:
        enabled_sources = [s for s in enabled_sources if s in source_filter]

    for name in enabled_sources:
        mod_path = COLLECTORS[name][0]
        try:
            print(f"  → {name}: collecting...", flush=True)
            collector_fn = _import_collector(mod_path)
            items = collector_fn(cfg)
            print(f"  ✓ {name}: {len(items)} items", flush=True)
            all_items.extend(items)
        except Exception as e:
            print(f"  ✗ {name}: {e}", flush=True)

    # ---- 过滤 & 去重 ----
    print("  → filtering...", flush=True)
    hot_filter = HotFilter(cfg)
    filtered = hot_filter.filter_and_rank(all_items)

    # ---- 生成 HTML ----
    os.makedirs(project_root / "docs", exist_ok=True)
    generate(cfg, filtered)
    print(f"\n  ✓ HTML: docs/index.html ({len(filtered)} items)", flush=True)

    # ---- 保存 JSON 快照 ----
    json_path = project_root / cfg.get("output", {}).get("json", "docs/data.json")
    snapshot = [
        {
            "title": item.title,
            "url": item.url,
            "source": item.source,
            "source_label": item.source_label,
            "score": round(item.score, 1),
            "summary": item.summary[:200],
            "author": item.author,
            "published_at": item.published_at.isoformat() if item.published_at else None,
            "tags": item.tags,
            "extra": item.extra,
        }
        for item in filtered
    ]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    # ---- 推送 ----
    if not dry_run:
        wecom_key = os.environ.get("WECOM_WEBHOOK_KEY", "")
        if wecom_key or cfg.get("wecom", {}).get("webhook_url"):
            push(cfg, filtered)
            print(f"  ✓ Pushed to WeCom ({len(filtered[:10])} items)", flush=True)
        else:
            print("  - Skipped WeCom push (no webhook key)", flush=True)
    else:
        print("  - Dry-run: skipped push", flush=True)

    print(f"\n✅ Done. Total: {len(all_items)} raw → {len(filtered)} after filter", flush=True)


if __name__ == "__main__":
    main()
