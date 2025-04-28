import pandas as pd
import argparse
import os
import logging
import sys

# Add project root to Python path (if run from project root, this might not be needed, but good practice)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config.settings import OUTPUT # Import OUTPUT settings for encoding and output dir
except ImportError:
    # Fallback if settings cannot be imported (e.g., run standalone without full project context)
    OUTPUT = {'encoding': 'utf-8-sig', 'directory': 'output', 'encoding_json': 'utf-8'}
    logging.warning("Could not import OUTPUT settings from config.settings. Using default settings.")

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Default columns from detail data to keep if --columns is not specified
DEFAULT_DETAIL_COLUMNS = [
    'office_reception', 'industry_classification', 'office_name', 'office_zipcode',
    'office_address', 'office_homepage', 'employees_total', 'employees_location',
    'employees_female', 'employees_parttime', 'establishment_year', 'capital',
    'labor_union', 'business_content', 'company_features', 'representative_title',
    'representative_name', 'corporate_number'
]

def merge_job_data(list_file_path, detail_csv_path, detail_columns_to_keep, output_mode='new'):
    """
    Merges job list data (CSV or JSON) and selected job detail data (CSV).
    Outputs the merged data based on the specified output mode.

    Args:
        list_file_path (str): Path to the job list CSV or JSON file.
        detail_csv_path (str): Path to the job detail CSV file.
        detail_columns_to_keep (list): List of column names from the detail CSV to merge.
        output_mode (str): 'new' to create new merged files, 'overwrite' to overwrite the original list file.

    Returns:
        list: List of paths to the successfully saved merged files, or empty list on failure.
    """
    saved_files = []
    output_dir = OUTPUT.get('directory', 'output')
    os.makedirs(output_dir, exist_ok=True)

    # --- Read List Data ---
    try:
        logging.info(f"Reading list data from: {list_file_path}")
        file_ext = os.path.splitext(list_file_path)[1].lower()
        list_encoding = OUTPUT.get('encoding', 'utf-8-sig') # Default for CSV

        if file_ext == '.csv':
            list_df = pd.read_csv(list_file_path, encoding=list_encoding, dtype={'job_number': str})
        elif file_ext == '.json' or file_ext == '.jsonl':
            # Try reading as JSON array first, then fallback to JSON Lines
            try:
                list_df = pd.read_json(list_file_path, orient='records', dtype={'job_number': str})
            except ValueError:
                logging.info(f"Reading {list_file_path} as JSON Lines.")
                list_df = pd.read_json(list_file_path, lines=True, orient='records', dtype={'job_number': str})
        else:
            logging.error(f"Unsupported list file format: {file_ext}. Please provide .csv, .json, or .jsonl")
            return saved_files

        logging.info(f"Read {len(list_df)} records from list file.")

        if 'job_number' not in list_df.columns:
            logging.error(f"'job_number' column not found in list file: {list_file_path}")
            return saved_files

    except FileNotFoundError:
        logging.error(f"List file not found: {list_file_path}")
        return saved_files
    except Exception as e:
        logging.error(f"Error reading list file {list_file_path}: {e}")
        return saved_files

    # --- Read Detail Data ---
    try:
        logging.info(f"Reading detail data from: {detail_csv_path}")
        detail_encoding = OUTPUT.get('encoding', 'utf-8-sig') # Use same encoding as list CSV for details
        detail_df = pd.read_csv(detail_csv_path, encoding=detail_encoding, dtype={'job_number_ref': str})
        logging.info(f"Read {len(detail_df)} records from detail CSV.")

        if 'job_number_ref' not in detail_df.columns:
            logging.error(f"'job_number_ref' column not found in detail CSV: {detail_csv_path}")
            return saved_files

        # --- Select Detail Columns ---
        # Ensure the join key is always included
        if 'job_number_ref' not in detail_columns_to_keep:
            detail_columns_to_keep_with_key = ['job_number_ref'] + detail_columns_to_keep
        else:
            detail_columns_to_keep_with_key = detail_columns_to_keep

        # Check for missing columns and warn
        missing_cols = [col for col in detail_columns_to_keep_with_key if col not in detail_df.columns]
        if missing_cols:
            logging.warning(f"Specified detail columns not found in {detail_csv_path}: {', '.join(missing_cols)}")

        # Select only the existing columns to keep + the key
        actual_cols_to_select = [col for col in detail_columns_to_keep_with_key if col in detail_df.columns]
        if not actual_cols_to_select or ('job_number_ref' not in actual_cols_to_select and 'job_number_ref' in detail_df.columns):
             logging.error("No valid columns (including join key 'job_number_ref') selected from detail data.")
             return saved_files
        if 'job_number_ref' not in actual_cols_to_select and 'job_number_ref' in detail_df.columns: # Ensure key is present if it exists
            actual_cols_to_select.append('job_number_ref')

        detail_df_selected = detail_df[actual_cols_to_select].copy() # Use .copy() to avoid SettingWithCopyWarning
        logging.info(f"Selected columns from detail data: {', '.join(actual_cols_to_select)}")


    except FileNotFoundError:
        logging.error(f"Detail CSV file not found: {detail_csv_path}")
        return saved_files
    except Exception as e:
        logging.error(f"Error reading or processing detail CSV {detail_csv_path}: {e}")
        return saved_files

    # --- Merge Data ---
    try:
        logging.info(f"Merging dataframes using list 'job_number' and detail 'job_number_ref'")
        # Perform a left merge using specific key columns
        merged_df = pd.merge(list_df, detail_df_selected, left_on='job_number', right_on='job_number_ref', how='left', suffixes=('', '_detail')) # Avoid _list suffix, use _detail only if needed

        # Drop the redundant key column from the right dataframe after merge
        if 'job_number_ref' in merged_df.columns:
            merged_df = merged_df.drop(columns=['job_number_ref'])

        # Clean up potential duplicate columns created by merge if suffixes were needed (prefer _detail)
        cols_to_drop = []
        renamed_cols = {}
        for col in merged_df.columns:
            if col.endswith('_detail'):
                original_col = col[:-len('_detail')]
                if original_col in merged_df.columns: # If original exists, _detail overrides it
                    merged_df[original_col] = merged_df[col]
                    cols_to_drop.append(col) # Mark _detail col for dropping
                else: # If only _detail exists, rename it
                    renamed_cols[col] = original_col
        if cols_to_drop:
            merged_df = merged_df.drop(columns=cols_to_drop)
        if renamed_cols:
            merged_df = merged_df.rename(columns=renamed_cols)


        logging.info(f"Merge complete. Resulting dataframe has {len(merged_df)} rows and {len(merged_df.columns)} columns.")

        # --- Determine Output Paths based on output_mode ---
        original_file_ext = os.path.splitext(list_file_path)[1].lower()

        if output_mode == 'overwrite':
            # Use the original list file path for overwriting
            output_path_base = list_file_path
            logging.info(f"Output mode set to 'overwrite'. Will attempt to overwrite: {list_file_path}")
        else: # Default to 'new'
            # Generate new file paths in the output directory
            list_filename_base = os.path.basename(list_file_path)
            output_base_name = f"merged_{list_filename_base.replace('.csv', '').replace('.json', '').replace('.jsonl', '')}"
            output_path_base = os.path.join(output_dir, output_base_name)
            logging.info(f"Output mode set to 'new'. Will create new files with base: {output_path_base}")

        # --- Save Merged Data ---
        # Determine the target format based on the original list file if overwriting, or save both if new
        target_formats = []
        if output_mode == 'overwrite':
            if original_file_ext == '.csv':
                target_formats.append('csv')
            elif original_file_ext in ['.json', '.jsonl']:
                target_formats.append('json') # Overwrite JSON/JSONL as standard JSON array
        else: # 'new' mode saves both
            target_formats.extend(['csv', 'json'])

        # Save in target formats
        if 'csv' in target_formats:
            csv_output_path = output_path_base if output_mode == 'overwrite' and original_file_ext == '.csv' else f"{output_path_base}.csv"
            try:
                csv_encoding = OUTPUT.get('encoding', 'utf-8-sig')
                merged_df.to_csv(csv_output_path, encoding=csv_encoding, index=False)
                logging.info(f"Merged data successfully saved as CSV to: {csv_output_path}")
                saved_files.append(csv_output_path)
            except Exception as e:
                logging.error(f"Failed to save merged data as CSV to {csv_output_path}: {e}")

        if 'json' in target_formats:
            json_output_path = output_path_base if output_mode == 'overwrite' and original_file_ext in ['.json', '.jsonl'] else f"{output_path_base}.json"
            try:
                json_encoding = OUTPUT.get('encoding_json', 'utf-8')
                # Use orient='records' for standard JSON array output
                json_string = merged_df.to_json(orient='records', force_ascii=False, indent=4)
                with open(json_output_path, 'w', encoding=json_encoding) as f:
                    f.write(json_string)
                logging.info(f"Merged data successfully saved as JSON to: {json_output_path}")
                saved_files.append(json_output_path)
            except Exception as e:
                logging.error(f"Failed to save merged data as JSON to {json_output_path}: {e}")

        return saved_files # Return list of successfully saved file paths

    except Exception as e:
        # Log the full traceback for merge/save errors
        logging.exception(f"Error during merge or save operation: {e}")
        return saved_files # Return empty or partially filled list

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge HelloWork job list (CSV/JSON) and detail CSV files, selecting specific detail columns.")
    parser.add_argument("list_file", help="Path to the job list CSV, JSON, or JSONL file.")
    parser.add_argument("detail_csv", help="Path to the job detail CSV file.")
    parser.add_argument("--columns", help="Comma-separated list of detail columns to merge (default: predefined list).")
    parser.add_argument("--output-mode", choices=['new', 'overwrite'], default='new',
                        help="Output mode: 'new' creates new merged files (default), 'overwrite' overwrites the original list file.")

    args = parser.parse_args()

    # --- Safety check for overwrite mode ---
    if args.output_mode == 'overwrite':
        confirm = input(f"WARNING: Output mode is 'overwrite'. This will modify the original file: {args.list_file}\nAre you sure you want to continue? (yes/no): ").lower()
        if confirm != 'yes':
            print("Operation cancelled by user.")
            sys.exit(0)

    # Determine columns to keep
    if args.columns:
        # Split by comma and remove leading/trailing whitespace
        detail_cols_to_keep = [col.strip() for col in args.columns.split(',') if col.strip()]
        logging.info(f"Using specified detail columns: {', '.join(detail_cols_to_keep)}")
    else:
        detail_cols_to_keep = DEFAULT_DETAIL_COLUMNS
        logging.info(f"Using default detail columns: {', '.join(detail_cols_to_keep)}")

    # Check input files exist
    if not os.path.exists(args.list_file):
        print(f"Error: List file not found - {args.list_file}")
        sys.exit(1)
    if not os.path.exists(args.detail_csv):
        print(f"Error: Detail CSV file not found - {args.detail_csv}")
        sys.exit(1)

    # Call merge function with the output mode
    saved_file_paths = merge_job_data(args.list_file, args.detail_csv, detail_cols_to_keep, args.output_mode)

    if saved_file_paths:
        if args.output_mode == 'overwrite':
            print(f"Successfully merged data and overwrote:")
        else:
            print(f"Successfully merged data saved to:")
        for path in saved_file_paths:
            print(f"- {path}")
    else:
        print("Merging failed or no files were saved. Check logs for details.")
        sys.exit(1)
