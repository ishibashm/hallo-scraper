import time
import sys
import os
import logging
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
import chromedriver_autoinstaller # To manage chromedriver automatically

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import BASE_URL, LIST_SELECTORS, PAGINATION, REQUEST_INTERVAL, USER_AGENT, OUTPUT

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
    Fetches a specific list page, extracts list data, saves it.
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

            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "form#ID_form_1")))
            logging.info("Search results page loaded (Page 1).")
            self.current_page = 1

            # Navigate to target page if target_page > 1
            while self.current_page < target_page:
                logging.info(f"Navigating from page {self.current_page} to {self.current_page + 1}")
                next_button_xpath = f"//input[@type='submit'][@name='fwListNaviBtnNext']"
                try:
                    next_button_element = wait.until(EC.presence_of_element_located((By.XPATH, next_button_xpath)))
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button_element)
                    time.sleep(0.3)
                    wait.until(EC.element_to_be_clickable(next_button_element))
                    self.driver.execute_script("arguments[0].click();", next_button_element)
                    self.current_page += 1

                    # Wait for the next page to load by waiting for the previous button
                    prev_button_xpath = f"//input[@type='submit'][@name='fwListNaviBtnPrev']"
                    wait.until(EC.presence_of_element_located((By.XPATH, prev_button_xpath)))
                    logging.info(f"Successfully navigated to page {self.current_page}")
                    time.sleep(REQUEST_INTERVAL) # Wait after page load

                except (NoSuchElementException, TimeoutException):
                    logging.error(f"Could not find or click 'Next' button when trying to reach page {target_page}. Stopping at page {self.current_page}.")
                    return False # Failed to reach target page
                except ElementClickInterceptedException:
                    logging.error(f"Clicking 'Next' button was intercepted on page {self.current_page}. Aborting.")
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
        # Check if driver is available
        if not self.driver:
             logging.error("Driver not available for parsing.")
             return False

        # --- Added: Save page source for debugging selectors ---
        page_source_path = os.path.join(OUTPUT['directory'], f"debug_page_source_page_{self.current_page}.html")
        try:
            with open(page_source_path, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            logging.debug(f"Saved page source for debugging to: {page_source_path}")
        except Exception as e:
            logging.error(f"Failed to save page source: {e}")
        # --- End Added ---

        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        page_list_data = []
        main_form = soup.select_one("form#ID_form_1")
        if not main_form:
             logging.warning("Could not find the main form#ID_form_1.")
             return False

        job_headers = main_form.select("tr.kyujin_head")
        logging.info(f"Found {len(job_headers)} job header rows (tr.kyujin_head).")

        if not job_headers and "検索結果はありませんでした" not in self.driver.page_source:
             logging.warning("No job header rows found.")
             logging.warning(self.driver.page_source[:2000])
             return False

        for i, header in enumerate(job_headers):
            job_data = {}
            logging.debug(f"--- Processing Job {i+1} ---")

            # --- Parse Header Info ---
            try:
                job_title_el = header.select_one(LIST_SELECTORS['job_title'])
                job_data['職種'] = job_title_el.text.strip() if job_title_el else ''
                logging.debug(f"  職種: {job_data['職種']}")

                # Reception/Deadline date are in the *next* sibling of the header
                date_row = header.find_next_sibling('tr')
                if date_row:
                    reception_date_el = date_row.select_one(LIST_SELECTORS['reception_date'])
                    job_data['受付年月日'] = reception_date_el.text.strip() if reception_date_el else ''
                    logging.debug(f"  受付年月日: {job_data['受付年月日']}")
                    deadline_date_el = date_row.select_one(LIST_SELECTORS['deadline_date'])
                    job_data['紹介期限日'] = deadline_date_el.text.strip() if deadline_date_el else ''
                    logging.debug(f"  紹介期限日: {job_data['紹介期限日']}")
                else:
                     logging.warning(f"Could not find date row for Job {i+1}")
                     job_data['受付年月日'] = ''
                     job_data['紹介期限日'] = ''

            except Exception as e:
                logging.warning(f"Error parsing header/date data for Job {i+1}: {e}")
                # Ensure keys exist even if parsing fails
                job_data.setdefault('職種', '')
                job_data.setdefault('受付年月日', '')
                job_data.setdefault('紹介期限日', '')

            # --- Parse Body Info ---
            # The actual body is the sibling *after* the date row
            body = date_row.find_next_sibling('tr', class_='kyujin_body') if date_row else None

            if body:
                logging.debug(f"  Found body row (tr.kyujin_body) for Job {i+1}.")
                # Iterate through selectors defined for the body
                for key, selector in LIST_SELECTORS.items():
                    # Skip header items and reference items
                    if key in ['job_title', 'reception_date', 'deadline_date'] or key.endswith('_ref'):
                        continue
                    try:
                        element = body.select_one(selector)
                        value = ''
                        if element:
                            if key == 'job_description':
                                value = ' '.join(element.stripped_strings)
                                logging.debug(f"    Parsed '{key}' (stripped): '{value[:50]}...' using selector '{selector}'")
                            elif key == 'wage': # Special handling for wage range which might have multiple divs
                                value = element.text.strip() # Get the primary wage range
                                logging.debug(f"    Parsed '{key}': '{value}' using selector '{selector}'")
                            elif key.startswith('work_hours_'): # Handle potentially missing work hour slots
                                # Check if the parent .flex exists before getting the div text
                                parent_flex = body.select_one(selector.rsplit(' > div', 1)[0]) # Get selector for the parent .flex
                                if parent_flex:
                                     hour_element = parent_flex.select_one('div')
                                     if hour_element:
                                          value = hour_element.text.strip()
                                          logging.debug(f"    Parsed '{key}': '{value}' using selector '{selector}'")
                                     else:
                                          logging.debug(f"    Work hour div not found within flex for '{key}' using selector '{selector}'")
                                else:
                                     logging.debug(f"    Work hour flex container not found for '{key}' using selector '{selector.rsplit(' > div', 1)[0]}'")
                            else:
                                value = element.text.strip()
                                logging.debug(f"    Parsed '{key}': '{value}' using selector '{selector}'")
                        else:
                            logging.debug(f"    Element for '{key}' not found using selector '{selector}'")

                        # Store the value, handle renamed keys if necessary (though not strictly needed with new selectors)
                        clean_key = key.replace('_text', '').replace('_details', '') # Basic cleaning, might need refinement
                        if key == "job_number_text": # Rename job_number_text to job_number
                            clean_key = "job_number"
                        job_data[clean_key] = value
                    except Exception as e:
                         logging.warning(f"Error parsing body field '{key}' for Job {i+1} with selector '{selector}': {e}")
                         clean_key = key.replace('_text', '').replace('_details', '')
                         if key == "job_number_text": clean_key = "job_number"
                         job_data[clean_key] = '' # Ensure key exists

                # --- Parse Items After Body (Special Notes, Positions) ---
                # Notes are in the next tr after body, inside div.kodawari
                notes_row = body.find_next_sibling('tr')
                if notes_row:
                    notes_elements = notes_row.select("div.kodawari span.nes_label")
                    job_data['special_notes_labels'] = ', '.join([label.text.strip() for label in notes_elements])
                    logging.debug(f"  Parsed special_notes_labels: {job_data['special_notes_labels']}")
                else:
                    logging.warning(f"Could not find notes row for Job {i+1}")
                    job_data['special_notes_labels'] = ''

                # Positions are in the tr after notes_row
                positions_row = notes_row.find_next_sibling('tr') if notes_row else None
                if positions_row:
                     # Corrected selector based on HTML structure provided in debug output
                     positions_element = positions_row.select_one("div.fs13.ml01")
                     job_data['number_of_positions'] = positions_element.text.strip() if positions_element else ''
                     logging.debug(f"  Parsed number_of_positions: {job_data['number_of_positions']}")
                else:
                     logging.warning(f"Could not find positions row for Job {i+1}")
                     job_data['number_of_positions'] = ''

                # --- Split Job Number ---
                if job_data.get('job_number') and '-' in job_data['job_number']:
                     try:
                         kSNoJo, kSNoGe = job_data['job_number'].split('-', 1)
                         job_data['kSNoJo'] = kSNoJo
                         job_data['kSNoGe'] = kSNoGe
                     except ValueError:
                         logging.warning(f"Could not split job number '{job_data['job_number']}' for Job {i+1}")

                page_list_data.append(job_data)
            else:
                logging.warning(f"Could not find body row (tr.kyujin_body) for Job {i+1}, header title: {job_data.get('職種')}")

        logging.info(f"Successfully parsed {len(page_list_data)} jobs' list data from page {self.current_page}.")
        self.list_data = page_list_data
        return bool(page_list_data)

    def save_list_data(self):
        """Saves the collected list data for the current page to a CSV file."""
        if not self.list_data:
            logging.warning("No list data collected to save.")
            return None
        try:
            df = pd.DataFrame(self.list_data)
            timestamp = datetime.now().strftime("%Y%m%d")
            pref_identifier = self.prefecture_code
            filename = f"{OUTPUT['filename_prefix']}list_page_{self.current_page}_{pref_identifier}_{timestamp}.{OUTPUT['format']}"
            output_dir = OUTPUT['directory']
            output_path = os.path.join(output_dir, filename)
            os.makedirs(output_dir, exist_ok=True)
            df.to_csv(output_path, encoding=OUTPUT['encoding'], index=False)
            logging.info(f"List data for page {self.current_page} successfully saved to: {output_path}")
            return output_path
        except Exception as e:
            logging.error(f"Failed to save list data: {e}")
            return None

    def check_next_page_exists(self):
        """Checks if a next page button exists on the current page."""
        if not self.driver:
            return False
        try:
            self.driver.find_element(By.CSS_SELECTOR, PAGINATION['next_button_selector'])
            logging.info("Next page button found.")
            return True
        except NoSuchElementException:
            logging.info("No next page button found.")
            return False

    def run_scraper_for_page(self, page_num=1):
        """Navigates to a specific page, parses list data, and saves it."""
        if not self.search_and_navigate(target_page=page_num):
            logging.error(f"Failed to navigate to page {page_num}.")
            self.close_driver()
            return None, False # No file saved, next page status unknown

        # Check for error page after navigation
        # Added small delay to ensure page source is updated after navigation
        time.sleep(0.5)
        if "システムエラー" in self.driver.page_source or "システムの混雑" in self.driver.page_source:
            logging.error(f"Received system error page on page {self.current_page}.")
            self.close_driver()
            return None, False

        logging.info(f"--- Processing Page {self.current_page} ---")
        found_data = self.parse_list_page_data()
        saved_filepath = None
        if found_data:
            saved_filepath = self.save_list_data()
        else:
            logging.warning(f"No job data found on page {self.current_page}.")

        next_page_exists = self.check_next_page_exists()

        self.close_driver() # Close driver after processing the target page
        return saved_filepath, next_page_exists

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
    # Argument 1: Prefecture Code (optional, default '26')
    # Argument 2: Target Page Number (optional, default 1)
    # Argument 3: Job Category Code (optional, default '1') - 1:一般, 2:新卒/既卒, 3:季節, 4:出稼ぎ, 5:障害者
    pref_code = "26" # Default Kyoto
    target_page_num = 1 # Default Page 1
    job_cat_code = "1" # Default 一般求人
    valid_job_cat_codes = ["1", "2", "3", "4", "5"]

    args = sys.argv[1:] # Get arguments excluding script name

    # More robust argument parsing
    if len(args) > 0:
        # Check first argument (Prefecture Code or Page Number)
        try:
            # Try interpreting as Prefecture Code
            code_val = int(args[0])
            if 1 <= code_val <= 47 or code_val == 59:
                pref_code = args[0]
                logging.info(f"Using prefecture code from argument 1: {pref_code}")
                # Check second argument (Page Number or Job Category Code)
                if len(args) > 1:
                    try:
                        # Try interpreting as Page Number
                        page_val = int(args[1])
                        target_page_num = max(1, page_val)
                        logging.info(f"Using target page number from argument 2: {target_page_num}")
                        # Check third argument (Job Category Code)
                        if len(args) > 2:
                            if args[2] in valid_job_cat_codes:
                                job_cat_code = args[2]
                                logging.info(f"Using job category code from argument 3: {job_cat_code}")
                            else:
                                logging.warning(f"Invalid job category code '{args[2]}' in argument 3. Using default '{job_cat_code}'.")
                    except ValueError:
                        # If second arg is not page number, try interpreting as Job Category Code
                        if args[1] in valid_job_cat_codes:
                            job_cat_code = args[1]
                            logging.info(f"Using job category code from argument 2 (page defaulted to 1): {job_cat_code}")
                        else:
                            logging.warning(f"Invalid argument '{args[1]}' for page number or job category. Using defaults.")
            else:
                # If first arg is integer but not valid pref code, assume it's Page Number
                raise ValueError("Not a valid prefecture code")
        except ValueError:
            # If first arg is not integer or not valid pref code, assume it's Page Number
            try:
                page_val = int(args[0])
                target_page_num = max(1, page_val)
                logging.info(f"Using target page number from argument 1 (prefecture defaulted to {pref_code}): {target_page_num}")
                # Check second argument (Job Category Code)
                if len(args) > 1:
                    if args[1] in valid_job_cat_codes:
                        job_cat_code = args[1]
                        logging.info(f"Using job category code from argument 2: {job_cat_code}")
                    else:
                        logging.warning(f"Invalid job category code '{args[1]}' in argument 2. Using default '{job_cat_code}'.")
            except ValueError:
                logging.warning(f"Invalid first argument '{args[0]}'. Using all defaults.")

    # Instantiate scraper with parsed codes
    scraper = HelloWorkScraper(prefecture_code=pref_code, job_category_code=job_cat_code)
    saved_file, has_next_page = scraper.run_scraper_for_page(page_num=target_page_num)

    # Output results for the AI/User
    if saved_file:
        print(f"SUCCESS: Saved list data for page {target_page_num} to {saved_file}")
        if has_next_page:
            print(f"NEXT_PAGE_AVAILABLE: True (Page {target_page_num + 1} likely exists)")
        else:
            print(f"NEXT_PAGE_AVAILABLE: False (Page {target_page_num} might be the last page)")
    else:
        print(f"FAILURE: Could not save list data for page {target_page_num}.")
        # Still report if next page might exist based on check before closing
        if has_next_page:
            print(f"NEXT_PAGE_AVAILABLE: True (Page {target_page_num + 1} likely exists)")
        else:
            print(f"NEXT_PAGE_AVAILABLE: False (Page {target_page_num} might be the last page)")
