import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import BASE_URL, SEARCH_PAYLOAD, LIST_SELECTORS, DETAIL_SELECTORS, PAGINATION, REQUEST_INTERVAL, USER_AGENT, OUTPUT

def test_settings():
    """設定ファイルの内容を確認するテスト"""
    print("基本URL:", BASE_URL)
    print("検索ペイロード:", SEARCH_PAYLOAD)
    print("リストセレクタ:", LIST_SELECTORS)
    print("詳細セレクタ:", DETAIL_SELECTORS)
    print("ページネーション設定:", PAGINATION)
    print("リクエスト間隔:", REQUEST_INTERVAL)
    print("User-Agent:", USER_AGENT)
    print("出力設定:", OUTPUT)

if __name__ == "__main__":
    test_settings()
