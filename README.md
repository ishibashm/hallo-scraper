# HelloWork Scraper

ハローワークインターネットサービスの求人情報をスクレイピングするためのPythonプロジェクトです。

## 概要

指定された都道府県およびページの求人一覧情報を取得し、CSVファイルとして `output` ディレクトリに出力します。
Seleniumを使用してブラウザを自動操作するため、ウェブサイトの構造変更の影響を受ける可能性があります。

## セットアップ

1.  **Pythonのインストール:** Python 3.x がインストールされていることを確認してください。
2.  **仮想環境の作成:**
    ```bash
    python -m venv .venv
    ```
3.  **仮想環境のアクティベート:**
    *   Windows (PowerShell):
        ```powershell
        .\.venv\Scripts\Activate.ps1
        ```
    *   macOS/Linux:
        ```bash
        source .venv/bin/activate
        ```
4.  **依存ライブラリのインストール:**
    ```bash
    pip install -r requirements.txt
    ```
    (`requirements.txt` には `selenium`, `beautifulsoup4`, `lxml`, `pandas`, `chromedriver-autoinstaller` が含まれている想定です)

## 実行方法

仮想環境をアクティベートした状態で、以下のコマンドを実行します。

```bash
python src/scraper.py [都道府県コード] [ページ番号]
```

*   **都道府県コード:** (任意) ハローワークの都道府県コード (1～47)。デフォルトは `26` (京都府)。
*   **ページ番号:** (任意) 取得したい求人一覧のページ番号。デフォルトは `1`。

**例:**

*   京都府の1ページ目を取得 (デフォルト):
    ```bash
    python src/scraper.py
    ```
*   東京都 (コード: 13) の5ページ目を取得:
    ```bash
    python src/scraper.py 13 5
    ```

## 出力

スクレイピング結果は `output` ディレクトリにCSVファイルとして保存されます。ファイル名は以下の形式です。

`hellowork_jobs_list_page_[ページ番号]_[都道府県コード]_[実行日時YYYYMMDD].csv`

例: `output/hellowork_jobs_list_page_1_26_20250424.csv`

## 設定

スクレイピングに関する設定は `config/settings.py` で変更できます。

*   `BASE_URL`: ハローワークの検索URL
*   `LIST_SELECTORS`: 求人一覧ページのデータ抽出に使用するCSSセレクタ
*   `PAGINATION`: ページネーション関連のセレクタ
*   `REQUEST_INTERVAL`: ページ遷移後の待機時間 (秒)
*   `USER_AGENT`: リクエスト時に使用するUser-Agent
*   `OUTPUT`: 出力ファイルに関する設定 (フォーマット、ディレクトリ名、プレフィックス、エンコーディング)

## 注意点

*   ハローワークインターネットサービスのウェブサイト構造が変更されると、スクレイピングが正常に動作しなくなる可能性があります。その場合は `config/settings.py` のCSSセレクタや `src/scraper.py` の抽出ロジックを修正する必要があります。
*   スクレイピングを行う際は、サーバーに過度な負荷をかけないよう、`REQUEST_INTERVAL` を適切に設定してください。
