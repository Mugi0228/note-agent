"""
Playwrightを使ってnoteに下書き保存するモジュール
投稿ボタンは押さない（人間が確認してから投稿する）
"""

import os
import time
from playwright.sync_api import sync_playwright


NOTE_EMAIL = os.environ["NOTE_EMAIL"]
NOTE_PASSWORD = os.environ["NOTE_PASSWORD"]


def save_as_draft(title: str, body: str) -> bool:
    """
    noteに記事を下書き保存する

    Args:
        title: 記事タイトル
        body: 記事本文（Markdown）

    Returns:
        成功したかどうか
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        try:
            # --- ログイン ---
            print("[publisher] noteにログイン中...")
            page.goto("https://note.com/login", wait_until="networkidle")
            time.sleep(2)

            page.fill('input[name="email"]', NOTE_EMAIL)
            page.fill('input[name="password"]', NOTE_PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            if "login" in page.url:
                print("[publisher] ログイン失敗")
                return False
            print("[publisher] ログイン成功")

            # --- 新規記事作成 ---
            page.goto("https://note.com/notes/new", wait_until="networkidle")
            time.sleep(3)

            # タイトル入力
            title_input = page.locator('[placeholder="記事タイトル"]').first
            title_input.click()
            title_input.fill(title)
            time.sleep(1)

            # 本文入力（contenteditable）
            body_area = page.locator('[contenteditable="true"]').first
            body_area.click()
            # Markdownをプレーンテキストとして貼り付け
            page.keyboard.type(body, delay=10)
            time.sleep(2)

            # --- 下書き保存 ---
            # 右上の「保存」または「下書き保存」ボタンをクリック
            save_button = page.locator('button:has-text("下書き保存")').first
            if save_button.is_visible():
                save_button.click()
            else:
                # キーボードショートカットで保存
                page.keyboard.press("Control+s")
            time.sleep(3)

            print(f"[publisher] 下書き保存完了: {title[:40]}")
            return True

        except Exception as e:
            print(f"[publisher] エラー: {e}")
            # スクリーンショットを保存（デバッグ用）
            page.screenshot(path="data/error_screenshot.png")
            return False

        finally:
            browser.close()
