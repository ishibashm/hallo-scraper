# ハローワーク求人情報スクレイピングの設定ファイル

# 基本URL
BASE_URL = "https://www.hellowork.mhlw.go.jp/kensaku/GECA110010.do"

# 検索条件ペイロード (簡略版)
# 必須と思われるキーに絞り込む
SEARCH_PAYLOAD = {
    "kjKbnRadioBtn": "1",      # 求人区分 (一般)
    "tDFK1CmbBox": "",         # 都道府県コード (スクリプトで設定)
    "searchBtn": "%E6%A4%9C%E7%B4%A2", # "検索"
    "kyujinkensu": "0",        # 初回検索時は0
    "summaryDisp": "false",    # 初回検索時はfalse
    "searchInitDisp": "0",     # 初回検索時は0
    "screenId": "GECA110010",  # スクリーンID
    "maba_vrbs": "infTkRiyoDantaiBtn%2CsearchShosaiBtn%2CsearchBtn%2CsearchNoBtn%2CsearchClearBtn%2CdispDetailBtn%2CkyujinhyoBtn", # 不明だが念のため残す
    # --- 不要と思われる空のキーを削除 ---
    "kSNoJo": "", # 詳細表示用なので初回は不要
    "kSNoGe": "", # 詳細表示用なので初回は不要
    "nenreiInput": "",
    "tDFK2CmbBox": "",
    "tDFK3CmbBox": "",
    "sKGYBRUIJo1": "",
    "sKGYBRUIGe1": "",
    "sKGYBRUIJo2": "",
    "sKGYBRUIGe2": "",
    "sKGYBRUIJo3": "",
    "sKGYBRUIGe3": "",
    "freeWordInput": "",
    "nOTKNSKFreeWordInput": "",
    "kJNoJo1": "",
    "kJNoGe1": "",
    "kJNoJo2": "",
    "kJNoGe2": "",
    "kJNoJo3": "",
    "kJNoGe3": "",
    "kJNoJo4": "",
    "kJNoGe4": "",
    "kJNoJo5": "",
    "kJNoGe5": "",
    "jGSHNoJo": "",
    "jGSHNoChuu": "",
    "jGSHNoGe": "",
    "iNFTeikyoRiyoDantaiID": "",
    "searchClear": "0",
    "siku1Hidden": "",
    "siku2Hidden": "",
    "siku3Hidden": "",
    "kiboSuruSKSU1Hidden": "",
    "kiboSuruSKSU2Hidden": "",
    "kiboSuruSKSU3Hidden": "",
    "action": "",
    "codeAssistType": "",
    "codeAssistKind": "",
    "codeAssistCode": "",
    "codeAssistItemCode": "",
    "codeAssistItemName": "",
    "codeAssistDivide": "",
    "preCheckFlg": "false"
}

# CSSセレクタ (求人リストページ - 2025/04 HTML構造に基づく - 再修正)
LIST_SELECTORS = {
    # --- Header items ---
    "job_title": "tr.kyujin_head td[class='m13 fs1'] div",
    "reception_date": "tr.kyujin_head + tr div.fs13.ml01:nth-of-type(1)",
    "deadline_date": "tr.kyujin_head + tr div.fs13.ml01:nth-of-type(2)",

    # --- Body items (using tr.border_new within tr.kyujin_body) ---
    # Select the second td (value) in the tr.border_new that contains the specific label text in the first td.
    # Using :contains is simpler for now, though potentially less robust than exact matching if labels change slightly.
    "job_category": "tr.kyujin_body tr.border_new:has(td:contains('求人区分')) > td:nth-of-type(2) > div",
    "office_name": "tr.kyujin_body tr.border_new:has(td:contains('事業所名')) > td:nth-of-type(2) > div",
    "work_location": "tr.kyujin_body tr.border_new:has(td:contains('就業場所')) > td:nth-of-type(2) > div",
    "job_description": "tr.kyujin_body tr.border_new:has(td:contains('仕事の内容')) > td:nth-of-type(2) > div",
    "employment_type": "tr.kyujin_body tr.border_new:has(td:contains('雇用形態')) > td:nth-of-type(2) > div",
    "wage": "tr.kyujin_body tr.border_new:has(td:contains('賃金')) > td:nth-of-type(2) div.width15em", # Specific class for wage div
    "work_hours_system": "tr.kyujin_body tr.border_new:has(td:contains('就業時間')) > td:nth-of-type(2) > div:first-of-type", # First div usually contains system type or time
    "work_hours_1": "tr.kyujin_body tr.border_new:has(td:contains('就業時間')) > td:nth-of-type(2) > div.flex:nth-of-type(1) > div", # Time slot 1 (use nth-of-type for flex divs)
    "work_hours_2": "tr.kyujin_body tr.border_new:has(td:contains('就業時間')) > td:nth-of-type(2) > div.flex:nth-of-type(2) > div", # Time slot 2
    "work_hours_3": "tr.kyujin_body tr.border_new:has(td:contains('就業時間')) > td:nth-of-type(2) > div.flex:nth-of-type(3) > div", # Time slot 3
    "holidays": "tr.kyujin_body tr.border_new:has(td:contains('休日')) > td:nth-of-type(2) > div:first-of-type", # Holiday type
    "weekly_holiday_system": "tr.kyujin_body tr.border_new:has(td:contains('休日')) > td:nth-of-type(2) > div.flex > div", # Weekly system within flex
    "age_limit": "tr.kyujin_body tr.border_new:has(td:contains('年齢')) > td:nth-of-type(2) > div:first-of-type", # Age limit text
    "age_limit_details": "tr.kyujin_body tr.border_new:has(td:contains('年齢')) > td:nth-of-type(2) > div:nth-of-type(2)", # Details (second div if present)
    "job_number_text": "tr.kyujin_body tr.border_new:has(td:contains('求人番号')) > td:nth-of-type(2) > div", # Job number
    "publication_scope": "tr.kyujin_body tr.border_new:has(td:contains('公開範囲')) > td:nth-of-type(2) > div",
    # special_notes_labels and number_of_positions are handled separately in scraper.py
}

# CSSセレクタ (求人詳細ページ - page.txt準拠)
DETAIL_SELECTORS = {
    # ----- 求人情報 -----
    # リストページと同じ項目は省略可（重複取得しない場合）
    # "job_title": "", # 詳細ページで取得する場合
    # "reception_date": "",
    # "deadline_date": "",
    # "job_category": "",
    # "office_name": "",
    # "work_location": "", # 詳細ページの方が詳しい場合あり
    # "job_description": "",
    # "employment_type": "",
    # "wage": "",
    # "work_hours_1": "", # 詳細ページの方が詳しい場合あり
    # "work_hours_2": "",
    # "work_hours_3": "",
    # "holidays": "",
    # "age_limit": "",
    "job_number": "#ID_kyujinNumber", # 例: 詳細ページのIDがわかればより確実
    # "publication_scope": "",
    # "special_notes_labels": "",
    # "number_of_positions": "",

    # ----- 事業所情報 -----
    "office_reception": "#ID_juriAtsh",
    "office_zipcode": "#ID_szciYbn",
    "office_address": "#ID_szci",
    "office_homepage": "#ID_hp",
    "employees_total": "#ID_jgisKigyoZentai",
    "employees_location": "#ID_jgisShgBs",
    "employees_female": "#ID_jgisUchiJosei",
    "employees_parttime": "#ID_jgisUchiPart",
    "establishment_year": "#ID_setsuritsuNen",
    "capital": "#ID_shkn",
    "labor_union": "#ID_rodoKumiai",
    "business_content": "#ID_jigyoNy",
    "company_features": "#ID_kaishaNoTokucho",
    "representative_title": "#ID_yshk",
    "representative_name": "#ID_dhshaMei",
    "corporate_number": "#ID_hoNinNo",
    # --- 他に必要な項目があれば追加 ---
    "phone": 'th:contains("電話番号") + td', # page.txt には無かったため推測
}

# ページネーション設定
PAGINATION = {
    "next_button_selector": 'input[type="submit"][name="fwListNaviBtnNext"]', # 次へボタン
}

# リクエスト間隔 (秒) - ユーザー指定
REQUEST_INTERVAL = 2

# User-Agent文字列 - page.txt より
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"

# 出力設定
OUTPUT = {
    "format": "csv",
    "directory": "output",
    "filename_prefix": "hellowork_jobs_",
    "encoding": "utf-8-sig" # Excelでの文字化け防止
}
