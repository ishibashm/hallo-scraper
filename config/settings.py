# ハローワーク求人情報スクレイピングの設定ファイル

# 基本URL
BASE_URL = "https://www.hellowork.mhlw.go.jp/kensaku/GECA110010.do"

# 検索条件ペイロード (初期値、必要に応じて調整)
SEARCH_PAYLOAD = {
    "kjKbnRadioBtn": "1",  # 求人区分：一般求人
    "tDFKCmbBox": "26",    # 都道府県：京都府 (例)
    "action": "",
    "searchBtn": "検索"
}

# CSSセレクタ (求人リストページ)
LIST_SELECTORS = {
    "job_container": "table.kyujin",
    "job_link": "a[href*='dispDetailBtn']",
    "job_id_params": ["kJNo", "jGSHNo"]
}

# CSSセレクタ (求人詳細ページ)
DETAIL_SELECTORS = {
    "job_number": "span.job-id",
    "company_name": "p.company",
    "location": "p.location",
    "salary": "p.salary",
    "hours": "p.hours",
    "qualification": "p.qualification",
    "benefits": "p.benefits",
    "homepage": "p.homepage",
    "phone": "p.phone"
}

# ページネーション設定
PAGINATION = {
    "next_button": "a.next",
    "max_pages": 10  # 最大ページ数、必要に応じて調整
}

# リクエスト間隔 (秒)
REQUEST_INTERVAL = 2

# User-Agent文字列
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# 出力設定
OUTPUT = {
    "format": "csv",
    "directory": "output",
    "filename_prefix": "hellowork_jobs_",
    "encoding": "utf-8"
}
