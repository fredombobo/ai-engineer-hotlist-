"""Collector: 中文源 (原生 RSS)"""
import feedparser, requests
from datetime import datetime, timezone
from src.models import HotItem

SOURCE_LABEL = "中文"
FEEDS = [("36kr", "https://36kr.com/feed"), ("huxiu", "https://www.huxiu.com/rss/0.xml"), ("zhihu", "https://www.zhihu.com/rss")]

def collect(cfg):
    if not cfg["sources"]["cn_social"]["enabled"]: return []
    max_n = cfg["sources"]["cn_social"].get("max_items", 20)
    items = []; seen = set()
    for name, url in FEEDS:
        if len(items) >= max_n: break
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200: continue
            feed = feedparser.parse(r.content)
            for e in feed.entries[:8]:
                link = e.get("link", "")
                if not link or link in seen: continue
                seen.add(link)
                t = e.get("title", "").strip()
                if not t: continue
                s = (e.get("summary", "") or e.get("description", ""))[:300]
                pub = None
                tp = e.get("published_parsed")
                if tp:
                    from time import mktime
                    try: pub = datetime.fromtimestamp(mktime(tp), tz=timezone.utc)
                    except: pass
                items.append(HotItem(title=t, url=link, source="cn_social",
                    source_label=SOURCE_LABEL, summary=s, score=35,
                    author=e.get("author", name), published_at=pub, tags=[],
                    extra={"source": name}))
        except: continue
    items.sort(key=lambda x: x.score, reverse=True)
    return items[:max_n]