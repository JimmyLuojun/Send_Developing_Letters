# src/utils/excel_writer_to_save_data.py
"""Module for saving processed data back to an Excel file."""
import logging
import pandas as pd
from pathlib import Path
from typing import List
from dataclasses import asdict, is_dataclass
from datetime import datetime
# --- Add openpyxl utility import ---
try:
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    logging.info("openpyxl not fully available. Column width adjustment will be skipped. Install with `poetry add openpyxl` or `pip install openpyxl`")
# --- End import ---

# Assuming TargetCompanyData is correctly defined in src.core
try:
    from src.core import TargetCompanyData
except ImportError:
    logging.error("Could not import TargetCompanyData from src.core. Ensure src is in PYTHONPATH or structure is correct.")
    TargetCompanyData = None # Basic fallback

logger = logging.getLogger(__name__)

# --- REFINED FUNCTION ---
def save_processed_data(
    processed_companies: List[TargetCompanyData], # type: ignore
    output_excel_path: Path
):
    """
    Saves the list of processed TargetCompanyData objects to an Excel file.
    Appends data to the file if it exists, otherwise creates a new file.
    Includes a 'saving_file_time' column and auto-adjusts column widths for headers.

    Args:
        processed_companies: List of TargetCompanyData objects processed in the current run.
        output_excel_path: Path object for the output Excel file.
    """
    if not processed_companies:
        logger.info("No new processed company data provided to save.")
        return

    # Validate input type
    if not TargetCompanyData or not all(is_dataclass(item) and isinstance(item, TargetCompanyData) for item in processed_companies):
         logger.error("save_processed_data expects a list of TargetCompanyData objects.")
         return

    # Ensure the output directory exists
    try:
        output_excel_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create output directory {output_excel_path.parent}: {e}", exc_info=True)
        return

    # Convert list of dataclass objects to DataFrame
    try:
        new_data_list = [asdict(company) for company in processed_companies]
        new_df = pd.DataFrame(new_data_list)
    except Exception as e:
        logger.error(f"Failed to convert processed company data to DataFrame: {e}", exc_info=True)
        return

    if new_df.empty:
        logger.info("Processed data resulted in an empty DataFrame. Nothing to save.")
        return

    # Add saving_file_time column
    current_time_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    new_df['saving_file_time'] = current_time_str

    # Define the desired order/subset of columns
    output_columns = [
        'saving_file_time', 'company_name', 'website', 'recipient_email',
        'contact_person', 'process_flag', 'target_language', 'main_business',
        'cooperation_points_str', 'generated_letter_subject',
        'generated_letter_body', 'processing_status', 'draft_id'
    ]

    # Filter DataFrame to include only desired columns that exist
    columns_to_write = [col for col in output_columns if col in new_df.columns]
    if not columns_to_write:
        logger.error("No valid columns defined in 'output_columns' match the processed data.")
        return
    new_df_filtered = new_df[columns_to_write]

    # --- Append Logic ---
    try:
        combined_df = new_df_filtered # Default to new data
        file_exists = output_excel_path.exists()

        if file_exists:
            logger.info(f"Reading existing data from: {output_excel_path}")
            try:
                existing_df = pd.read_excel(output_excel_path, engine='openpyxl')
                logger.info(f"Found {len(existing_df)} existing records.")
                # Align columns before concatenating
                existing_cols = set(existing_df.columns)
                new_cols = set(new_df_filtered.columns)
                base_cols = [col for col in output_columns if col in existing_cols.union(new_cols)]
                extra_existing_cols = sorted(list(existing_cols.difference(base_cols)))
                all_cols_ordered = base_cols + extra_existing_cols
                existing_df_aligned = existing_df.reindex(columns=all_cols_ordered)
                new_df_aligned = new_df_filtered.reindex(columns=all_cols_ordered)
                logger.info(f"Appending {len(new_df_aligned)} new records to existing data.")
                combined_df = pd.concat([existing_df_aligned, new_df_aligned], ignore_index=True)
                # Optional: Duplicate removal logic here...
            except Exception as read_e:
                logger.error(f"Failed to read/process existing file {output_excel_path}. BACKING UP and overwriting. Error: {read_e}", exc_info=True)
                try:
                    backup_path = output_excel_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx")
                    output_excel_path.rename(backup_path)
                    logger.info(f"Backed up existing file to {backup_path}")
                except Exception as backup_e:
                    logger.error(f"Failed to backup existing file {output_excel_path}: {backup_e}")
                combined_df = new_df_filtered # Fallback to only new data
        else:
            logger.info(f"Creating new results file: {output_excel_path}")
            # combined_df is already set to new_df_filtered

        # --- Write to Excel using ExcelWriter for formatting ---
        sheet_name = 'ProcessedData' # Define a sheet name
        with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
            combined_df.to_excel(writer, index=False, sheet_name=sheet_name)

            # --- Auto-adjust column widths ---
            if OPENPYXL_AVAILABLE:
                try:
                    # Access the workbook and worksheet objects
                    # workbook = writer.book # Not typically needed for column widths
                    worksheet = writer.sheets[sheet_name]

                    # Iterate through columns and set width based on header length + padding
                    for i, column_header in enumerate(combined_df.columns):
                        column_letter = get_column_letter(i + 1) # Get column letter (A, B, C...)
                        header_length = len(str(column_header))
                        # Add padding; adjust multiplier/minimum as needed
                        adjusted_width = (header_length + 2) * 1.1
                        minimum_width = 10 # Ensure a minimum width
                        worksheet.column_dimensions[column_letter].width = max(adjusted_width, minimum_width)
                    logger.info("Adjusted column widths based on headers.")
                except Exception as fmt_e:
                     logger.warning(f"Could not auto-adjust column widths: {fmt_e}")
            else:
                 logger.warning("openpyxl not fully available, skipping column width adjustment.")
            # --- End auto-adjust ---

        num_new = len(new_df_filtered)
        total_rows = len(combined_df)
        logger.info(f"Successfully saved data. Added {num_new} new records. Total rows in file: {total_rows}. Path: {output_excel_path}")

    except ImportError:
         logger.error("The 'openpyxl' library is required for Excel operations. Please install it.")
    except Exception as e:
        logger.error(f"Failed to save data to Excel file '{output_excel_path}': {e}", exc_info=True)

# --- Original commented out code ---
# ...