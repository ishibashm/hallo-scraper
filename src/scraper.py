import requests
import time
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from config.settings import BASE_URL, SEARCH_PAYLOAD, LIST_SELECTORS, DETAIL_SELECTORS, PAGINATION, REQUEST_INTERVAL, USER_AGENT, OUTPUT

class HelloWorkScraper:
    def __init__(self):
        self.job_data = []
        self.driver = self.setup_driver()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})

    def setup_driver(self):
        """Seleniumドライバーを設定"""
        import chromedriver_autoinstaller
        chromedriver_autoinstaller.install()
        options = Options()
        options.add_argument(f"user-agent={USER_AGENT}")
        options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)
        return driver

    def search_jobs(self):
        """検索条件を指定して求人リストの最初のページを取得"""
        # セッションを使用してPOSTリクエストを送信
        response = self.session.post(BASE_URL, data=SEARCH_PAYLOAD)
        if response.status_code == 200:
            print("検索リクエスト成功")
            return self.parse_job_list(response.text)
        else:
            print(f"検索リクエスト失敗: ステータスコード {response.status_code}")
            return None

    def parse_job_list(self, html_content):
        """求人リストページから各求人のキーパラメータを抽出"""
        soup = BeautifulSoup(html_content, 'lxml')
        job_containers = soup.select(LIST_SELECTORS['job_container'])
        job_links = []
        print(f"求人コンテナ数: {len(job_containers)}")
        print(f"使用しているセレクタ: {LIST_SELECTORS['job_container']}")
        
        for container in job_containers:
            links = container.select(LIST_SELECTORS['job_link'])
            print(f"コンテナ内のリンク数: {len(links)}")
            print(f"リンク用セレクタ: {LIST_SELECTORS['job_link']}")
            for link in links:
                href = link.get('href', '')
                if href:
                    params = self.extract_job_params(href)
                    if params:
                        job_links.append(params)
                        print(f"抽出されたパラメータ: {params}")
                    else:
                        print(f"パラメータ抽出失敗: {href}")
                else:
                    print("href属性が見つかりません")
        
        return job_links

    def extract_job_params(self, href):
        """URLから求人IDパラメータを抽出"""
        params = {}
        for param in LIST_SELECTORS['job_id_params']:
            if param in href:
                start_idx = href.find(param + '=') + len(param) + 1
                end_idx = href.find('&', start_idx) if '&' in href[start_idx:] else len(href)
                params[param] = href[start_idx:end_idx]
        return params if all(param in params for param in LIST_SELECTORS['job_id_params']) else None

    def get_job_details(self, job_params):
        """求人詳細ページを取得し、データを抽出"""
        detail_url = f"{BASE_URL}?action=dispDetailBtn&{'&'.join([f'{k}={v}' for k, v in job_params.items()])}"
        response = self.session.get(detail_url)
        if response.status_code == 200:
            job_details = self.parse_job_details(response.text)
            job_details.update(job_params)
            self.job_data.append(job_details)
            print(f"詳細データ取得成功: {job_params}")
        else:
            print(f"詳細ページ取得失敗: {detail_url}, ステータスコード {response.status_code}")
        time.sleep(REQUEST_INTERVAL)

    def parse_job_details(self, html_content):
        """求人詳細ページからデータを抽出"""
        soup = BeautifulSoup(html_content, 'lxml')
        details = {}
        for key, selector in DETAIL_SELECTORS.items():
            element = soup.select_one(selector)
            details[key] = element.text.strip() if element else ''
        return details

    def handle_pagination(self):
        """ページネーションを処理し、複数ページの求人リストを取得"""
        current_page = 1
        while current_page <= PAGINATION['max_pages']:
            print(f"ページ {current_page} を処理中...")
            job_links = self.search_jobs()
            if not job_links:
                print("求人リンクが見つかりませんでした。")
                break
            
            for job in job_links:
                self.get_job_details(job)
            
            current_page += 1
            from selenium.webdriver.common.by import By
            next_button = self.driver.find_element(By.CSS_SELECTOR, PAGINATION['next_button'])
            if next_button:
                next_button.click()
                time.sleep(2)  # ページ読み込み待機
            else:
                print("次ページボタンが見つかりませんでした。")
                break
            time.sleep(REQUEST_INTERVAL)

    def save_data(self):
        """取得したデータを指定形式で保存"""
        if not self.job_data:
            print("保存するデータがありません。")
            return
        
        df = pd.DataFrame(self.job_data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{OUTPUT['filename_prefix']}{timestamp}.{OUTPUT['format']}"
        output_path = os.path.join(OUTPUT['directory'], filename)
        
        if OUTPUT['format'] == 'csv':
            df.to_csv(output_path, encoding=OUTPUT['encoding'], index=False)
        elif OUTPUT['format'] == 'excel':
            df.to_excel(output_path, index=False)
        print(f"データを保存しました: {output_path}")

if __name__ == "__main__":
    scraper = HelloWorkScraper()
    scraper.handle_pagination()
    scraper.save_data()
