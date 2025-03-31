# src/data_access/excel_reader.py
"""Module for reading and processing data from Excel files."""
import logging
import pandas as pd
from pathlib import Path
from typing import List
from src.core import TargetCompanyData

logger = logging.getLogger(__name__)

def read_company_data(excel_file_path: Path) -> List[TargetCompanyData]:
    """
    Reads company data from Excel, cleans it, filters based on 'process' flag,
    validates required fields, and returns a list of TargetCompanyData objects.

    Args:
        excel_file_path: Path object pointing to the Excel file.

    Returns:
        List of TargetCompanyData objects. Returns an empty list on error or if no valid data found.
    """
    try:
        if not excel_file_path.is_file():
            logger.error(f"Excel file not found at: {excel_file_path}")
            return []

        # Read Excel, handle potential issues during read
        try:
            data = pd.read_excel(excel_file_path)
        except Exception as read_err:
            logger.error(f"Failed to read Excel file '{excel_file_path}' with pandas: {read_err}", exc_info=True)
            return []

        # Handle empty file case
        if data.empty:
            logger.info(f"Excel file '{excel_file_path}' is empty or contains no data.")
            return []

        # Normalize column names: strip whitespace, convert to lower case
        original_columns = list(data.columns)
        data.columns = data.columns.str.strip().str.lower()
        normalized_columns = list(data.columns)
        logger.info(f"Read Excel file: {excel_file_path}. Original Columns: {original_columns}, Normalized Columns: {normalized_columns}")

        # Define required columns (case-insensitive after normalization)
        required_columns = ['website', 'recipient_email', 'company', 'contact person', 'process']
        missing_cols = [col for col in required_columns if col not in data.columns]
        if missing_cols:
            logger.error(f"Error: Required columns missing in Excel file: {', '.join(missing_cols)}")
            return []

        company_data_list: List[TargetCompanyData] = []
        for index, row in data.iterrows():
            row_num = index + 2  # For user-friendly logging (Excel row number)

            # Use pandas methods for safer access and type handling (handles NaN)
            company_name_raw = row.get('company')
            website_raw = row.get('website')
            email_raw = row.get('recipient_email')
            contact_raw = row.get('contact person')
            process_flag_raw = row.get('process')

            # --- 1. Filter by Process Flag ---
            process_flag = str(process_flag_raw or '').strip()
            if process_flag.lower() != 'yes':
                logger.debug(f"Skipping row {row_num} for '{company_name_raw}' because process flag is '{process_flag_raw}'.")
                continue

            # --- 2. Validate Required Fields (handle None/NaN, empty strings after strip) ---
            company_name = str(company_name_raw or '').strip()
            if not company_name or pd.isna(company_name_raw):
                logger.warning(f"Skipping row {row_num} due to missing or invalid company name ('{company_name_raw}').")
                continue

            website = str(website_raw or '').strip()
            if not website or pd.isna(website_raw):
                logger.warning(f"Skipping row {row_num} for '{company_name}' due to missing or invalid website ('{website_raw}').")
                continue

            email = str(email_raw or '').strip()
            if not email or pd.isna(email_raw):
                logger.warning(f"Skipping row {row_num} for '{company_name}' due to missing or invalid email ('{email_raw}').")
                continue

            # Contact person can be empty/missing, handle gracefully
            contact = str(contact_raw or '').strip()
            if pd.isna(contact_raw):
                contact = ""  # Ensure empty string if original was NaN/None

            # --- 3. Clean/Prepare Data ---
            # Add "https://" prefix if missing *only if* it looks like a domain part exists
            if not website.startswith(("http://", "https://")) and '.' in website:
                website = "https://" + website

            # --- 4. Create TargetCompanyData object ---
            try:
                company_obj = TargetCompanyData(
                    website=website,
                    recipient_email=email,
                    company_name=company_name,
                    contact_person=contact,
                    process_flag=process_flag  # Store the stripped flag used for filtering
                )
                company_data_list.append(company_obj)
            except Exception as obj_err:
                logger.error(f"Error creating TargetCompanyData object for row {row_num} ('{company_name}'): {obj_err}", exc_info=True)
                continue

        logger.info(f"Successfully extracted and validated data for {len(company_data_list)} companies from '{excel_file_path}'.")
        return company_data_list

    except FileNotFoundError:
        logger.error(f"Error: File not found at {excel_file_path}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred processing Excel file '{excel_file_path}': {e}", exc_info=True)
        return []