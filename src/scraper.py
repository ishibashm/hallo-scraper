import time
import sys
import os
import logging
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin # Import urljoin

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
import argparse # For better argument parsing
import chromedriver_autoinstaller # To manage chromedriver automatically

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import BASE_URL, LIST_SELECTORS, PAGINATION, REQUEST_INTERVAL, USER_AGENT, OUTPUT
# --- Import DetailScraper ---
try:
    from src.detail_scraper import DetailScraper
except ImportError:
    # This might happen if detail_scraper.py hasn't been created yet, handle gracefully
    DetailScraper = None
    logging.warning("Could not import DetailScraper. Detail fetching will be unavailable.")

# Logging setup
# --- Changed log level to DEBUG ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# --- Keep other loggers at WARNING to reduce noise ---
logging.getLogger('selenium.webdriver.remote.remote_connection').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('chromedriver_autoinstaller').setLevel(logging.WARNING) # Suppress installer info messages if already installed

class HelloWorkScraper:
    """
    Scrapes job postings from HelloWork website using Selenium.
    Fetches job list pages and optionally triggers detail scraping.
    """
    # --- Added job_category_code parameter, default is '1' (General) ---
    def __init__(self, prefecture_code="26", job_category_code="1"):
        self.list_data = []
        self.prefecture_code = prefecture_code
        self.job_category_code = job_category_code # Store job category code
        self.driver = None # Initialize driver as None
        self.current_page = 1
        logging.info(f"Scraper initialized for prefecture code: {self.prefecture_code}, job category: {self.job_category_code}")

    def _setup_driver(self):
        """Sets up the Selenium WebDriver if not already setup."""
        if self.driver:
            return True # Already setup
        try:
            chromedriver_path = chromedriver_autoinstaller.install()
            options = ChromeOptions()
            options.add_argument(f"user-agent={USER_AGENT}")
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            options.add_argument('--log-level=3')

            service = ChromeService(executable_path=chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
            logging.info(f"WebDriver setup successful using chromedriver at: {chromedriver_path}")
            return True
        except Exception as e:
            logging.error(f"WebDriver setup failed: {e}")
            self.driver = None
            return False

    def search_and_navigate(self, target_page=1):
        """Performs initial search and navigates to the target page."""
        if not self._setup_driver():
             return False # Driver setup failed

        initial_url = BASE_URL + "?action=initDisp&screenId=GECA110010"
        logging.info(f"Navigating to initial search page: {initial_url}")
        try:
            self.driver.get(initial_url)
            wait = WebDriverWait(self.driver, 20)

            pref_dropdown = wait.until(EC.presence_of_element_located((By.ID, "ID_tDFK1CmbBox")))
            select = Select(pref_dropdown)
            select.select_by_value(self.prefecture_code)
            logging.info(f"Selected prefecture code: {self.prefecture_code}")

            # --- Modified: Select job category radio button with improved click logic ---
            try:
                job_category_radio_xpath = f"//input[@name='kjKbnRadioBtn'][@value='{self.job_category_code}']"
                job_category_radio = wait.until(EC.presence_of_element_located((By.XPATH, job_category_radio_xpath)))
                # Ensure the radio button is visible and clickable, try direct click first
                self.driver.execute_script("arguments[0].scrollIntoViewIfNeeded(true);", job_category_radio)
                time.sleep(0.3) # Delay after scroll
                wait.until(EC.element_to_be_clickable((By.XPATH, job_category_radio_xpath)))
                try:
                    job_category_radio.click()
                    logging.debug("Successfully clicked radio button directly.")
                except ElementClickInterceptedException:
                    logging.warning("Direct click intercepted, attempting JavaScript click for radio button.")
                    self.driver.execute_script("arguments[0].click();", job_category_radio)
                    logging.debug("Successfully clicked radio button via JavaScript.")

                logging.info(f"Selected job category radio button (value='{self.job_category_code}').")
            except (NoSuchElementException, TimeoutException):
                logging.error(f"Could not find or select the job category radio button (value='{self.job_category_code}'). Valid codes: 1(一般), 2(新卒/既卒), 3(季節), 4(出稼ぎ), 5(障害者). Halting.")
                return False
            except ElementClickInterceptedException:
                 logging.error(f"Clicking job category radio button (value='{self.job_category_code}') was intercepted even with JS fallback. Halting.")
                 return False
            except Exception as e:
                logging.error(f"Unexpected error during job category selection: {e}")
                return False
            # --- End Modification ---

            # --- Ensure search button click is outside the radio button try/except ---
            search_button = wait.until(EC.element_to_be_clickable((By.ID, "ID_searchBtn")))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_button)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", search_button)
            logging.info("Clicked search button.")

            # Wait for a known element on the results page
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "form#ID_form_1, #ID_noItem"))) # Wait for main form or "no results" message
            logging.info("Search results page loaded (Page 1).")
            self.current_page = 1

            # Navigate to target page if target_page > 1
            while self.current_page < target_page:
                logging.info(f"Navigating from page {self.current_page} to {self.current_page + 1}")
                next_button_xpath = f"//input[@type='submit'][@name='fwListNaviBtnNext']"
                try:
                    next_button_element = wait.until(EC.element_to_be_clickable((By.XPATH, next_button_xpath)))
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button_element)
                    time.sleep(0.3)
                    # Use JS click for reliability
                    self.driver.execute_script("arguments[0].click();", next_button_element)
                    self.current_page += 1

                    # Wait for the next page to load by waiting for the previous button OR main form/no results
                    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='submit'][@name='fwListNaviBtnPrev'] | //form[@id='ID_form_1'] | //div[@id='ID_noItem']")))
                    logging.info(f"Successfully navigated to page {self.current_page}")
                    time.sleep(REQUEST_INTERVAL) # Wait after page load

                except (NoSuchElementException, TimeoutException):
                    logging.error(f"Could not find or click 'Next' button when trying to reach page {target_page}. Stopping at page {self.current_page}.")
                    return False # Failed to reach target page
                except ElementClickInterceptedException:
                    logging.error(f"Clicking 'Next' button was intercepted on page {self.current_page - 1}. Aborting.")
                    return False
                except Exception as e:
                    logging.error(f"An error occurred during pagination to page {self.current_page + 1}: {e}")
                    return False

            logging.info(f"Successfully reached target page {self.current_page}.")
            return True # Reached target page

        except (NoSuchElementException, TimeoutException) as e:
            logging.error(f"Error during Selenium search/navigation: {e}")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred during search/navigation: {e}")
            return False

    def parse_list_page_data(self):
        """Parses the CURRENT job list page in Selenium to extract visible data."""
        if not self.driver:
             logging.error("Driver not available for parsing.")
             return False

        page_source_path = os.path.join(OUTPUT['directory'], f"debug_page_source_page_{self.current_page}.html")
        try:
            with open(page_source_path, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            logging.debug(f"Saved page source for debugging to: {page_source_path}")
        except Exception as e:
            logging.error(f"Failed to save page source: {e}")

        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        page_list_data = []

        # --- MODIFIED: Search the entire document for job items first ---
        job_items = soup.select("tr.kyujin_head")
        logging.info(f"Found {len(job_items)} job items (tr.kyujin_head) in the entire document on page {self.current_page}.")
        # --- END MODIFICATION ---

        # Optional: Check if the main form exists as a basic validation, but don't necessarily fail if items were found elsewhere
        main_form = soup.select_one("form#ID_form_1")
        if not main_form:
             logging.warning(f"Main form (form#ID_form_1) not found, but proceeding as job items might exist outside it.")

        if not job_items:
            if soup.find(id='ID_noItem') or "検索結果はありませんでした" in self.driver.page_source:
                logging.info(f"No job results found on page {self.current_page}.")
            else:
                logging.warning(f"No job items (tr.kyujin_head) found anywhere on page {self.current_page}.")
            self.list_data = [] # Ensure list_data is empty
            return True # No items is a valid parse state, or "no results" page

        for i, header in enumerate(job_items):
            job_data = {}
            logging.debug(f"--- Processing Job {i+1} on page {self.current_page} ---")

            # --- Find related rows (relative to the current header) ---
            date_row = header.find_next_sibling('tr')
            body_row = date_row.find_next_sibling('tr', class_='kyujin_body') if date_row else None
            notes_row = None
            positions_row = None
            footer_row = None

            # Determine notes, positions, footer based on structure after body_row
            current_row = body_row
            if current_row:
                potential_next = current_row.find_next_sibling('tr')
                while potential_next:
                    if 'kyujin_foot' in potential_next.get('class', []):
                        footer_row = potential_next
                        break # Found footer, stop searching siblings
                    elif potential_next.select_one("div.kodawari"):
                        notes_row = potential_next
                    # Check specifically for the structure containing '求人数'
                    elif potential_next.select_one("div.fs13.ml01") and '求人数' in potential_next.text:
                        positions_row = potential_next

                    current_row = potential_next
                    potential_next = current_row.find_next_sibling('tr')

            # --- Parse Header Info ---
            try:
                job_title_el = header.select_one(LIST_SELECTORS['job_title'])
                job_data['職種'] = job_title_el.text.strip() if job_title_el else ''
                if date_row:
                    reception_date_el = date_row.select_one(LIST_SELECTORS['reception_date'])
                    job_data['受付年月日'] = reception_date_el.text.strip() if reception_date_el else ''
                    deadline_date_el = date_row.select_one(LIST_SELECTORS['deadline_date'])
                    job_data['紹介期限日'] = deadline_date_el.text.strip() if deadline_date_el else ''
                else: job_data['受付年月日'], job_data['紹介期限日'] = '', ''
                logging.debug(f"  Header: {job_data['職種']}, {job_data['受付年月日']}, {job_data['紹介期限日']}")
            except Exception as e:
                logging.warning(f"Error parsing header/date for Job {i+1}: {e}")
                job_data.setdefault('職種', ''), job_data.setdefault('受付年月日', ''), job_data.setdefault('紹介期限日', '')

            # --- Parse Body Info ---
            if body_row:
                for key, selector in LIST_SELECTORS.items():
                    if key in ['job_title', 'reception_date', 'deadline_date', 'detail_link'] or key.endswith('_ref'):
                        continue
                    try:
                        element = body_row.select_one(selector)
                        value = ''
                        if element:
                            if key == 'job_description': value = ' '.join(element.stripped_strings)
                            else: value = element.text.strip()
                        clean_key = key.replace('_text', '').replace('_details', '')
                        if key == "job_number_text": clean_key = "job_number"
                        job_data[clean_key] = value
                        if value: logging.debug(f"    Body '{clean_key}': '{value[:50]}...'")
                    except Exception as e:
                        logging.warning(f"Error parsing body field '{key}': {e}")
                        clean_key = key.replace('_text', '').replace('_details', '')
                        if key == "job_number_text": clean_key = "job_number"
                        job_data[clean_key] = ''
            else: logging.warning(f"Could not find body row for Job {i+1}")

            # --- Parse Special Notes ---
            job_data['special_notes_labels'] = ''
            if notes_row:
                notes_elements = notes_row.select("div.kodawari span.nes_label")
                job_data['special_notes_labels'] = ', '.join([label.text.strip() for label in notes_elements])
                logging.debug(f"  Notes: {job_data['special_notes_labels']}")
            else: logging.debug(f"No notes row found for Job {i+1}")

            # --- Parse Number of Positions ---
            job_data['number_of_positions'] = ''
            if positions_row:
                positions_element = positions_row.select_one("div.fs13.ml01")
                if positions_element:
                    job_data['number_of_positions'] = positions_element.text.strip().replace('求人数：','').split('名')[0].strip() # Extract number
                    logging.debug(f"  Positions: {job_data['number_of_positions']}")
                else: # Fallback might not be needed if the selector is reliable
                     logging.debug("Positions element (div.fs13.ml01) not found in positions_row")
            else: logging.debug(f"No positions row found for Job {i+1}")

            # --- Split Job Number ---
            if job_data.get('job_number') and '-' in job_data['job_number']:
                try:
                    kSNoJo, kSNoGe = job_data['job_number'].split('-', 1)
                    job_data['kSNoJo'] = kSNoJo
                    job_data['kSNoGe'] = kSNoGe
                except ValueError: logging.warning(f"Could not split job number '{job_data['job_number']}'")

            # --- Extract Detail Link ---
            job_data['detail_link_href'] = ''
            if footer_row:
                detail_link_element = footer_row.select_one(LIST_SELECTORS['detail_link'])
                if detail_link_element and detail_link_element.has_attr('href'):
                    relative_url = detail_link_element['href']
                    base_scrape_url = self.driver.current_url if self.driver else BASE_URL
                    job_data['detail_link_href'] = urljoin(base_scrape_url, relative_url)
                    logging.debug(f"  Detail Link: {job_data['detail_link_href']}")
                else: logging.warning(f"Could not find detail link href in footer for Job {i+1}")
            else: logging.warning(f"Could not find footer row for Job {i+1}")

            page_list_data.append(job_data)

        self.list_data = page_list_data
        logging.info(f"Finished parsing page {self.current_page}. Found {len(page_list_data)} jobs.")
        return True # Indicate parsing attempt was made

    def save_list_data(self):
        """Saves the collected list data for the current page to a CSV file."""
        if not self.list_data:
            logging.info(f"No list data to save for page {self.current_page}.")
            return None # Nothing to save
        try:
            df = pd.DataFrame(self.list_data)
            timestamp = datetime.now().strftime("%Y%m%d")
            pref_identifier = self.prefecture_code
            output_dir = OUTPUT['directory']
            os.makedirs(output_dir, exist_ok=True)

            base_filename = f"{OUTPUT['filename_prefix']}list_page_{self.current_page}_{pref_identifier}_{timestamp}"
            saved_paths = []

            # --- CSV出力 ---
            csv_filename = f"{base_filename}.csv"
            csv_output_path = os.path.join(output_dir, csv_filename)
            csv_encoding = OUTPUT.get('encoding', 'utf-8-sig') # CSV用のエンコーディング取得
            try:
                df.to_csv(csv_output_path, encoding=csv_encoding, index=False)
                logging.info(f"List data for page {self.current_page} successfully saved as CSV to: {csv_output_path}")
                saved_paths.append(csv_output_path)
            except Exception as e:
                logging.error(f"Failed to save list data as CSV for page {self.current_page}: {e}")

            # --- JSON出力 ---
            json_filename = f"{base_filename}.json" # 拡張子を .json に変更
            json_output_path = os.path.join(output_dir, json_filename)
            # JSONは通常 utf-8。設定にあればそれを使うが、なければutf-8。
            json_encoding = OUTPUT.get('encoding_json', 'utf-8')
            try:
                # orient='records' でレコードの配列を生成, lines=True を削除
                # indent=4 を追加して可読性を向上
                json_string = df.to_json(orient='records', force_ascii=False, indent=4)
                with open(json_output_path, 'w', encoding=json_encoding) as f:
                    f.write(json_string)
                logging.info(f"List data for page {self.current_page} successfully saved as JSON to: {json_output_path}")
                saved_paths.append(json_output_path)
            except Exception as e:
                logging.error(f"Failed to save list data as JSON for page {self.current_page}: {e}")


            # どちらか一方でも成功していれば、最初の成功パスを返す（互換性のため）
            # 両方失敗した場合は None を返す
            return saved_paths[0] if saved_paths else None
        except Exception as e:
            logging.error(f"Failed to save list data for page {self.current_page}: {e}")
            return None

    def check_next_page_exists(self):
        """Checks if a next page button exists and is enabled on the current page."""
        if not self.driver: return False
        try:
            next_button = self.driver.find_element(By.XPATH, "//input[@type='submit'][@name='fwListNaviBtnNext']")
            is_disabled = next_button.get_attribute('disabled')
            if is_disabled:
                 logging.info("Next page button found but is disabled.")
                 return False
            logging.info("Next page button found and enabled.")
            return True
        except NoSuchElementException:
            logging.info("No next page button found.")
            return False

    def run_scraper_for_page(self, page_num=1):
        """Navigates to a specific page, parses list data, and saves it. (Less used now)"""
        if not self.search_and_navigate(target_page=page_num):
            logging.error(f"Failed to navigate to page {page_num}.")
            self.close_driver()
            return None, False

        time.sleep(0.5)
        if "システムエラー" in self.driver.page_source or "システムの混雑" in self.driver.page_source:
            logging.error(f"Received system error page on page {self.current_page}.")
            self.close_driver()
            return None, False

        logging.info(f"--- Processing Single Page {self.current_page} ---")
        parse_successful = self.parse_list_page_data()
        saved_filepath = None
        if parse_successful and self.list_data:
            saved_filepath = self.save_list_data()
        elif not parse_successful:
             logging.warning(f"Failed to parse page {self.current_page}.")
        else: # parse successful but no data
             logging.info(f"No job listings found on page {self.current_page}.")

        next_page_exists = self.check_next_page_exists()
        self.close_driver() # Close driver when running for single page
        return saved_filepath, next_page_exists

    def run_pagination_scrape(self, start_page=1, prompt_interval=5):
        """
        Scrapes job list data starting from start_page, iterating through pages
        until no 'Next' button is found or user chooses to stop.

        Args:
            start_page (int): The page number to start scraping from.
            prompt_interval (int): Ask user to continue every N pages. 0 means never ask.
        """
        total_saved_files = []
        pages_processed_since_prompt = 0

        if not self.search_and_navigate(target_page=start_page):
            logging.error(f"Failed to navigate to the starting page {start_page}. Aborting pagination.")
            self.close_driver()
            return total_saved_files

        while True:
            logging.info(f"--- Processing Page {self.current_page} ---")

            time.sleep(0.5)
            if "システムエラー" in self.driver.page_source or "システムの混雑" in self.driver.page_source:
                logging.error(f"Received system error page on page {self.current_page}. Stopping pagination.")
                break

            parse_successful = self.parse_list_page_data()
            saved_filepath = None
            if parse_successful and self.list_data: # Only save if parse was ok AND data exists
                saved_filepath = self.save_list_data()
                if saved_filepath:
                    total_saved_files.append(saved_filepath)
                    pages_processed_since_prompt += 1
                else:
                    logging.error(f"Failed to save data for page {self.current_page}. Stopping.")
                    break
            elif parse_successful and not self.list_data:
                 logging.info(f"No job listings found on page {self.current_page}.")
                 # Still increment counter if user wants to be prompted even on empty pages
                 pages_processed_since_prompt += 1
            else: # parse_successful was False
                 logging.warning(f"Failed to parse page {self.current_page}. Stopping pagination for safety.")
                 break

            # --- Prompt user to continue ---
            if prompt_interval > 0 and pages_processed_since_prompt >= prompt_interval:
                try:
                    print("-" * 30)
                    user_input = input(f"Processed {pages_processed_since_prompt} pages (up to page {self.current_page}). Continue? (y/n): ").lower().strip()
                    print("-" * 30)
                    if user_input != 'y':
                        logging.info("User chose to stop pagination.")
                        break
                    else:
                        pages_processed_since_prompt = 0 # Reset counter
                except EOFError:
                    logging.warning("Could not get user input (EOFError). Continuing pagination automatically.")
                    pages_processed_since_prompt = 0 # Reset to avoid repeated warnings

            # Check if next page exists
            if not self.check_next_page_exists():
                logging.info(f"No 'Next' button found or enabled on page {self.current_page}. Pagination finished.")
                break

            # Navigate to the next page
            logging.info(f"Navigating from page {self.current_page} to {self.current_page + 1}")
            next_button_xpath = "//input[@type='submit'][@name='fwListNaviBtnNext']"
            wait = WebDriverWait(self.driver, 20)
            try:
                next_button_element = wait.until(EC.element_to_be_clickable((By.XPATH, next_button_xpath)))
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button_element)
                time.sleep(0.3)
                self.driver.execute_script("arguments[0].click();", next_button_element)
                self.current_page += 1

                # Wait for next page load indicator
                wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='submit'][@name='fwListNaviBtnPrev'] | //form[@id='ID_form_1'] | //div[@id='ID_noItem']")))
                logging.info(f"Successfully navigated to page {self.current_page}")
                time.sleep(REQUEST_INTERVAL)

            except (NoSuchElementException, TimeoutException):
                logging.error(f"Could not find or click 'Next' button on page {self.current_page -1}. Stopping.")
                break
            except ElementClickInterceptedException:
                logging.error(f"'Next' button click intercepted on page {self.current_page - 1}. Aborting.")
                break
            except Exception as e:
                logging.error(f"An error occurred during pagination navigation from page {self.current_page - 1}: {e}")
                break

        self.close_driver()
        logging.info(f"Pagination scrape complete. Saved data for {len(total_saved_files)} pages.")
        return total_saved_files

    def close_driver(self):
        """Closes the Selenium WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                logging.info("WebDriver closed.")
            except Exception as e:
                logging.error(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None

# Main execution block
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape job listings from HelloWork, optionally fetching details.")
    parser.add_argument("prefecture_code", nargs='?', default="26", help="Prefecture code (e.g., 26 for Kyoto). Default: 26")
    parser.add_argument("start_page", nargs='?', type=int, default=1, help="Starting page number for pagination. Default: 1")
    parser.add_argument("job_category_code", nargs='?', default="1", choices=["1", "2", "3", "4", "5"], help="Job category code (1:General, 2:Graduates, 3:Seasonal, 4:Migrant, 5:Disabled). Default: 1")
    parser.add_argument("--fetch-details", action="store_true", help="Fetch detail pages for jobs found in the list scrape.")
    parser.add_argument("--prompt-interval", type=int, default=5, help="Ask user to continue every N pages (0 to disable). Default: 5")

    args = parser.parse_args()

    pref_code = args.prefecture_code
    start_page_num = max(1, args.start_page) # Ensure start_page >= 1
    job_cat_code = args.job_category_code
    fetch_details_flag = args.fetch_details
    prompt_interval_val = max(0, args.prompt_interval) # Ensure interval >= 0

    logging.info(f"Starting list scrape for prefecture {pref_code}, category {job_cat_code}, starting from page {start_page_num}")
    if prompt_interval_val > 0:
        logging.info(f"Will prompt user to continue every {prompt_interval_val} pages.")

    list_scraper = HelloWorkScraper(prefecture_code=pref_code, job_category_code=job_cat_code)
    saved_list_files = list_scraper.run_pagination_scrape(start_page=start_page_num, prompt_interval=prompt_interval_val)

    if saved_list_files:
        print(f"SUCCESS: List scrape {'finished' if prompt_interval_val == 0 else 'stopped/finished'}. Saved data for {len(saved_list_files)} pages.")
        for i, f in enumerate(saved_list_files):
            actual_page_num = start_page_num + i
            print(f"  - List Page {actual_page_num}: {f}")

        if fetch_details_flag:
            if DetailScraper is None:
                logging.error("DetailScraper class not available. Cannot fetch details.")
                print("ERROR: Detail fetching requested but DetailScraper could not be imported.")
            else:
                logging.info("--- Starting Detail Scrape Phase ---")
                successful_detail_files_count = 0
                for list_csv_file in saved_list_files:
                    if not os.path.exists(list_csv_file):
                         logging.warning(f"List CSV file {list_csv_file} not found. Skipping detail processing for this file.")
                         continue
                    logging.info(f"Processing details from list file: {list_csv_file}")
                    try:
                        detail_scraper = DetailScraper()
                        detail_scraper.run_detail_scrape_from_csv(list_csv_file)
                        successful_detail_files_count += 1
                    except Exception as e:
                        logging.error(f"An unexpected error occurred processing details for {list_csv_file}: {e}")
                        print(f"ERROR: Failed to process details for {list_csv_file}. See logs.")

                logging.info("--- Detail Scrape Phase Finished ---")
                if successful_detail_files_count > 0:
                     print(f"Detail scraping initiated for {successful_detail_files_count} list file(s). Check 'output' directory for detail CSVs and logs for details.")
                elif len(saved_list_files) > 0:
                     print("Detail scraping process finished, but encountered issues or no details were processed. Check logs.")
        else:
            print("Skipping detail fetching as --fetch-details flag was not provided.")
    else:
        print(f"FAILURE: No list data files were saved during pagination starting from page {start_page_num}.")
