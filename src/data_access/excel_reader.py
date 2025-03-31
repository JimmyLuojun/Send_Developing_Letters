# src/data_access/excel_reader.py
"""Module for reading and processing data from Excel files."""
import logging
import pandas as pd
from pathlib import Path
from typing import List
from src.core import TargetCompanyData # Keep this import

logger = logging.getLogger(__name__)

def read_company_data(file_path: Path) -> List[TargetCompanyData]:
    """
    Reads company data from an Excel file and returns a list of TargetCompanyData objects.
    Handles optional language column for manual language specification.
    """
    try:
        # Use openpyxl, handle potential NaN values gracefully during read
        df = pd.read_excel(file_path, engine='openpyxl', keep_default_na=False, na_values=[''])
        logging.info(f"Read Excel file: {file_path}. Original Columns: {list(df.columns)}")
    except FileNotFoundError:
        logging.error(f"Excel file not found at {file_path}")
        return []
    except Exception as e:
        logging.error(f"Failed to read Excel file {file_path}: {e}", exc_info=True)
        return []

    # --- Normalize columns ---
    original_columns = list(df.columns)
    df.columns = [str(col).strip().lower() for col in df.columns]
    normalized_columns = list(df.columns)
    logging.info(f"Normalized Columns: {normalized_columns}")

    companies = []
    required_columns = ['company', 'website', 'recipient_email', 'process']
    if not all(col in normalized_columns for col in required_columns):
        missing = [col for col in required_columns if col not in normalized_columns]
        logging.error(f"Missing required columns in Excel file after normalization: {missing}. Check headers.")
        return []

    # --- Check for optional language column ---
    language_column_present = 'language' in normalized_columns
    if language_column_present:
        logging.info("Optional 'language' column found in Excel.")
    else:
        logging.info("Optional 'language' column not found. Auto-detection will be used if needed.")

    for index, row in df.iterrows():
        try:
            # Read values as strings, strip whitespace
            company_name = str(row.get('company', '')).strip()
            website = str(row.get('website', '')).strip()
            recipient_email = str(row.get('recipient_email', '')).strip()
            # Get the 'process' value as a string directly
            process_flag_str = str(row.get('process', '')).strip() # Get the raw string value
            contact_person_str = str(row.get('contact person', '')).strip()

            # Basic validation for essential fields
            if not company_name or not website or not recipient_email:
                 logging.warning(f"Skipping row {index + 2} due to missing essential data (Company, Website, or Email).")
                 continue

            # --- Read Manual Language ---
            manual_language = None
            if language_column_present and 'language' in row and pd.notna(row['language']):
                lang_val = str(row['language']).strip().lower()
                if (len(lang_val) == 2) or (len(lang_val) == 5 and '-' in lang_val):
                    manual_language = lang_val
                    logging.debug(f"Using manual language '{manual_language}' from Excel for {company_name}")
                elif lang_val: # Only warn if non-empty but invalid
                    logging.warning(f"Invalid language code format '{lang_val}' in Excel row {index + 2} for {company_name}. Ignoring.")
            # --- End Read Manual Language ---

            # Create the TargetCompanyData object using the correct keyword 'process_flag'
            company_obj = TargetCompanyData(
                company_name=company_name,
                website=website,
                recipient_email=recipient_email,
                # vvv THE ONLY SIGNIFICANT CHANGE IS HERE vvv
                process_flag=process_flag_str, # Pass the string value with the keyword 'process_flag'
                # ^^^ THE ONLY SIGNIFICANT CHANGE IS HERE ^^^
                contact_person=contact_person_str or None, # Use None if empty string
                target_language=manual_language,
                # Initialize other fields (already matches TargetCompanyData defaults)
                # main_business=None, # Not needed if default is None
                # cooperation_points_str=None, # Not needed if default is None
                # generated_letter_subject=None, # Not needed if default is None
                # generated_letter_body=None, # Not needed if default is None
                # processing_status=None, # Not needed if default is None
                # draft_id=None # Not needed if default is None
            )
            companies.append(company_obj)

        except KeyError as e:
             # Log which column is missing if it's one we explicitly access
             logging.error(f"Missing expected column key '{e}' while processing row {index + 2}. Check Excel headers. Skipping row.")
        except Exception as e:
            # Log other unexpected errors during row processing
            logging.error(f"Unexpected error processing row {index + 2} in Excel: {e}", exc_info=True)

    logging.info(f"Successfully created {len(companies)} company data objects from '{file_path}'.")
    return companies