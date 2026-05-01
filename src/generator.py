"""
Claude APIを使って、非エンジニア向けnote記事を生成するモジュール
"""

import os
import httpx
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """
あなたはAIツール「Claude」の新機能を、非エンジニアのビジネスパーソンにわかりやすく解説するnoteライターです。

## 記事の方針
- 専門用語は使わない。使う場合は必ず一言で説明する
- 「自分の仕事にどう使えるか」を必ず書く
- 読んで「試してみたい」と思わせる温度感
- 文体はフラットで親しみやすい（ですます調）
- 長さ: 800〜1200文字

## 記事の構成
1. タイトル（キャッチーに、30文字以内）
2. 導入（2〜3文。「こんな人に読んでほしい」を含める）
3. 何が変わったか（箇条書き3点以内でシンプルに）
4. 実際にどう使えるか（具体的なシーン1〜2個）
5. まとめ（1〜2文）

## 出力フォーマット
タイトルと本文をMarkdownで出力してください。
先頭行を # タイトル としてください。
"""


def fetch_article_content(url: str) -> str:
    """記事URLからテキストコンテンツを取得"""
    try:
        resp = httpx.get(url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        # 簡易テキスト抽出（HTMLタグを除去）
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        # scriptとstyleを除去
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)[:3000]
    except Exception as e:
        print(f"[generator] コンテンツ取得失敗 ({url}): {e}")
        return ""


def generate_note_article(article: dict) -> dict:
    """
    記事情報からnote用の記事を生成する

    Returns:
        {
            "title": str,
            "body": str,
            "source_title": str,
            "source_url": str,
        }
    """
    source_title = article.get("title", "")
    source_url = article.get("url", "")
    source_label = article.get("source", "")
    description = article.get("description", "")

    # 元記事のコンテンツを取得（changelogは説明文のみ使用）
    if "Changelog" in source_label:
        content = f"タイトル: {source_title}\n概要: {description}"
    else:
        content = fetch_article_content(source_url)
        if not content:
            content = f"タイトル: {source_title}"

    user_message = f"""
以下のAnthropicの公式情報をもとに、非エンジニア向けのnote記事を書いてください。

## 元情報
ソース: {source_label}
タイトル: {source_title}
URL: {source_url}
内容:
{content}
"""

    print(f"[generator] 記事生成中: {source_title[:50]}...")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    full_text = response.content[0].text

    # タイトルと本文を分離
    lines = full_text.strip().split("\n")
    title = lines[0].lstrip("# ").strip() if lines else source_title
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else full_text

    print(f"[generator] 生成完了: {title[:40]}")

    return {
        "title": title,
        "body": body,
        "source_title": source_title,
        "source_url": source_url,
    }
