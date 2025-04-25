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
    "detail_link": "tr.kyujin_foot a[id='ID_dispDetailBtn']", # Detail link button in the list item footer
}

# CSSセレクタ (求人詳細ページ - 2025/04/25 分析結果に基づく)
DETAIL_SELECTORS = {
    # ----- 基本情報 (テーブル1) -----
    "job_number": "#ID_kjNo",                   # 求人番号
    "reception_date": "#ID_uktkYmd",            # 受付年月日
    "deadline_date": "#ID_shkiKigenHi",         # 紹介期限日
    "office_reception": "#ID_juriAtsh",         # 受理安定所
    "job_category_detail": "#ID_kjKbn",         # 求人区分 (詳細ページ用 - リストページの 'job_category' と区別)
    "online_application": "#ID_onlinJishuOboUktkKahi", # オンライン自主応募の受付
    "industry_classification": "#ID_sngBrui",   # 産業分類

    # ----- 求人事業所 (テーブル2) -----
    "office_number": "#ID_jgshNo",              # 事業所番号
    "office_name_kana": "#ID_jgshMeiKana",      # 事業所名 (カナ)
    "office_name": "#ID_jgshMei",               # 事業所名
    "office_zipcode": "#ID_szciYbn",            # 所在地 郵便番号
    "office_address": "#ID_szci",               # 所在地 住所
    "office_homepage": "#ID_hp",                # ホームページ (aタグなのでhref属性を取得)

    # ----- 仕事内容 (テーブル3) -----
    "job_title_detail": "#ID_sksu",             # 職種 (詳細ページ用)
    "job_description_detail": "#ID_shigotoNy",  # 仕事内容 (詳細ページ用)
    "employment_type_detail": "#ID_koyoKeitai", # 雇用形態 (詳細ページ用)
    "contract_type": "#ID_hakenUkeoiToShgKeitai", # 就業形態 (派遣・請負等)
    "dispatch_license_num": "#ID_hakenUkeoiToRdsha", # 労働者派遣事業の許可番号
    "employment_period_details": "#ID_koyoKikan", # 雇用期間
    "contract_renewal_possibility": "#ID_koyoKikanKeiyakuKsnNoKnsi", # 契約更新の可能性
    "contract_renewal_condition": "#ID_koyoKikanKeiyakuKsnNoJkn", # 契約更新の条件
    "work_location_detail": "#ID_shgBs",        # 就業場所
    "work_location_zip": "#ID_shgBsYubinNo",    # 就業場所 郵便番号
    "work_location_address": "#ID_shgBsJusho",  # 就業場所 住所
    "nearest_station": "#ID_shgBsMyorEki",      # 最寄り駅
    "transport_from_station": "#ID_shgBsKotsuShudan", # 最寄り駅からの交通手段
    "time_from_station": "#ID_shgBsShyoJn",     # 所要時間
    "work_location_notes": "#ID_shgBsTkjk",     # 就業場所に関する特記事項
    "smoking_measures": "#ID_shgBsKitsuTsak",   # 受動喫煙対策
    "car_commute": "#ID_mycarTskn",             # マイカー通勤
    "transfer_possibility": "#ID_tenkinNoKnsi", # 転勤の可能性
    "age_limit_detail": "#ID_nenreiSegn",       # 年齢 (詳細ページ用)
    "education_required": "#ID_grki",           # 学歴 (必須かどうか)
    "education_level": "#ID_grkiIjo",           # 学歴 (レベル)
    "required_experience": "#ID_hynaKiknt",     # 必要な経験等
    "required_pc_skills": "#ID_hynaPc",         # 必要なPCスキル
    "required_licenses": "#ID_hynaMenkyoSkku",  # 必要な免許・資格
    "trial_period": "#ID_trialKikan",           # 試用期間 (有無)
    "trial_period_duration": "#ID_trialKikanKikan", # 試用期間 (期間)
    "trial_period_conditions": "#ID_trialKikanChuuNoRodoJkn", # 試用期間中の労働条件

    # ----- 賃金・手当 (テーブル4) -----
    "wage_detail": "#ID_chgn",                  # 賃金 (a+b) (詳細ページ用)
    "base_salary": "#ID_khky",                  # 基本給
    "fixed_allowance": "#ID_tgktNiShwrTat",     # 定額手当
    "fixed_overtime_pay_status": "#ID_koteiZngyKbn", # 固定残業代 (有無)
    "wage_type": "#ID_chgnKeitaiToKbn",         # 賃金形態
    "commute_allowance_status": "#ID_tsknTat",  # 通勤手当 (有無・実費)
    "commute_allowance_limit_unit": "#ID_tsknTatTsuki", # 通勤手当 (上限単位 月額など)
    "commute_allowance_limit_amount": "#ID_tsknTatKingaku", # 通勤手当 (上限金額)
    "wage_cutoff_date": "#ID_chgnSkbi",         # 賃金締切日
    "wage_payment_date_type": "#ID_chgnSrbi",   # 賃金支払日 (固定など)
    "wage_payment_month": "#ID_chgnSrbiTsuki",  # 支払月
    "wage_payment_day": "#ID_chgnSrbiHi",       # 支払日
    "pay_raise_system": "#ID_shokyuSd",         # 昇給制度
    "pay_raise_last_year": "#ID_shokyuMaeNendoJisseki", # 昇給(前年度実績)
    "pay_raise_amount_rate": "#ID_sokkgSkrt",   # 昇給金額/昇給率
    "bonus_system": "#ID_shoyoSdNoUmu",         # 賞与制度の有無

    # ----- 労働時間 (テーブル5) -----
    "work_hours_or": "#ID_shgJnOr",             # 就業時間 (又は)
    "work_hours_notes": "#ID_shgJiknTkjk",      # 就業時間に関する特記事項
    "overtime_status": "#ID_jkgiRodoJn",        # 時間外労働時間 (有無など)
    "article36_agreement": "#ID_sanrokuKyotei", # 36協定における特別条項
    "break_time": "#ID_kyukeiJn",               # 休憩時間
    "days_per_week": "#ID_shuRdNisu",           # 週所定労働日数
    "holidays_detail": "#ID_kyjs",              # 休日等
    "weekly_holiday_system_detail": "#ID_shukFtskSei", # 週休二日制
    "other_holidays": "#ID_kyjsSnta",           # その他休日
    "annual_paid_leave_6months": "#ID_nenjiYukyu", # 6ヶ月経過後の年次有給休暇日数

    # ----- その他の労働条件等 (テーブル6) -----
    "insurance": "#ID_knyHoken",                # 加入保険等
    "severance_pay_mutual_aid": "#ID_tskinKsi", # 退職金共済
    "severance_pay_system": "#ID_tskinSd",      # 退職金制度
    "retirement_age_system": "#ID_tnsei",       # 定年制
    "reemployment_system": "#ID_saiKoyoSd",     # 再雇用制度
    "extended_work_system": "#ID_kmec",         # 勤務延長
    "childcare_facility_available": "#ID_riyoKanoTkjShst", # 利用可能託児施設

    # ----- 会社の情報 (テーブル7) -----
    "employees_total": "#ID_jgisKigyoZentai",      # 従業員数 企業全体
    "employees_location": "#ID_jgisShgBs",         # 従業員数 就業場所
    "employees_female": "#ID_jgisUchiJosei",       # 従業員数 うち女性
    "employees_parttime": "#ID_jgisUchiPart",      # 従業員数 うちパート
    "establishment_year": "#ID_setsuritsuNen",     # 設立年
    "capital": "#ID_shkn",                     # 資本金
    "labor_union": "#ID_rodoKumiai",               # 労働組合
    "business_content": "#ID_jigyoNy",             # 事業内容
    "company_features": "#ID_kaishaNoTokucho",     # 会社の特長
    "representative_title": "#ID_yshk",            # 役職
    "representative_name": "#ID_dhshaMei",         # 代表者名
    "corporate_number": "#ID_hoNinNo",             # 法人番号
    "work_rules_fulltime": "#ID_fltmShgKisoku",    # 就業規則 フルタイム
    "work_rules_parttime": "#ID_partShgKisoku",    # 就業規則 パートタイム
    "childcare_leave_taken": "#ID_ikujiKyugyoStkJisseki", # 育児休業取得実績
    "caregiver_leave_taken": "#ID_kaigoKyugyoStkJisseki", # 介護休業取得実績
    "nursing_leave_taken": "#ID_kangoKyukaStkJisseki",  # 看護休暇取得実績
    "uij_turn_welcome": "#ID_uIJTurn",             # UIJターン歓迎

    # ----- 選考等 (テーブル8) -----
    "hiring_count": "#ID_saiyoNinsu",              # 採用人数
    "reason_for_recruitment": "#ID_boshuRy",       # 募集理由
    "selection_method": "#ID_selectHoho",          # 選考方法
    "result_notification_timing": "#ID_selectKekkaTsuch", # 選考結果通知のタイミング
    "document_screening_result_notification": "#ID_shoruiSelectKekka", # 書類選考結果通知
    "interview_result_notification": "#ID_mensetsuSelectKekka", # 面接選考結果通知
    "notification_method_to_applicant": "#ID_ksshEnoTsuchiHoho", # 求職者への通知方法
    "selection_date_time": "#ID_selectNichijiTo",  # 選考日時等
    "selection_location_zip": "#ID_selectBsYubinNo", # 選考場所 郵便番号
    "selection_location_address": "#ID_selectBsJusho", # 選考場所 住所
    "selection_location_station": "#ID_selectBsMyorEki", # 選考場所 最寄り駅
    "transport_to_selection_location": "#ID_selectBsMyorEkiKotsuShudan", # 最寄り駅からの交通手段
    "time_to_selection_location": "#ID_selectBsShyoJn", # 所要時間
    "application_documents": "#ID_oboShoruitou",    # 応募書類等
    "application_document_sending_method": "#ID_oboShoruiNoSofuHoho", # 応募書類の送付方法
    "other_sending_method_details": "#ID_sntaNoSofuHoho", # その他の送付方法詳細
    "mailing_address_zip": "#ID_yusoNoSofuBsYubinNo", # 郵送の送付場所 郵便番号
    "mailing_address": "#ID_yusoNoSofuBsJusho",     # 郵送の送付場所 住所
    "return_of_application_documents": "#ID_obohen", # 応募書類の返戻
    "selection_notes": "#ID_selectTkjk",           # 選考に関する特記事項
    "contact_department_title": "#ID_ttsYkm",        # 担当者 課係名、役職名
    "contact_phone": "#ID_ttsTel",                 # 担当者 電話番号
    "contact_fax": "#ID_ttsFax",                   # 担当者 FAX

    # ----- 求人に関する特記事項 (テーブル9) -----
    "job_specific_notes": "#ID_kjTkjk",            # 求人に関する特記事項

    # ----- 求人・事業所PR情報 (テーブル10) -----
    "message_from_office": "#ID_jgshKaraNoMsg",    # 事業所からのメッセージ
    "job_based_pay_system": "#ID_shokumuKyuSd",    # 職務給制度
    "reinstatement_system": "#ID_fukushokuSd",     # 復職制度

    # ----- 障害者に対する配慮に関する状況 (テーブル11) -----
    "elevator_available": "#ID_elevator",          # エレベーター
    # ... 他の配慮項目も必要に応じて追加 ...
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
