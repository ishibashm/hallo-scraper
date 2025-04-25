import pandas as pd
import argparse
import os
import logging
import sys

# Add project root to Python path (if run from project root, this might not be needed, but good practice)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config.settings import OUTPUT # Import OUTPUT settings for encoding
except ImportError:
    # Fallback if settings cannot be imported (e.g., run standalone without full project context)
    OUTPUT = {'encoding': 'utf-8-sig'}
    logging.warning("Could not import OUTPUT settings from config.settings. Using default encoding 'utf-8-sig'.")

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def merge_job_data(list_csv_path, detail_csv_path, output_csv_path):
    """
    Merges job list data and job detail data based on job number.

    Args:
        list_csv_path (str): Path to the job list CSV file.
        detail_csv_path (str): Path to the job detail CSV file.
        output_csv_path (str): Path for the merged output CSV file.

    Returns:
        bool: True if merge was successful, False otherwise.
    """
    try:
        logging.info(f"Reading list data from: {list_csv_path}")
        # Read job_number explicitly as string to avoid type issues during merge
        list_df = pd.read_csv(list_csv_path, encoding=OUTPUT.get('encoding', 'utf-8-sig'), dtype={'job_number': str})
        logging.info(f"Read {len(list_df)} records from list CSV.")

        if 'job_number' not in list_df.columns:
            logging.error(f"'job_number' column not found in list CSV: {list_csv_path}")
            return False

    except FileNotFoundError:
        logging.error(f"List CSV file not found: {list_csv_path}")
        return False
    except Exception as e:
        logging.error(f"Error reading list CSV {list_csv_path}: {e}")
        return False

    try:
        logging.info(f"Reading detail data from: {detail_csv_path}")
        # Read job_number_ref explicitly as string
        detail_df = pd.read_csv(detail_csv_path, encoding=OUTPUT.get('encoding', 'utf-8-sig'), dtype={'job_number_ref': str})
        logging.info(f"Read {len(detail_df)} records from detail CSV.")

        if 'job_number_ref' not in detail_df.columns:
            logging.error(f"'job_number_ref' column not found in detail CSV: {detail_csv_path}")
            return False

        # Define columns to potentially drop from detail_df before merging if they also exist in list_df
        cols_to_drop_from_detail = ['reception_date', 'deadline_date'] # Example: Often redundant
        detail_df_cleaned = detail_df.drop(columns=[col for col in cols_to_drop_from_detail if col in detail_df.columns and col in list_df.columns], errors='ignore')

    except FileNotFoundError:
        logging.error(f"Detail CSV file not found: {detail_csv_path}")
        return False
    except Exception as e:
        logging.error(f"Error reading detail CSV {detail_csv_path}: {e}")
        return False

    try:
        logging.info(f"Merging dataframes using list 'job_number' and detail 'job_number_ref'")
        # Perform a left merge using specific key columns
        merged_df = pd.merge(list_df, detail_df_cleaned, left_on='job_number', right_on='job_number_ref', how='left', suffixes=('_list', '_detail')) # Use suffixes to disambiguate any remaining common cols

        # Drop the redundant key column from the right dataframe after merge
        if 'job_number_ref' in merged_df.columns:
            merged_df = merged_df.drop(columns=['job_number_ref'])

        # Optional: Clean up suffixes if desired (e.g., prefer '_detail' values)
        # Example: If 'office_name_list' and 'office_name_detail' exist, keep '_detail' and rename
        # for col in list(merged_df.columns):
        #     if col.endswith('_detail'):
        #         original_col_name = col[:-len('_detail')]
        #         # If the original column (or _list suffixed one) exists, overwrite with _detail value
        #         if original_col_name in merged_df.columns or f"{original_col_name}_list" in merged_df.columns:
        #              merged_df[original_col_name] = merged_df[col]
        #              # Drop the original/list and the detail column
        #              merged_df = merged_df.drop(columns=[col, f"{original_col_name}_list"], errors='ignore')
        #         else: # If only _detail column exists, just rename it
        #              merged_df = merged_df.rename(columns={col: original_col_name})

        logging.info(f"Merge complete. Resulting dataframe has {len(merged_df)} rows and {len(merged_df.columns)} columns.")

        output_dir = os.path.dirname(output_csv_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        merged_df.to_csv(output_csv_path, encoding=OUTPUT.get('encoding', 'utf-8-sig'), index=False)
        logging.info(f"Merged data successfully saved to: {output_csv_path}")
        return True

    except Exception as e:
        # Log the full traceback for merge/save errors
        logging.exception(f"Error during merge or save operation: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge HelloWork job list CSV and detail CSV files.")
    parser.add_argument("list_csv", help="Path to the job list CSV file.")
    parser.add_argument("detail_csv", help="Path to the job detail CSV file.")
    parser.add_argument("output_csv", help="Path for the merged output CSV file.")

    args = parser.parse_args()

    if not os.path.exists(args.list_csv):
        print(f"Error: List CSV file not found - {args.list_csv}")
        sys.exit(1)
    if not os.path.exists(args.detail_csv):
        print(f"Error: Detail CSV file not found - {args.detail_csv}")
        sys.exit(1)

    success = merge_job_data(args.list_csv, args.detail_csv, args.output_csv)

    if success:
        print(f"Successfully merged data saved to {args.output_csv}")
    else:
        print("Merging failed. Check logs for details.")
        sys.exit(1)
