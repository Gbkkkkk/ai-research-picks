#!/usr/bin/env python3
"""Render a public RSS feed and landing page from data/items.json."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "https://Gbkkkkk.github.io/ai-research-picks"


def parse_date(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def clean_items(raw_items: list[dict], limit: int) -> list[dict]:
    required = {"url", "title", "added_at", "summary_zh", "why_zh"}
    seen: set[str] = set()
    result: list[dict] = []
    for item in raw_items:
        missing = required - item.keys()
        if missing:
            raise ValueError(f"条目缺少字段 {sorted(missing)}: {item!r}")
        url = item["url"].strip()
        if not valid_http_url(url):
            raise ValueError(f"无效 URL: {url}")
        if url in seen:
            continue
        parse_date(item["added_at"])
        seen.add(url)
        result.append(item)
    result.sort(key=lambda item: parse_date(item["added_at"]), reverse=True)
    return result[:limit]


def item_description(item: dict) -> str:
    topics = " · ".join(item.get("topics", []))
    rows = [
        ("类型", item.get("content_type", "未分类")),
        ("作者/机构", item.get("authors", "未注明")),
        ("原始发布日期", item.get("published_at", "未注明")),
        ("主题", topics or "未分类"),
        ("推荐级别", item.get("priority", "值得浏览")),
        ("核心内容", item["summary_zh"]),
        ("为什么值得读", item["why_zh"]),
        ("局限/阅读提示", item.get("caveat_zh", "请结合原文判断。")),
    ]
    parts = [f"<p><strong>{html.escape(label)}：</strong>{html.escape(str(value))}</p>" for label, value in rows]
    parts.append(f'<p><a href="{html.escape(item["url"], quote=True)}">打开原文</a></p>')
    return "".join(parts)


def render_feed(items: list[dict], base_url: str) -> str:
    feed_url = f"{base_url}/feed.xml"
    now = datetime.now(timezone.utc)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        "    <title>AI Research Picks by Codex</title>",
        f"    <link>{html.escape(base_url)}</link>",
        "    <description>每周一和周四更新的 AI 论文与技术博客精选：AI memory、world models、information theory、理论 ML、AI detector 与前沿热点。</description>",
        "    <language>zh-CN</language>",
        f'    <atom:link href="{html.escape(feed_url)}" rel="self" type="application/rss+xml" />',
        f"    <lastBuildDate>{format_datetime(now)}</lastBuildDate>",
        "    <generator>Codex + scripts/update_feed.py</generator>",
    ]
    for item in items:
        guid = hashlib.sha256(item["url"].encode("utf-8")).hexdigest()
        lines.extend([
            "    <item>",
            f"      <title>{html.escape(item['title'])}</title>",
            f"      <link>{html.escape(item['url'])}</link>",
            f'      <guid isPermaLink="false">ai-research-picks:{guid}</guid>',
            f"      <pubDate>{format_datetime(parse_date(item['added_at']))}</pubDate>",
        ])
        for topic in item.get("topics", []):
            lines.append(f"      <category>{html.escape(topic)}</category>")
        safe_description = item_description(item).replace("]]>", "]]]]><![CDATA[>")
        lines.append(f"      <description><![CDATA[{safe_description}]]></description>")
        lines.append("    </item>")
    lines.extend(["  </channel>", "</rss>", ""])
    return "\n".join(lines)


def render_index(items: list[dict], base_url: str) -> str:
    cards = []
    for item in items:
        topics = " · ".join(item.get("topics", []))
        published = item.get("published_at", "日期未注明")
        cards.append(
            '<article class="card">'
            f'<div class="meta">{html.escape(item.get("priority", "值得浏览"))} · {html.escape(item.get("content_type", "未分类"))} · {html.escape(published)} · {html.escape(topics)}</div>'
            f'<h2><a href="{html.escape(item["url"], quote=True)}">{html.escape(item["title"])}</a></h2>'
            f'<p>{html.escape(item["summary_zh"])}</p>'
            f'<p><strong>为什么值得读：</strong>{html.escape(item["why_zh"])}</p>'
            f'<p class="caveat"><strong>阅读提示：</strong>{html.escape(item.get("caveat_zh", "请结合原文判断。"))}</p>'
            '</article>'
        )
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="alternate" type="application/rss+xml" title="AI Research Picks by Codex" href="{base_url}/feed.xml">
  <title>AI Research Picks by Codex</title>
  <style>
    :root {{ color-scheme: light dark; --accent:#6957ff; --muted:#6b7280; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font:16px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif; }}
    main {{ width:min(820px,calc(100% - 32px)); margin:48px auto 80px; }}
    header {{ margin-bottom:36px; }}
    h1 {{ font-size:clamp(2rem,6vw,3.5rem); line-height:1.1; margin:.2em 0; }}
    h2 {{ line-height:1.3; }}
    a {{ color:var(--accent); }}
    .subscribe {{ display:inline-block; padding:10px 16px; border:1px solid currentColor; border-radius:999px; text-decoration:none; font-weight:650; }}
    .card {{ padding:24px 0; border-top:1px solid color-mix(in srgb,currentColor 18%,transparent); }}
    .meta,.caveat {{ color:var(--muted); }}
    footer {{ margin-top:40px; color:var(--muted); }}
  </style>
</head>
<body><main>
  <header>
    <p>CURATED BY CODEX</p>
    <h1>AI Research Picks</h1>
    <p>AI memory、world models、information theory、理论 ML、AI detector 与其他前沿研究。周一少量速览，周四完整精选。</p>
    <a class="subscribe" href="{base_url}/feed.xml">订阅 RSS</a>
  </header>
  {''.join(cards)}
  <footer>这里只发布公开论文/博客的链接与原创中文摘要，不包含私人阅读记录。</footer>
</main></body></html>
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    raw_items = json.loads((ROOT / "data" / "items.json").read_text(encoding="utf-8"))
    items = clean_items(raw_items, args.limit)
    (ROOT / "feed.xml").write_text(render_feed(items, base_url), encoding="utf-8", newline="\n")
    (ROOT / "index.html").write_text(render_index(items, base_url), encoding="utf-8", newline="\n")
    ET.parse(ROOT / "feed.xml")
    print(f"Rendered {len(items)} unique item(s); RSS XML is valid.")


if __name__ == "__main__":
    main()
