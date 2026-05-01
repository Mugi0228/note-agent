"""
パイプライン全体のエントリーポイント

実行フロー:
  1. Anthropicサイトを監視して新着記事を検出
  2. Claude APIで非エンジニア向け記事を生成
  3. noteに下書き保存
"""

import sys
from scraper import fetch_new_articles
from generator import generate_note_article
from note_publisher import save_as_draft


def main():
    print("=" * 50)
    print("note-agent パイプライン開始")
    print("=" * 50)

    # Step 1: 新着記事を検出
    new_articles = fetch_new_articles()

    if not new_articles:
        print("新着記事なし。終了します。")
        sys.exit(0)

    # Step 2 & 3: 記事生成 → 下書き保存
    success_count = 0
    for article in new_articles:
        print(f"\n--- 処理中: {article['title'][:50]} ---")

        # 記事生成
        generated = generate_note_article(article)

        # 下書き保存
        ok = save_as_draft(
            title=generated["title"],
            body=generated["body"],
        )

        if ok:
            success_count += 1

    print("\n" + "=" * 50)
    print(f"完了: {success_count}/{len(new_articles)}件 下書き保存しました")
    print("noteにログインして確認 → 投稿ボタンを押してください")
    print("=" * 50)


if __name__ == "__main__":
    main()
