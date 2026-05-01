"""
Anthropic公式ブログ・Changelogを監視して新着記事を検出するモジュール
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
import httpx
from bs4 import BeautifulSoup

DATA_FILE = Path(__file__).parent.parent / "data" / "last_seen.json"

SOURCES = {
    "anthropic_blog": {
        "url": "https://www.anthropic.com/news",
        "label": "Anthropic Blog",
    },
    "anthropic_changelog": {
        "url": "https://docs.anthropic.com/en/release-notes/overview",
        "label": "Anthropic Changelog",
    },
}


def _load_last_seen() -> dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {}


def _save_last_seen(data: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _fetch_articles_from_blog(url: str) -> list[dict]:
    """Anthropicブログから記事一覧を取得"""
    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    articles = []
    # Anthropicブログのリンクを抽出（/news/ 配下のリンク）
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/news/" in href and href != "/news/":
            full_url = href if href.startswith("http") else f"https://www.anthropic.com{href}"
            title = a.get_text(strip=True)
            if title and len(title) > 5:  # 短すぎるテキストは除外
                articles.append({
                    "url": full_url,
                    "title": title,
                    "id": hashlib.md5(full_url.encode()).hexdigest(),
                })

    # 重複URLを除去
    seen_urls = set()
    unique = []
    for a in articles:
        if a["url"] not in seen_urls:
            seen_urls.add(a["url"])
            unique.append(a)
    return unique


def _fetch_articles_from_changelog(url: str) -> list[dict]:
    """Anthropic Changelogから更新情報を取得"""
    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    articles = []
    # h2/h3タグ（日付見出し）を取得
    for heading in soup.find_all(["h2", "h3"]):
        text = heading.get_text(strip=True)
        if text:
            article_id = hashlib.md5(text.encode()).hexdigest()
            # 直後のテキスト（概要）を取得
            description = ""
            sibling = heading.find_next_sibling()
            if sibling:
                description = sibling.get_text(strip=True)[:200]
            articles.append({
                "url": url,
                "title": f"[Changelog] {text}",
                "description": description,
                "id": article_id,
            })
    return articles[:10]  # 最新10件のみ


def fetch_new_articles() -> list[dict]:
    """
    全ソースを巡回し、前回から新しく追加された記事を返す
    """
    last_seen = _load_last_seen()
    new_articles = []

    for source_key, source in SOURCES.items():
        print(f"[scraper] Checking {source['label']}...")
        try:
            if source_key == "anthropic_changelog":
                articles = _fetch_articles_from_changelog(source["url"])
            else:
                articles = _fetch_articles_from_blog(source["url"])

            seen_ids = set(last_seen.get(source_key, []))
            for article in articles:
                if article["id"] not in seen_ids:
                    article["source"] = source["label"]
                    article["detected_at"] = datetime.now().isoformat()
                    new_articles.append(article)
                    print(f"  [NEW] {article['title'][:60]}")

            # 最新IDリストを保存（最大100件）
            all_ids = list(seen_ids | {a["id"] for a in articles})
            last_seen[source_key] = all_ids[:100]

        except Exception as e:
            print(f"  [ERROR] {source['label']}: {e}")

    _save_last_seen(last_seen)
    print(f"[scraper] 新着: {len(new_articles)}件")
    return new_articles
