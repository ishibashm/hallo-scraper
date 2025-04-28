# HelloWork Scraper

ハローワークインターネットサービスの求人情報をスクレイピングするためのPythonプロジェクトです。

## 概要

指定された都道府県およびページの求人一覧情報を取得し、CSVファイルとJSONファイルの両方で `output` ディレクトリに出力します。
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

## 基本的な使い方 (推奨ワークフロー)

求人一覧に特定の詳細情報を追加したデータを作成したい場合の、最もシンプルで推奨される手順です。

**ステップ 1: 求人一覧の取得**

まず、`src/scraper.py` を使用して、対象の求人一覧データを取得し、ファイルに保存します。

```bash
# 例: 京都府(26)の一般求人(1)を1ページ目から取得
python src/scraper.py 26 1 1
# => output/hellowork_jobs_list_page_1_26_YYYYMMDD.csv (および .json) が生成される
```

**ステップ 2: リストのエンリッチ (詳細情報の結合)**

次に、`src/detail_scraper.py` の `--enrich` モードを使用して、ステップ1で作成した一覧ファイルに詳細情報を結合します。

```bash
# 例1: デフォルトの詳細列を追加してエンリッチ (全件処理)
python src/detail_scraper.py output/hellowork_jobs_list_page_1_26_YYYYMMDD.csv --enrich
# => output/enriched_hellowork_jobs_list_page_1_26_YYYYMMDD.csv (および .json) が生成される

# 例2: 特定の列 ('office_name', 'capital') のみ追加し、先頭10件のみ処理
python src/detail_scraper.py output/hellowork_jobs_list_page_1_26_YYYYMMDD.csv --enrich --columns "office_name,capital" --limit 10
# => output/enriched_hellowork_jobs_list_page_1_26_YYYYMMDD.csv (および .json) が生成される (10件分のデータ)
```

*   `--enrich` モードでは、既に出力済みの `enriched_*.csv` ファイルが存在する場合、そのファイルに記録されている求人（必要な詳細列が揃っている場合）については、詳細ページの再取得をスキップします。
*   `--limit N` は、入力一覧ファイルの先頭から処理する **行数 (求人件数)** を指定します (スキップされた行もカウントに含まれます)。

## その他の使い方

**1. 詳細データのみを別途取得・追記する**

求人一覧とは別に、詳細データだけを収集・管理したい場合は、`src/detail_scraper.py` を `--enrich` オプションなしで使用します。`src/scraper.py` の `--fetch-details` オプションも内部でこのモードを使用します。

```bash
# 例: list_page_1.csv の未取得求人の詳細を最大10件取得し、details_1_details.csv に追記
python src/detail_scraper.py output/hellowork_jobs_list_page_1_26_YYYYMMDD.csv --limit 10
```
*   このモードでは、出力先の `*_details.csv` ファイルに存在する求人はスキップされます。

**2. 手動でデータを結合する**

既に取得済みの「一覧データファイル」と「詳細データCSVファイル」がある場合、`src/merge_data.py` を使用して手動で結合できます。

```bash
# 例: デフォルト列で結合し、新しい merged_*.csv/.json ファイルを作成
python src/merge_data.py output/list.csv output/details.csv

# 例: 指定列で結合し、元の list.csv を上書き (確認あり)
python src/merge_data.py output/list.csv output/details.csv --columns "office_name" --output-mode overwrite
```
*   詳細については、`src/merge_data.py` の説明セクションを参照してください。
## 基本的な使い方 (推奨ワークフロー)

求人一覧に特定の詳細情報を追加したデータを作成したい場合の、最もシンプルで推奨される手順です。

**ステップ 1: 求人一覧の取得**

まず、`src/scraper.py` を使用して、対象の求人一覧データを取得し、ファイルに保存します。

```bash
# 例: 京都府(26)の一般求人(1)を1ページ目から取得
python src/scraper.py 26 1 1
# => output/hellowork_jobs_list_page_1_26_YYYYMMDD.csv (および .json) が生成される
```

**ステップ 2: リストのエンリッチ (詳細情報の結合)**

次に、`src/detail_scraper.py` の `--enrich` モードを使用して、ステップ1で作成した一覧ファイルに詳細情報を結合します。

```bash
# 例1: デフォルトの詳細列を追加してエンリッチ (全件処理)
python src/detail_scraper.py output/hellowork_jobs_list_page_1_26_YYYYMMDD.csv --enrich
# => output/enriched_hellowork_jobs_list_page_1_26_YYYYMMDD.csv (および .json) が生成される

# 例2: 特定の列 ('office_name', 'capital') のみ追加し、先頭10件のみ処理
python src/detail_scraper.py output/hellowork_jobs_list_page_1_26_YYYYMMDD.csv --enrich --columns "office_name,capital" --limit 10
# => output/enriched_hellowork_jobs_list_page_1_26_YYYYMMDD.csv (および .json) が生成される (10件分のデータ)
```

*   `--enrich` モードでは、既に出力済みの `enriched_*.csv` ファイルが存在する場合、そのファイルに記録されている求人（必要な詳細列が揃っている場合）については、詳細ページの再取得をスキップします。
*   `--limit N` は、入力一覧ファイルの先頭から処理する **行数 (求人件数)** を指定します (スキップされた行もカウントに含まれます)。

## その他の使い方

**1. 詳細データのみを別途取得・追記する**

求人一覧とは別に、詳細データだけを収集・管理したい場合は、`src/detail_scraper.py` を `--enrich` オプションなしで使用します。

```bash
# 例: list_page_1.csv の未取得求人の詳細を最大10件取得し、details_1_details.csv に追記
python src/detail_scraper.py output/hellowork_jobs_list_page_1_26_YYYYMMDD.csv --limit 10
```
*   このモードでは、出力先の `*_details.csv` ファイルに存在する求人はスキップされます。

**2. 手動でデータを結合する**

既に取得済みの「一覧データファイル」と「詳細データCSVファイル」がある場合、`src/merge_data.py` を使用して手動で結合できます。

```bash
# 例: デフォルト列で結合し、新しい merged_*.csv/.json ファイルを作成
python src/merge_data.py output/list.csv output/details.csv

# 例: 指定列で結合し、元の list.csv を上書き (確認あり)
python src/merge_data.py output/list.csv output/details.csv --columns "office_name" --output-mode overwrite
```
*   詳細については、`src/merge_data.py` の説明セクションを参照してください。
## 出力

スクレイピング結果は `output` ディレクトリに保存されます。求人一覧データはCSV形式とJSON形式の両方で出力されます。

*   **一覧データ (CSV):** `hellowork_jobs_list_page_[ページ番号]_[都道府県コード]_[実行日時YYYYMMDD].csv`
    *   例: `output/hellowork_jobs_list_page_1_26_20250425.csv`
*   **一覧データ (JSON):** `hellowork_jobs_list_page_[ページ番号]_[都道府県コード]_[実行日時YYYYMMDD].json`
    *   例: `output/hellowork_jobs_list_page_1_26_20250425.json`
*   **詳細データ ( `--fetch-details` 指定時):**
    *   詳細データは現在CSVとJSON形式で出力されます (`src/detail_scraper.py` の仕様)。
    *   CSV: `hellowork_jobs_details_..._details.csv` (追記)
    *   JSON: `hellowork_jobs_details_..._details.json` (上書き)
    *   例 (CSV): `output/hellowork_jobs_details_1_26_20250425_details.csv`
    *   例 (JSON): `output/hellowork_jobs_details_1_26_20250425_details.json`
    *   詳細データファイルは、元となった一覧データファイルごとに生成されます。

## 詳細データの取得・リストのエンリッチ (個別実行)

`src/detail_scraper.py` スクリプトは、2つのモードで動作します。

1.  **詳細データのみ取得モード (デフォルト):** `src/scraper.py` で取得した求人一覧CSVを元に、各求人の詳細情報のみを取得し、別のファイルに追記保存します。
2.  **リストエンリッチモード (`--enrich`):** 求人一覧ファイル (CSV/JSON/JSONL) を元に、各求人の詳細情報を取得し、指定された詳細列を元のリストデータに結合して、新しいエンリッチ済みファイルを作成します。

```bash
# モード 1: 詳細データのみ取得 (CSV入力のみ)
python src/detail_scraper.py <一覧CSVファイルパス> [--limit N]

# モード 2: リストエンリッチ (CSV/JSON/JSONL入力)
python src/detail_scraper.py <一覧ファイルパス> --enrich [--columns <列名1,...>] [--limit N]
```

**引数:**

*   **`<一覧ファイルパス>`:** (必須)
    *   デフォルトモードの場合: `job_number` (または `kSNoJo`, `kSNoGe`) と `detail_link_href` 列を含む、`src/scraper.py` で生成された一覧 **CSV** ファイルのパス。
    *   `--enrich` モードの場合: `job_number` (または `kSNoJo`, `kSNoGe`) と `detail_link_href` 列を含む、一覧データファイル (**CSV, JSON, JSONL**) のパス。
*   **`--enrich`:** (任意) このフラグを指定すると、リストエンリッチモードで動作します。
*   **`--columns <列名1,...>`:** (任意, `--enrich` モード専用) エンリッチ時に結合する詳細データの列名をカンマ区切りで指定します。指定しない場合は、スクリプト内で定義されたデフォルト列 (事業所情報など) が使用されます。
*   **`--limit N`:** (任意) 処理する入力一覧ファイルの最大 **行数 (求人件数)** を指定します。指定しない場合は、一覧ファイル内のすべての行が処理対象となります。
    *   デフォルトモード: 既存の詳細ファイル (`*_details.csv`) に存在しない求人のうち、最大N件の詳細を取得します。
    *   `--enrich` モード: 既存のエンリッチファイル (`enriched_*.csv`) に存在し、かつ必要な詳細列がすべて揃っている求人はスキップしつつ、入力一覧ファイルの先頭から最大N行を処理します (スキップされた行もN件のカウントに含まれます)。

**動作:**

*   **デフォルトモード (`--enrich` なし):**
    1.  指定された `<一覧CSVファイルパス>` を読み込みます。
    2.  対応する詳細データCSVファイル (`output/*_details.csv`) が存在すれば、取得済みの求人番号を読み込み、スキップ対象とします。
    3.  一覧CSV内の未取得求人の詳細ページをスクレイピングします (`--limit` があればその件数まで)。
    4.  新しく取得した詳細データを、詳細データCSVファイルに **追記** します。
    5.  同時に、その時点での詳細データCSV全体のデータを、対応するJSONファイル (`output/*_details.json`) に **上書き** します。
*   **リストエンリッチモード (`--enrich` あり):**
    1.  指定された `<一覧ファイルパス>` (CSV/JSON/JSONL) を読み込みます。
    2.  対応するエンリッチ済みCSVファイル (`output/enriched_*.csv`) が存在すれば、取得済みの求人番号と詳細データを読み込みます。
    3.  一覧ファイル内の各行について、以下の処理を行います (`--limit` があればその行数まで)。
        *   求人番号がエンリッチ済みCSVに存在し、かつ `--columns` で指定された（またはデフォルトの）**すべての詳細列が既に記録されている**場合、詳細ページの取得を **スキップ** し、既存のデータを使用します。
        *   上記以外の場合、詳細ページをスクレイピングし、指定された詳細列を抽出して元のリストデータに結合します。
    4.  すべての行の処理後、最終的なエンリッチ済みデータ全体を、新しいCSVファイル (`output/enriched_*.csv`) とJSONファイル (`output/enriched_*.json`) として **上書き** 保存します。

**出力ファイル:**

*   **デフォルトモード:**
    *   詳細データ (CSV): `output/hellowork_jobs_details_..._details.csv` (追記)
    *   詳細データ (JSON): `output/hellowork_jobs_details_..._details.json` (上書き)
*   **リストエンリッチモード (`--enrich`):**
    *   エンリッチ済みデータ (CSV): `output/enriched_[元の一覧ファイル名ベース].csv` (上書き)
    *   エンリッチ済みデータ (JSON): `output/enriched_[元の一覧ファイル名ベース].json` (上書き)

**実行例:**

*   **デフォルトモード: 一覧CSV `list_page_1.csv` の未取得データを最大10件取得:**
    ```bash
    python src/detail_scraper.py output/hellowork_jobs_list_page_1_26_20250427.csv --limit 10
    ```
*   **エンリッチモード: 一覧ファイル `list.csv` をデフォルト列でエンリッチ (全件):**
    ```bash
    python src/detail_scraper.py input/list.csv --enrich
    ```
    (出力: `output/enriched_list.csv` と `.json`)
*   **エンリッチモード: 一覧ファイル `list.json` の先頭5件を、指定列でエンリッチ:**
    ```bash
    python src/detail_scraper.py input/list.json --enrich --columns "office_name,capital" --limit 5
    ```
    (出力: `output/enriched_list.csv` と `.json`。5件分のデータが含まれ、既存ファイルがあればスキップ処理が試みられる)
## データ結合

`src/scraper.py` で取得した一覧データ (CSV/JSON/JSONL) と詳細データ (CSV) を結合するには、`src/merge_data.py` スクリプトを使用します。

```bash
python src/merge_data.py <一覧ファイルパス> <詳細CSVファイルパス> [--columns <列名1,列名2,...>]
```

**引数:**

*   **`<一覧ファイルパス>`:** (必須) `src/scraper.py` で生成された一覧データファイル (CSV, JSON, JSONL のいずれか) のパス。`job_number` 列が必要です。
*   **`<詳細CSVファイルパス>`:** (必須) `src/detail_scraper.py` または `src/scraper.py --fetch-details` で生成された詳細データCSVファイルのパス。`job_number_ref` 列が必要です。
*   **`--columns <列名1,列名2,...>`:** (任意) 詳細CSVから結合したい列名をカンマ区切りで指定します。指定しない場合は、以下のデフォルト列が使用されます:
    *   `office_reception`, `industry_classification`, `office_name`, `office_zipcode`, `office_address`, `office_homepage`, `employees_total`, `employees_location`, `employees_female`, `employees_parttime`, `establishment_year`, `capital`, `labor_union`, `business_content`, `company_features`, `representative_title`, `representative_name`, `corporate_number`

**動作:**

1.  指定された一覧データファイルと詳細CSVファイルを読み込みます。
2.  詳細CSVから、結合キー (`job_number_ref`) と `--columns` で指定された列（またはデフォルト列）を選択します。
3.  一覧データと選択された詳細データを `job_number` と `job_number_ref` をキーとして左結合します。
4.  結合結果をCSV形式とJSON形式の両方で `output` ディレクトリに出力します。出力ファイル名は、入力された一覧ファイル名に基づいて自動生成されます (例: `merged_hellowork_jobs_list_page_1_26_20250428.csv` および `.json`)。

**出力ファイル:**

*   **結合データ (CSV):** `output/merged_[元の一覧ファイル名ベース].csv`
*   **結合データ (JSON):** `output/merged_[元の一覧ファイル名ベース].json`

**例:**

*   **デフォルト列を使用して結合:**
    ```bash
    python src/merge_data.py output/hellowork_jobs_list_page_1_26_20250428.csv output/hellowork_jobs_details_1_26_20250428_details.csv
    ```
    (出力: `output/merged_hellowork_jobs_list_page_1_26_20250428.csv` と `.json`)

*   **指定した列 (`office_name`, `capital`) を使用して結合:**
    ```bash
    python src/merge_data.py output/hellowork_jobs_list_page_1_26_20250428.json output/hellowork_jobs_details_1_26_20250428_details.csv --columns "office_name, capital"
    ```
    (出力: `output/merged_hellowork_jobs_list_page_1_26_20250428.csv` と `.json`)

## 設定

スクレイピングに関する設定は `config/settings.py` で変更できます。

*   `BASE_URL`: ハローワークの検索URL
*   `LIST_SELECTORS`: 求人一覧ページのデータ抽出に使用するCSSセレクタ
*   `PAGINATION`: ページネーション関連のセレクタ
*   `REQUEST_INTERVAL`: ページ遷移後の待機時間 (秒)
*   `USER_AGENT`: リクエスト時に使用するUser-Agent
*   `OUTPUT`: 出力ファイルに関する設定 (ディレクトリ名, プレフィックス, エンコーディング (`encoding` は主にCSV用, `encoding_json` でJSON用を指定可能))

## 注意点

*   ハローワークインターネットサービスのウェブサイト構造が変更されると、スクレイピングが正常に動作しなくなる可能性があります。その場合は `config/settings.py` のCSSセレクタや `src/scraper.py` の抽出ロジックを修正する必要があります。
*   スクレイピングを行う際は、サーバーに過度な負荷をかけないよう、`REQUEST_INTERVAL` を適切に設定してください。
