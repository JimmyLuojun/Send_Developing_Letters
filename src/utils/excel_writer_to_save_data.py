# src/utils/excel_writer_to_save_data.py
"""Module for saving processed data back to an Excel file."""
import logging
import pandas as pd
from pathlib import Path
from typing import List
from dataclasses import asdict, is_dataclass # Import is_dataclass
from datetime import datetime # Import datetime
# Assuming TargetCompanyData is correctly defined in src.core
try:
    from src.core import TargetCompanyData
except ImportError:
    logging.error("Could not import TargetCompanyData from src.core. Ensure src is in PYTHONPATH or structure is correct.")
    # Provide a fallback or raise a clearer error if core structure is crucial
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
    Includes a 'saving_file_time' column for the batch save time.

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
        # Use asdict for robust conversion from dataclass instances
        new_data_list = [asdict(company) for company in processed_companies]
        new_df = pd.DataFrame(new_data_list)
    except Exception as e:
        logger.error(f"Failed to convert processed company data to DataFrame: {e}", exc_info=True)
        return

    if new_df.empty:
        logger.info("Processed data resulted in an empty DataFrame. Nothing to save.")
        return

    # --- Add saving_file_time column ---
    # Generate timestamp *once* for this batch
    current_time_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    new_df['saving_file_time'] = current_time_str
    # --- End Add saving_file_time column ---


    # Define the desired order/subset of columns for the output Excel file
    # Ensure 'saving_file_time' is first as requested
    output_columns = [
        'saving_file_time', # Added first
        'company_name', 'website', 'recipient_email', 'contact_person',
        'process_flag', # Store the flag used for the 'should_process' property
        'target_language', 'main_business',
        'cooperation_points_str', # Save raw string
        # 'cooperation_points_list', # Usually skip list/object columns
        'generated_letter_subject', 'generated_letter_body',
        'processing_status', 'draft_id'
        # Add 'should_process' if you want the calculated boolean value saved explicitly
        # 'should_process'
    ]

    # Add 'should_process' property value as a separate column if desired
    # if 'should_process' in output_columns:
    #    try:
    #        # Important: Access property on original objects, not dicts/DataFrame rows
    #        new_df['should_process'] = [company.should_process for company in processed_companies]
    #    except Exception as e:
    #        logger.error(f"Failed to calculate 'should_process' property for saving: {e}")
    #        # Ensure column exists before trying to drop if calculation fails midway
    #        if 'should_process' in new_df.columns:
    #             new_df = new_df.drop(columns=['should_process'], errors='ignore')


    # Filter DataFrame to include only desired columns that actually exist in the new data
    # Make sure saving_file_time is included if it was added successfully
    columns_to_write = [col for col in output_columns if col in new_df.columns]
    if not columns_to_write:
        logger.error("No valid columns defined in 'output_columns' match the processed data.")
        return
    new_df_filtered = new_df[columns_to_write]

    # --- Append Logic ---
    try:
        combined_df = new_df_filtered # Start with the new data as default
        if output_excel_path.exists():
            logger.info(f"Reading existing data from: {output_excel_path}")
            try:
                existing_df = pd.read_excel(output_excel_path, engine='openpyxl')
                logger.info(f"Found {len(existing_df)} existing records.")

                # --- Column Alignment (Robust Append) ---
                existing_cols = set(existing_df.columns)
                new_cols = set(new_df_filtered.columns)
                # Use the desired output_columns order as base, add extra existing if any
                base_cols = [col for col in output_columns if col in existing_cols.union(new_cols)]
                extra_existing_cols = sorted(list(existing_cols.difference(base_cols)))
                all_cols_ordered = base_cols + extra_existing_cols # Final column order

                # Reindex both DataFrames
                existing_df_aligned = existing_df.reindex(columns=all_cols_ordered)
                new_df_aligned = new_df_filtered.reindex(columns=all_cols_ordered)
                # --- End Column Alignment ---

                logger.info(f"Appending {len(new_df_aligned)} new records to existing data.")
                combined_df = pd.concat([existing_df_aligned, new_df_aligned], ignore_index=True)

                # Optional: Remove duplicates after appending, keeping the latest entry
                # key_columns = ['recipient_email', 'company_name']
                # ... (duplicate removal logic as before) ...

            except FileNotFoundError:
                 logger.info(f"Existing file check passed but read failed. Creating new file.")
                 combined_df = new_df_filtered
            except Exception as read_e:
                logger.error(f"Failed to read/process existing file {output_excel_path}. BACKING UP and overwriting. Error: {read_e}", exc_info=True)
                try:
                    backup_path = output_excel_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx")
                    output_excel_path.rename(backup_path)
                    logger.info(f"Backed up existing file to {backup_path}")
                except Exception as backup_e:
                    logger.error(f"Failed to backup existing file {output_excel_path}: {backup_e}")
                combined_df = new_df_filtered
        else:
            logger.info(f"Creating new results file: {output_excel_path}")
            # combined_df is already set to new_df_filtered

        # --- Write to Excel ---
        combined_df.to_excel(output_excel_path, index=False, engine='openpyxl')
        num_new = len(new_df_filtered)
        total_rows = len(combined_df)
        logger.info(f"Successfully saved data. Added {num_new} new records. Total rows in file: {total_rows}. Path: {output_excel_path}")

    except ImportError:
         logger.error("The 'openpyxl' library is required for Excel operations. Please install it.")
    except Exception as e:
        logger.error(f"Failed to save data to Excel file '{output_excel_path}': {e}", exc_info=True)

# Keep the commented-out original function if desired for reference, otherwise remove
# --- Original save_data_to_excel logic (commented out) ---
# ...