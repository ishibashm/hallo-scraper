import time
import sys
import os
import logging
import json
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Selenium imports (必要なものを追加)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import chromedriver_autoinstaller

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import BASE_URL, DETAIL_SELECTORS, REQUEST_INTERVAL, USER_AGENT, OUTPUT # BASE_URLも使う可能性あり

# Logging setup (scraper.pyと同様の設定を推奨)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('selenium.webdriver.remote.remote_connection').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('chromedriver_autoinstaller').setLevel(logging.WARNING)

class DetailScraper:
    """
    Scrapes job detail pages from HelloWork based on links provided from the list scrape.
    """
    def __init__(self):
        self.driver = None
        logging.info("DetailScraper initialized.")

    def _setup_driver(self):
        """Sets up the Selenium WebDriver (similar to HelloWorkScraper)."""
        if self.driver:
            return True
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
            logging.info(f"DetailScraper WebDriver setup successful using: {chromedriver_path}")
            return True
        except Exception as e:
            logging.error(f"DetailScraper WebDriver setup failed: {e}")
            self.driver = None
            return False

    def fetch_detail_page(self, detail_url):
        """Navigates to the detail page URL and returns the page source."""
        if not self.driver:
            logging.error("Driver not set up. Call _setup_driver first.")
            return None

        full_url = urljoin(BASE_URL, detail_url) # Ensure it's a full URL
        logging.info(f"Fetching detail page: {full_url}")
        try:
            self.driver.get(full_url)
            # Wait for a key element specific to the detail page to ensure it loaded
            # Example: Wait for the job number element
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, DETAIL_SELECTORS.get("job_number", "#ID_kjNo")))) # Use a known selector
            logging.info(f"Successfully loaded detail page.")
            time.sleep(REQUEST_INTERVAL) # Respect request interval
            return self.driver.page_source
        except TimeoutException:
            logging.error(f"Timeout waiting for detail page elements to load: {full_url}")
            return None
        except Exception as e:
            logging.error(f"Error fetching detail page {full_url}: {e}")
            return None

    def parse_detail_page(self, page_source, job_number):
        """Parses the HTML source of a detail page using DETAIL_SELECTORS."""
        if not page_source:
            return None

        soup = BeautifulSoup(page_source, 'lxml')
        detail_data = {'job_number_ref': job_number} # Include reference job number

        logging.debug(f"Parsing details for job number: {job_number}")
        for key, selector in DETAIL_SELECTORS.items():
            try:
                element = soup.select_one(selector)
                value = ''
                if element:
                    if key == 'office_homepage': # Special handling for links
                        value = element.get('href', '').strip()
                    else:
                        # Extract text, potentially handling multiple lines/stripped strings
                        value = ' '.join(element.stripped_strings) if element.stripped_strings else element.text.strip()
                    logging.debug(f"  Parsed '{key}': '{value[:100]}...' using selector '{selector}'")
                else:
                    logging.debug(f"  Element for '{key}' not found using selector '{selector}'")
                detail_data[key] = value
            except Exception as e:
                logging.warning(f"Error parsing detail field '{key}' for job {job_number} with selector '{selector}': {e}")
                detail_data[key] = '' # Ensure key exists

        return detail_data

    def save_detail_data(self, detail_data_list, output_filename="job_details.csv"):
        """Saves the collected detail data to a CSV file."""
        if not detail_data_list:
            logging.warning("No detail data collected to save.")
            return None
        try:
            df = pd.DataFrame(detail_data_list)
            output_dir = OUTPUT['directory']
            output_path = os.path.join(output_dir, output_filename)
            os.makedirs(output_dir, exist_ok=True)
            # Append mode if file exists? Or overwrite? Overwrite for simplicity now.
            df.to_csv(output_path, encoding=OUTPUT['encoding'], index=False)
            logging.info(f"Detail data successfully saved to: {output_path}")
            return output_path
        except Exception as e:
            logging.error(f"Failed to save detail data: {e}")
            return None

    def run_detail_scrape_from_csv(self, list_csv_path):
        """
        Reads job numbers and detail links from the list CSV, scrapes details, and saves them.
        """
        all_details = []
        try:
            list_df = pd.read_csv(list_csv_path, encoding=OUTPUT.get('encoding', 'utf-8-sig'))
            logging.info(f"Read {len(list_df)} entries from list CSV: {list_csv_path}")
        except FileNotFoundError:
            logging.error(f"List CSV file not found: {list_csv_path}")
            return
        except Exception as e:
            logging.error(f"Error reading list CSV {list_csv_path}: {e}")
            return

        if 'job_number' not in list_df.columns or 'detail_link_href' not in list_df.columns:
            logging.error(f"CSV {list_csv_path} must contain 'job_number' and 'detail_link_href' columns.")
            return

        if not self._setup_driver():
            logging.error("Failed to set up WebDriver for detail scraping.")
            return

        for index, row in list_df.iterrows():
            job_num = row['job_number']
            detail_href = row['detail_link_href']

            if pd.isna(detail_href) or not detail_href:
                logging.warning(f"Skipping job {job_num} due to missing detail link.")
                continue

            logging.info(f"Processing detail page for job {job_num} ({index + 1}/{len(list_df)})")
            page_source = self.fetch_detail_page(detail_href)

            if page_source:
                detail_info = self.parse_detail_page(page_source, job_num)
                if detail_info:
                    all_details.append(detail_info)
            else:
                logging.warning(f"Failed to fetch or parse detail page for job {job_num}")
            
            # Optional: Add a small delay between detail page requests if needed beyond REQUEST_INTERVAL
            # time.sleep(1)

        self.close_driver()

        if all_details:
            # Construct a filename, perhaps based on the input CSV name
            base_name = os.path.basename(list_csv_path)
            detail_filename = base_name.replace("list_page", "details").replace(".csv", "_details.csv")
            self.save_detail_data(all_details, output_filename=detail_filename)
        else:
            logging.warning("No detail data was successfully scraped.")


    def close_driver(self):
        """Closes the Selenium WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                logging.info("DetailScraper WebDriver closed.")
            except Exception as e:
                logging.error(f"Error closing DetailScraper WebDriver: {e}")
            finally:
                self.driver = None

# Example usage (can be called from scraper.py or run standalone)
if __name__ == "__main__":
    # Example: Process details from a specific list CSV file
    # Provide the path to a list CSV as a command-line argument
    if len(sys.argv) > 1:
        input_csv_path = sys.argv[1]
        if os.path.exists(input_csv_path):
            logging.info(f"Starting detail scrape process for CSV: {input_csv_path}")
            detail_scraper = DetailScraper()
            detail_scraper.run_detail_scrape_from_csv(input_csv_path)
            print(f"Detail scraping process finished for {input_csv_path}.")
        else:
            print(f"Error: Input CSV file not found - {input_csv_path}")
            logging.error(f"Input CSV file not found: {input_csv_path}")
    else:
        print("Please provide the path to a job list CSV file as an argument.")
        print("Example: python src/detail_scraper.py output/hellowork_jobs_list_page_1_26_20250425.csv")
