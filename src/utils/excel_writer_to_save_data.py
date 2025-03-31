# src/utils/excel_writer_to_save_data.py
"""Module for saving processed data back to an Excel file."""
import logging
import pandas as pd
from pathlib import Path
from typing import List
from datetime import datetime
# Assuming TargetCompanyData is correctly defined in src.core
try:
    from src.core import TargetCompanyData
except ImportError:
    # Provide a fallback or raise a clearer error if core structure is crucial
    logging.error("Could not import TargetCompanyData from src.core. Ensure src is in PYTHONPATH or structure is correct.")
    # Define a dummy class perhaps, or re-raise to halt execution if needed.
    class TargetCompanyData: pass # Basic fallback


def save_processed_data(
    processed_companies: List[TargetCompanyData],
    output_excel_path: Path
):
    """
    Saves the list of processed TargetCompanyData objects to an Excel file.
    Overwrites the file if it exists.

    Args:
        processed_companies: List of TargetCompanyData objects.
        output_excel_path: Path object for the output Excel file.
    """
    if not processed_companies:
        logging.info("No processed company data to save.")
        return

    # Define the columns expected in the output Excel
    output_columns = [
        'saving_file_time',
        'company_name',
        'website',
        'main_business',
        'recipient_email',
        'contact_person',
        'cooperation_points_str', # Save raw string
        'generated_letter_subject',
        'generated_letter_body',
        'processing_status',
        'draft_id'
    ]

    # Convert list of objects to list of dictionaries
    data_to_save = []
    # Use a single timestamp for all rows in this batch
    current_time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    for company in processed_companies:
        # Check if 'company' object has the expected attributes before accessing
        # This adds robustness if the input list might be inconsistent
        data_to_save.append({
            'saving_file_time': current_time,
            'company_name': getattr(company, 'company_name', None),
            'website': getattr(company, 'website', None),
            'main_business': getattr(company, 'main_business', None),
            'recipient_email': getattr(company, 'recipient_email', None),
            'contact_person': getattr(company, 'contact_person', None),
            'cooperation_points_str': getattr(company, 'cooperation_points_str', None),
            'generated_letter_subject': getattr(company, 'generated_letter_subject', None),
            'generated_letter_body': getattr(company, 'generated_letter_body', None),
            'processing_status': getattr(company, 'processing_status', None),
            'draft_id': getattr(company, 'draft_id', None)
        })

    # Create DataFrame with specified columns
    try:
        df_to_save = pd.DataFrame(data_to_save, columns=output_columns)
    except Exception as e:
        logging.error(f"Failed to create pandas DataFrame: {e}", exc_info=True)
        return # Cannot proceed without DataFrame

    try:
        # Ensure the output directory exists
        output_excel_path.parent.mkdir(parents=True, exist_ok=True)
        # Save the DataFrame to Excel, overwriting the file
        df_to_save.to_excel(output_excel_path, index=False, engine='openpyxl')
        # Use len(data_to_save) which is accurate even when DataFrame is mocked
        logging.info(f"Successfully saved processed data for {len(data_to_save)} companies to {output_excel_path}")
    except Exception as e:
        logging.error(f"Failed to save processed data to Excel file '{output_excel_path}': {e}", exc_info=True)

# --- Original save_data_to_excel logic (commented out) ---
# (Keep commented or remove if not needed)
# import openpyxl
# from typing import Dict
# def save_data_to_excel_append_mode(data_dict: Dict[str, any], filename: str):
#     # ... (original append logic) ...
#     pass