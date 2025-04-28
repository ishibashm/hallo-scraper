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

# Default columns to keep when using --enrich mode if --columns is not specified
DEFAULT_DETAIL_COLUMNS_TO_ENRICH = [
    'office_reception', 'industry_classification', 'office_name', 'office_zipcode',
    'office_address', 'office_homepage', 'employees_total', 'employees_location',
    'employees_female', 'employees_parttime', 'establishment_year', 'capital',
    'labor_union', 'business_content', 'company_features', 'representative_title',
    'representative_name', 'corporate_number'
]

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

    def run_detail_scrape_from_csv(self, list_file_path, limit=None):
        """
        Reads job numbers and detail links from the list CSV, scrapes details,
        skips jobs already present in the output file, and appends new data to a *details* CSV/JSON.
        This is the original functionality when --enrich is NOT used.

        Args:
            list_file_path (str): Path to the job list CSV file.
            limit (int, optional): Maximum number of new detail pages to scrape. Defaults to None (no limit).
        """
        all_details = []
        processed_count = 0
        skipped_count = 0
        existing_job_numbers = set()

        # --- Determine output filename and load existing job numbers ---
        base_name = os.path.basename(list_file_path)
        # Ensure the output filename reflects it contains details
        # Handle potential different input filenames more robustly
        if "list_page" in base_name:
             detail_filename_base = base_name.replace("list_page", "details")
        else:
             # Add _details suffix if 'list_page' wasn't in the name
             name_part, ext_part = os.path.splitext(base_name)
             detail_filename_base = f"{name_part}_details{ext_part}"

        output_filename = detail_filename_base # Use the generated base name
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
                list_df = pd.read_csv(list_file_path, encoding=OUTPUT.get('encoding', 'utf-8-sig'),
                                      dtype={'job_number': str, 'kSNoJo': str, 'kSNoGe': str})
            except ValueError as ve: # Handle case where kSNoJo/kSNoGe might not exist in older files
                 # Check if the error message indicates missing columns we tried to read
                 if 'Usecols do not match columns' in str(ve) or all(col not in pd.read_csv(list_file_path, nrows=0).columns for col in ['kSNoJo', 'kSNoGe']):
                     logging.warning("Columns 'kSNoJo' or 'kSNoGe' might be missing. Reading only 'job_number'. Comparison might be inaccurate if format differs.")
                     list_df = pd.read_csv(list_file_path, encoding=OUTPUT.get('encoding', 'utf-8-sig'),
                                           dtype={'job_number': str}) # Read only job_number
                 else:
                     raise ve # Re-raise other ValueErrors

            logging.info(f"Read {len(list_df)} entries from list CSV: {list_file_path}")
        except FileNotFoundError:
            logging.error(f"List CSV file not found: {list_file_path}")
            return
        except Exception as e:
            logging.error(f"Error reading list CSV {list_file_path}: {e}")
            return

        # Check required columns - adapt based on whether kSNoJo/kSNoGe were read
        required_cols = ['detail_link_href']
        has_split_cols = 'kSNoJo' in list_df.columns and 'kSNoGe' in list_df.columns
        has_job_number_col = 'job_number' in list_df.columns

        if not has_split_cols and not has_job_number_col:
             logging.error(f"CSV {list_file_path} must contain either ('kSNoJo' and 'kSNoGe') or 'job_number' column.")
             return
        if 'detail_link_href' not in list_df.columns:
            logging.error(f"CSV {list_file_path} must contain 'detail_link_href' column.")
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
            # Use the filename determined earlier (which already includes _details)
            self.save_detail_data(all_details, output_filename=output_filename)
            logging.info(f"Successfully processed {processed_count} new detail pages. Skipped {skipped_count}.")
        else:
            logging.warning(f"No new detail data was successfully scraped (Processed: {processed_count}, Skipped: {skipped_count}).")

    def enrich_list_data(self, list_file_path, columns_to_keep, limit=None):
        """
        Reads a list file (CSV/JSON/JSONL), scrapes details for each entry,
        merges selected detail columns back into the list data, and saves
        the enriched data to new CSV and JSON files.

        Args:
            list_file_path (str): Path to the job list CSV, JSON, or JSONL file.
            columns_to_keep (list): List of detail column names to extract and merge.
            limit (int, optional): Maximum number of list entries to process. Defaults to None.
        """
        all_enriched_data = []
        processed_count = 0 # Count of newly fetched details
        skipped_count = 0   # Count of skipped detail fetches (found in existing enriched file)
        output_dir = OUTPUT.get('directory', 'output')
        os.makedirs(output_dir, exist_ok=True)

        # --- Determine expected enriched output path ---
        base_name = os.path.basename(list_file_path)
        name_part, _ = os.path.splitext(base_name)
        enriched_output_base_name = f"enriched_{name_part}"
        enriched_csv_path = os.path.join(output_dir, f"{enriched_output_base_name}.csv")

        # --- Load existing enriched data for skipping ---
        existing_data_map = {}
        job_number_key_in_enriched = None # To store which key ('job_number' or combined) is used in the existing file

        if os.path.exists(enriched_csv_path):
            logging.info(f"Found existing enriched file: {enriched_csv_path}. Loading data to enable skipping.")
            try:
                # Determine potential job number keys from the existing file header
                try:
                    existing_file_cols = pd.read_csv(enriched_csv_path, nrows=0, encoding=OUTPUT.get('encoding', 'utf-8-sig')).columns.tolist()
                except Exception as read_err:
                    logging.error(f"Could not read header from existing enriched file {enriched_csv_path}: {read_err}. Skipping disabled.")
                    existing_file_cols = []

                potential_keys = ['job_number', 'kSNoJo', 'kSNoGe']
                # Read only necessary columns: potential keys + columns_to_keep that actually exist in the file
                cols_to_read = [col for col in potential_keys if col in existing_file_cols]
                cols_to_read.extend([col for col in columns_to_keep if col in existing_file_cols])
                cols_to_read = list(set(cols_to_read)) # Remove duplicates

                if not cols_to_read:
                     logging.warning(f"Could not determine necessary columns (job key or specified details) in existing enriched file: {enriched_csv_path}. Skipping disabled.")
                else:
                    existing_df = pd.read_csv(enriched_csv_path, usecols=cols_to_read, dtype=str, encoding=OUTPUT.get('encoding', 'utf-8-sig'))
                    logging.info(f"Loaded {len(existing_df)} records from existing enriched file.")

                    # Determine the job number key used in the existing file
                    if 'job_number' in existing_df.columns:
                        job_number_key_in_enriched = 'job_number'
                    elif 'kSNoJo' in existing_df.columns and 'kSNoGe' in existing_df.columns:
                         # Create a temporary combined key for mapping if split keys exist
                         existing_df['_combined_job_num'] = existing_df['kSNoJo'].fillna('') + '-' + existing_df['kSNoGe'].fillna('')
                         job_number_key_in_enriched = '_combined_job_num'
                    else:
                         logging.warning("Could not determine a valid job number key in the existing enriched file. Skipping disabled.")

                    if job_number_key_in_enriched:
                        # Create the map for quick lookup: {job_num: {col1: val1, ...}}
                        # Only map columns that were actually requested (columns_to_keep)
                        cols_in_map = [col for col in columns_to_keep if col in existing_df.columns]
                        for _, row in existing_df.iterrows():
                            job_num = row[job_number_key_in_enriched]
                            if pd.notna(job_num) and job_num:
                                existing_data_map[job_num] = {col: row.get(col) for col in cols_in_map}
                        logging.info(f"Created map for {len(existing_data_map)} existing job numbers to enable skipping.")

            except Exception as e:
                logging.error(f"Error reading existing enriched file {enriched_csv_path}: {e}. Skipping will be disabled.")
                existing_data_map = {} # Ensure map is empty on error

        # --- Read Input List Data ---
        try:
            logging.info(f"Reading list data for enrichment from: {list_file_path}")
            file_ext = os.path.splitext(list_file_path)[1].lower()
            list_encoding = OUTPUT.get('encoding', 'utf-8-sig') # Default for CSV

            if file_ext == '.csv':
                list_df = pd.read_csv(list_file_path, encoding=list_encoding, dtype=str) # Read all as string initially
            elif file_ext == '.json' or file_ext == '.jsonl':
                try:
                    list_df = pd.read_json(list_file_path, orient='records', dtype=str)
                except ValueError:
                    logging.info(f"Reading {list_file_path} as JSON Lines.")
                    list_df = pd.read_json(list_file_path, lines=True, orient='records', dtype=str)
            else:
                logging.error(f"Unsupported list file format: {file_ext}. Please provide .csv, .json, or .jsonl")
                return

            logging.info(f"Read {len(list_df)} records from list file for enrichment.")

            # Check required columns
            required_cols = ['detail_link_href']
            has_split_cols = 'kSNoJo' in list_df.columns and 'kSNoGe' in list_df.columns
            has_job_number_col = 'job_number' in list_df.columns

            if not has_split_cols and not has_job_number_col:
                 logging.error(f"List file {list_file_path} must contain either ('kSNoJo' and 'kSNoGe') or 'job_number' column for merging.")
                 return
            if 'detail_link_href' not in list_df.columns:
                 logging.error(f"List file {list_file_path} must contain 'detail_link_href' column.")
                 return

        except FileNotFoundError:
            logging.error(f"List file not found: {list_file_path}")
            return
        except Exception as e:
            logging.error(f"Error reading list file {list_file_path}: {e}")
            return

        if not self._setup_driver():
            logging.error("Failed to set up WebDriver for detail scraping.")
            return

        # --- Process each entry in the list ---
        total_to_process = len(list_df)
        # detail_data_cache = {} # Cache is less relevant now with skip logic based on file

        for index, row_series in list_df.iterrows():
            row = row_series.to_dict() # Work with dict for easier modification

            # --- Check overall limit (based on index/row number processed) ---
            # Note: Limit applies to the number of *rows processed* from the input list,
            # regardless of whether details were fetched or skipped.
            if limit is not None and index >= limit:
                logging.info(f"Reached processing limit of {limit} input rows. Stopping enrichment.")
                break

            # --- Determine job number for comparison and lookup ---
            job_num_for_comparison = None
            job_num_display = "N/A"
            if has_split_cols and pd.notna(row.get('kSNoJo')) and pd.notna(row.get('kSNoGe')):
                job_num_for_comparison = f"{row['kSNoJo']}-{row['kSNoGe']}"
                job_num_display = job_num_for_comparison
            elif has_job_number_col and pd.notna(row.get('job_number')):
                job_num_for_comparison = row['job_number']
                job_num_display = job_num_for_comparison
            else:
                 logging.warning(f"Skipping row {index + 1} due to missing/invalid job number identifier.")
                 skipped_count += 1
                 all_enriched_data.append(row) # Append original row even if skipped
                 continue

            detail_href = row.get('detail_link_href')

            if pd.isna(detail_href) or not detail_href:
                logging.warning(f"Skipping job {job_num_display} due to missing detail link.")
                skipped_count += 1
                all_enriched_data.append(row) # Append original row
                continue

            # --- Check if job exists in existing enriched data and has all requested columns ---
            should_skip = False
            if job_num_for_comparison in existing_data_map:
                # Check if *all* requested columns are present in the mapped data for this job
                existing_details = existing_data_map[job_num_for_comparison]
                if all(col in existing_details and pd.notna(existing_details[col]) for col in columns_to_keep):
                    should_skip = True
                    logging.debug(f"Skipping detail fetch for job {job_num_display} - found in existing enriched data with all requested columns.")
                    for col in columns_to_keep:
                        row[col] = existing_details.get(col, '') # Use existing data
                    skipped_count += 1
                else:
                    logging.debug(f"Job {job_num_display} found in existing data, but missing some requested columns. Will re-fetch.")

            if not should_skip:
                # --- Fetch and parse detail page (only if not skipped) ---
                logging.info(f"Fetching details for job {job_num_display} ({index + 1}/{total_to_process}, Fetched: {processed_count}, Skipped: {skipped_count})")
                page_source = self.fetch_detail_page(detail_href)
                detail_info = None
                if page_source:
                    detail_info = self.parse_detail_page(page_source, job_num_for_comparison)

                if detail_info:
                    # Select only the requested columns from the detail_info
                    for col in columns_to_keep:
                        row[col] = detail_info.get(col, '') # Add/update column in the original row dict
                    processed_count += 1
                else:
                    logging.warning(f"Failed to fetch or parse detail page for job {job_num_display}. Columns will be empty.")
                    # Ensure requested columns exist in the row, even if empty, if fetch failed
                    for col in columns_to_keep:
                        if col not in row:
                            row[col] = ''
                    # Don't increment skipped_count here, as it wasn't found/complete in existing file

            all_enriched_data.append(row) # Append the (potentially enriched) row

        # --- Save Enriched Data ---
        if not all_enriched_data:
            logging.warning("No data to save after enrichment process.")
            return

        enriched_df = pd.DataFrame(all_enriched_data)

        # Use the paths generated earlier
        csv_output_path = enriched_csv_path # Reuse the path determined at the start
        json_output_path = os.path.join(output_dir, f"{enriched_output_base_name}.json")

        saved_files = []
        # Save CSV (Overwrite)
        try:
            csv_encoding = OUTPUT.get('encoding', 'utf-8-sig')
            enriched_df.to_csv(csv_output_path, encoding=csv_encoding, index=False)
            logging.info(f"Enriched data successfully saved/overwritten as CSV to: {csv_output_path}")
            saved_files.append(csv_output_path)
        except Exception as e:
            logging.error(f"Failed to save enriched data as CSV: {e}")

        # Save JSON (Overwrite)
        try:
            json_encoding = OUTPUT.get('encoding_json', 'utf-8')
            json_string = enriched_df.to_json(orient='records', force_ascii=False, indent=4)
            with open(json_output_path, 'w', encoding=json_encoding) as f:
                f.write(json_string)
            logging.info(f"Enriched data successfully saved/overwritten as JSON to: {json_output_path}")
            saved_files.append(json_output_path)
        except Exception as e:
            logging.error(f"Failed to save enriched data as JSON: {e}")

        logging.info(f"Enrichment process finished. Newly Fetched: {processed_count}, Skipped (Existing & Complete): {skipped_count}.")
        if saved_files:
             print("Enriched data saved/overwritten to:")
             for p in saved_files: print(f"- {p}")


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

# Main execution block
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape HelloWork job details. Can either generate a details-only file or enrich an existing list file.")
    parser.add_argument("list_file", help="Path to the input job list file (CSV, JSON, or JSONL).")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of list entries/detail pages to process.")
    parser.add_argument("--enrich", action='store_true', help="Enable enrichment mode: Fetch details, merge selected columns, and save to new 'enriched_*' files.")
    parser.add_argument("--columns", help="Comma-separated list of detail columns to merge when using --enrich (default: predefined list).")

    args = parser.parse_args()

    if not os.path.exists(args.list_file):
        print(f"Error: Input list file not found - {args.list_file}")
        logging.error(f"Input list file not found: {args.list_file}")
        sys.exit(1)

    detail_scraper = DetailScraper()

    if args.enrich:
        # --- Enrichment Mode ---
        logging.info(f"Starting enrichment process for list file: {args.list_file}")
        if args.limit is not None:
            logging.info(f"Processing limit set to: {args.limit}")

        # Determine columns to keep for enrichment
        if args.columns:
            cols_to_keep = [col.strip() for col in args.columns.split(',') if col.strip()]
            logging.info(f"Using specified columns for enrichment: {', '.join(cols_to_keep)}")
        else:
            cols_to_keep = DEFAULT_DETAIL_COLUMNS_TO_ENRICH
            logging.info(f"Using default columns for enrichment: {', '.join(cols_to_keep)}")

        detail_scraper.enrich_list_data(args.list_file, cols_to_keep, limit=args.limit)
        print(f"Enrichment process finished for {args.list_file}.")

    else:
        # --- Original Mode (Details-only file generation) ---
        # Check if input is CSV for this mode
        if not args.list_file.lower().endswith('.csv'):
             print("Error: Original mode (without --enrich) currently only supports CSV input files.")
             logging.error("Original mode (without --enrich) requires a CSV input file.")
             sys.exit(1)

        logging.info(f"Starting detail scrape process (details-only file) for CSV: {args.list_file}")
        if args.limit is not None:
            logging.info(f"Processing limit set to: {args.limit}")
        logging.info("Will automatically skip jobs found in the output details file and append new data.")

        detail_scraper.run_detail_scrape_from_csv(args.list_file, limit=args.limit)
        print(f"Detail scraping process (details-only file) finished for {args.list_file}.")
