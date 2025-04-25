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

仮想環境をアクティベートした状態で、`src/scraper.py` を実行します。

```bash
python src/scraper.py [都道府県コード] [開始ページ] [求人区分コード] [--fetch-details] [--prompt-interval N]
```

**位置引数:**

*   **`都道府県コード`:** (任意) ハローワークの都道府県コード (1～47)。海外は `59`。 **デフォルト: `26` (京都府)**
*   **`開始ページ`:** (任意) スクレイピングを開始する求人一覧のページ番号。1以上の整数。 **デフォルト: `1`**
*   **`求人区分コード`:** (任意) ハローワークの求人区分コード。 **デフォルト: `1` (一般求人)**
    *   `1`: 一般
    *   `2`: 新卒・既卒
    *   `3`: 季節
    *   `4`: 出稼ぎ
    *   `5`: 障害者

**オプション引数:**

*   **`--fetch-details`:** このフラグを指定すると、求人一覧の取得後、各求人の詳細情報も取得して別のファイルに保存します。
*   **`--prompt-interval N`:** (任意) `N` ページ取得するごとに、処理を継続するか確認するプロンプトを表示します。`0` を指定するとプロンプトは表示されません。 **デフォルト: `5`**

**引数の指定について:**

*   位置引数は順番通りに指定する必要があります。例えば、求人区分コードを指定したい場合は、都道府県コードと開始ページも指定する必要があります。
*   オプション引数はどの位置にでも指定できます。

**例:**

*   **京都府の一般求人を1ページ目から取得 (すべてデフォルト):**
    ```bash
    python src/scraper.py
    ```
*   **東京都 (13) の一般求人を1ページ目から取得:**
    ```bash
    python src/scraper.py 13
    ```
*   **東京都 (13) の一般求人を5ページ目から取得:**
    ```bash
    python src/scraper.py 13 5
    ```
*   **東京都 (13) の新卒・既卒求人 (2) を5ページ目から取得:**
    ```bash
    python src/scraper.py 13 5 2
    ```
*   **大阪府 (27) の障害者求人 (5) を1ページ目から取得し、詳細情報も取得:**
    ```bash
    python src/scraper.py 27 1 5 --fetch-details
    ```
*   **京都府の一般求人を1ページ目から取得し、2ページごとに継続確認:**
    ```bash
    python src/scraper.py --prompt-interval 2
    ```
*   **東京都 (13) の一般求人を3ページ目から取得し、詳細情報も取得、10ページごとに継続確認:**
    ```bash
    python src/scraper.py 13 3 --fetch-details --prompt-interval 10
    ```

## 出力

スクレイピング結果は `output` ディレクトリにCSVファイルとして保存されます。

*   **一覧データ:** `hellowork_jobs_list_page_[ページ番号]_[都道府県コード]_[実行日時YYYYMMDD].csv`
    *   例: `output/hellowork_jobs_list_page_1_26_20250425.csv`
*   **詳細データ ( `--fetch-details` 指定時):** `hellowork_jobs_details_[ページ番号]_[都道府県コード]_[実行日時YYYYMMDD]_details.csv`
    *   例: `output/hellowork_jobs_details_1_26_20250425_details.csv`
    *   詳細データファイルは、元となった一覧データファイルごとに生成されます。

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
