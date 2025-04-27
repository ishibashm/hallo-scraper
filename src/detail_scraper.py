import argparse
import time
import sys
import os
import json # Add json import
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
            csv_output_path = os.path.join(output_dir, output_filename)
            json_output_path = os.path.splitext(csv_output_path)[0] + ".json" # Create JSON filename
            os.makedirs(output_dir, exist_ok=True)

            # --- Save to CSV (Append mode) ---
            try:
                csv_file_exists = os.path.exists(csv_output_path)
                write_mode = 'a' if csv_file_exists else 'w'
                write_header = not csv_file_exists

                df.to_csv(csv_output_path, mode=write_mode, header=write_header, encoding=OUTPUT.get('encoding', 'utf-8-sig'), index=False)

                if csv_file_exists:
                    logging.info(f"Appended {len(detail_data_list)} new records to CSV: {csv_output_path}")
                else:
                    logging.info(f"Detail data successfully saved (new CSV file) to: {csv_output_path}")
            except Exception as e:
                 logging.error(f"Failed to save detail data to CSV: {e}")
                 # Continue to try saving JSON even if CSV fails

            # --- Save to JSON (Overwrite mode) ---
            try:
                # Convert DataFrame records to list of dicts for JSON serialization
                # Important: Read the *entire* existing CSV if appending JSON, otherwise just save new data
                # For simplicity and debug purpose, let's overwrite JSON with *all* data currently in the CSV
                if os.path.exists(csv_output_path):
                     full_df_for_json = pd.read_csv(csv_output_path, encoding=OUTPUT.get('encoding', 'utf-8-sig'), dtype=str) # Read all as string for consistency
                     json_data_to_save = full_df_for_json.to_dict('records')
                else: # If CSV didn't exist before this run, just use the new data
                     json_data_to_save = df.to_dict('records')

                with open(json_output_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data_to_save, f, ensure_ascii=False, indent=4)
                logging.info(f"Detail data successfully saved/overwritten to JSON: {json_output_path}")
            except Exception as e:
                logging.error(f"Failed to save detail data to JSON: {e}")

            # Return the CSV path as the primary output path
            return csv_output_path
        except Exception as e:
            # Catch potential errors before saving attempts (e.g., DataFrame creation)
            logging.error(f"Failed during detail data preparation for saving: {e}")
            return None

    def run_detail_scrape_from_csv(self, list_csv_path, limit=None):
        """
        Reads job numbers and detail links from the list CSV, scrapes details,
        skips jobs already present in the output file, and appends new data.

        Args:
            list_csv_path (str): Path to the job list CSV file.
            limit (int, optional): Maximum number of new detail pages to scrape. Defaults to None (no limit).
        """
        all_details = []
        processed_count = 0
        skipped_count = 0
        existing_job_numbers = set()

        # --- Determine output filename and load existing job numbers ---
        base_name = os.path.basename(list_csv_path)
        detail_filename_parts = os.path.splitext(base_name.replace("list_page", "details"))
        output_filename = f"{detail_filename_parts[0]}_details{detail_filename_parts[1]}"
        output_path = os.path.join(OUTPUT['directory'], output_filename)

        if os.path.exists(output_path):
            try:
                logging.info(f"Checking existing details file: {output_path}")
                existing_df = pd.read_csv(output_path, encoding=OUTPUT.get('encoding', 'utf-8-sig'), usecols=['job_number_ref'], dtype={'job_number_ref': str})
                existing_job_numbers = set(existing_df['job_number_ref'].dropna().unique())
                logging.info(f"Loaded {len(existing_job_numbers)} existing job numbers from {output_path} to skip.")
            except FileNotFoundError:
                # Should not happen if os.path.exists is true, but handle defensively
                logging.warning(f"Existing details file check failed (FileNotFound): {output_path}. Will not skip any.")
            except Exception as e:
                logging.error(f"Error reading existing details file {output_path}: {e}. Will not skip any.")


        try:
            # Read job_number related columns explicitly as string
            # Ensure kSNoJo and kSNoGe are read if they exist, otherwise fallback to job_number
            try:
                # Try reading all three, handling potential missing columns gracefully later
                list_df = pd.read_csv(list_csv_path, encoding=OUTPUT.get('encoding', 'utf-8-sig'),
                                      dtype={'job_number': str, 'kSNoJo': str, 'kSNoGe': str})
            except ValueError as ve: # Handle case where kSNoJo/kSNoGe might not exist in older files
                 if 'Usecols do not match columns' in str(ve):
                     logging.warning("Columns 'kSNoJo' or 'kSNoGe' might be missing. Reading only 'job_number'. Comparison might be inaccurate if format differs.")
                     list_df = pd.read_csv(list_csv_path, encoding=OUTPUT.get('encoding', 'utf-8-sig'),
                                           dtype={'job_number': str})
                 else:
                     raise ve # Re-raise other ValueErrors

            logging.info(f"Read {len(list_df)} entries from list CSV: {list_csv_path}")
        except FileNotFoundError:
            logging.error(f"List CSV file not found: {list_csv_path}")
            return
        except Exception as e:
            logging.error(f"Error reading list CSV {list_csv_path}: {e}")
            return

        # Check required columns - adapt based on whether kSNoJo/kSNoGe were read
        required_cols = ['detail_link_href']
        has_split_cols = 'kSNoJo' in list_df.columns and 'kSNoGe' in list_df.columns
        has_job_number_col = 'job_number' in list_df.columns

        if not has_split_cols and not has_job_number_col:
             logging.error(f"CSV {list_csv_path} must contain either ('kSNoJo' and 'kSNoGe') or 'job_number' column.")
             return
        if 'detail_link_href' not in list_df.columns:
             logging.error(f"CSV {list_csv_path} must contain 'detail_link_href' column.")
             return


        if not self._setup_driver():
            logging.error("Failed to set up WebDriver for detail scraping.")
            return

        total_to_process = len(list_df)
        for index, row in list_df.iterrows():
            # --- Check limit ---
            if limit is not None and processed_count >= limit:
                logging.info(f"Reached processing limit of {limit}. Stopping.")
                break

            # --- Determine the job number to use for comparison ---
            job_num_for_comparison = None
            job_num_display = "N/A" # For logging
            if has_split_cols and pd.notna(row['kSNoJo']) and pd.notna(row['kSNoGe']):
                job_num_for_comparison = f"{row['kSNoJo']}-{row['kSNoGe']}"
                job_num_display = job_num_for_comparison
            elif has_job_number_col and pd.notna(row['job_number']):
                 # Use job_number directly if split columns aren't available/valid
                 job_num_for_comparison = row['job_number']
                 job_num_display = job_num_for_comparison
                 if not has_split_cols: # Log warning only if split cols were expected but missing
                      logging.log(logging.DEBUG if index < 5 else logging.DEBUG - 5, # Log first few occurrences more visibly
                                  f"Using 'job_number' ({job_num_display}) for comparison as 'kSNoJo'/'kSNoGe' are missing/invalid.")
            else:
                 logging.warning(f"Skipping row {index + 1} due to missing/invalid job number identifier.")
                 skipped_count += 1
                 continue

            detail_href = row['detail_link_href']

            # --- Skip if constructed job number already exists ---
            if job_num_for_comparison in existing_job_numbers:
                logging.debug(f"Skipping job {job_num_display} as it exists in the output file.")
                skipped_count += 1
                continue

            if pd.isna(detail_href) or not detail_href:
                logging.warning(f"Skipping job {job_num_display} due to missing detail link.")
                skipped_count += 1
                continue

            logging.info(f"Processing detail page for job {job_num_display} ({index + 1}/{total_to_process}, Processed: {processed_count}, Skipped: {skipped_count})")
            page_source = self.fetch_detail_page(detail_href)

            if page_source:
                # Pass the comparison-ready job number to parse_detail_page
                detail_info = self.parse_detail_page(page_source, job_num_for_comparison)
                if detail_info:
                    all_details.append(detail_info)
                    processed_count += 1 # Increment count only on successful processing
            else:
                logging.warning(f"Failed to fetch or parse detail page for job {job_num_display}")
                # Optionally count this as skipped or failed? For now, just log.

            # Optional: Add a small delay between detail page requests if needed beyond REQUEST_INTERVAL
            # time.sleep(1)

        self.close_driver()

        if all_details:
            # Construct a filename, perhaps based on the input CSV name
            base_name = os.path.basename(list_csv_path)
            # Ensure the output filename reflects it contains details
            detail_filename_parts = os.path.splitext(base_name.replace("list_page", "details"))
            detail_filename = f"{detail_filename_parts[0]}_details{detail_filename_parts[1]}"

            # --- Decide whether to append or overwrite ---
            # For simplicity, let's overwrite. If appending is needed, logic here needs change.
            self.save_detail_data(all_details, output_filename=detail_filename)
            logging.info(f"Successfully processed {processed_count} new detail pages. Skipped {skipped_count}.")
        else:
            logging.warning(f"No new detail data was successfully scraped (Processed: {processed_count}, Skipped: {skipped_count}).")


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
    parser = argparse.ArgumentParser(description="Scrape HelloWork job detail pages from a list CSV, skipping existing and appending.")
    parser.add_argument("list_csv", help="Path to the job list CSV file containing 'job_number' and 'detail_link_href'.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of new detail pages to scrape.")

    args = parser.parse_args()

    if not os.path.exists(args.list_csv):
        print(f"Error: Input list CSV file not found - {args.list_csv}")
        logging.error(f"Input list CSV file not found: {args.list_csv}")
        sys.exit(1)

    logging.info(f"Starting detail scrape process for CSV: {args.list_csv}")
    if args.limit is not None:
        logging.info(f"Processing limit set to: {args.limit}")
    logging.info("Will automatically skip jobs found in the output file and append new data.")

    detail_scraper = DetailScraper()
    # Call run_detail_scrape_from_csv without skip_existing_path
    detail_scraper.run_detail_scrape_from_csv(args.list_csv, limit=args.limit)

    print(f"Detail scraping process finished for {args.list_csv}.")
