"""翻译工具: 英文→中文 (直接调 Google Translate API,零依赖)"""
from __future__ import annotations
import hashlib
import json
import re
import requests

_CACHE: dict[str, str] = {}
_API_URL = "https://translate.googleapis.com/translate_a/single"


def translate(text: str) -> str:
    """英译中,带内存缓存"""
    if not text or not text.strip():
        return text
    key = hashlib.md5(text.encode()).hexdigest()
    if key in _CACHE:
        return _CACHE[key]
    try:
        params = {
            "client": "gtx",
            "sl": "en",
            "tl": "zh-CN",
            "dt": "t",
            "q": text[:2000],
        }
        r = requests.get(_API_URL, params=params, timeout=10)
        if r.status_code == 200:
            result = "".join(seg[0] for seg in r.json()[0] if seg[0])
            _CACHE[key] = result
            return result
    except Exception:
        pass
    return text


def translate_batch(texts: list[str]) -> list[str]:
    return [translate(t) for t in texts]
