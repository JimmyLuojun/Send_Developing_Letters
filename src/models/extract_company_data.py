# /Users/junluo/Documents/Send_Developing_Letters/src/models/extract_company_data.py
import pandas as pd
from typing import List, Dict

def extract_company_data(excel_file_path: str) -> List[Dict]:
    """
    Extracts company data (website, recipient email, contact person) from Excel.

    Args:
        excel_file_path: Path to the Excel file.

    Returns:
        List of dictionaries, each with 'website', 'recipient_email', 'company', and 'contact_person' keys.
        Returns an empty list on error.
    """
    try:
        data = pd.read_excel(excel_file_path)
        data.columns = data.columns.str.strip().str.lower()

        required_columns = ['website', 'recipient_email', 'company', 'contact person']
        if not all(col in data.columns for col in required_columns):
            print(f"Error: Required columns ({', '.join(required_columns)}) not found.")
            return []

        # --- Validation and Cleaning ---
        # Use a boolean mask for valid rows, handling missing/empty values:
        valid_mask = (
            data['website'].notna() &
            (data['website'].astype(str).str.strip() != "") &
            data['recipient_email'].notna() &
            (data['recipient_email'].astype(str).str.strip() != "") &
            (data['contact person'].notna()) &
            (data['process'].astype(str).str.lower() == 'yes')
        )

        valid_data = data.loc[valid_mask, ['website', 'recipient_email', 'company', 'contact person']].astype(str)

        def add_https(url):
            if not url.startswith(("http://", "https://")):
                return "https://" + url
            return url

        valid_data['website'] = valid_data['website'].str.strip().apply(add_https)
        valid_data['recipient_email'] = valid_data['recipient_email'].str.strip()
        valid_data['contact person'] = valid_data['contact person'].str.strip() # Strip whitespace

        return valid_data.to_dict('records')

    except FileNotFoundError:
        print(f"Error: File not found at {excel_file_path}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []

# Example Usage (for testing):
if __name__ == '__main__':
    # Create a sample DataFrame (for testing purposes)
    data = {
        'Company': ['Company A', 'Company B', 'Company C', 'Company D', 'Company E'],
        'Website': ['example.com', '  http://example.org ', 'example.net\n\n', None, ''],
        'Recipient_Email': ['a@example.com', 'b@example.org', 'c@example.net', None, ''],
		'Contact Person': ['John Doe', 'Jane Smith', '  ', 'Peter Jones', ''],
        'Process' : ['yes', 'yes', 'no', 'yes', 'No']
    }
    df = pd.DataFrame(data)

    # Create a temporary Excel file (for testing)
    test_excel_file = 'test_websites.xlsx'
    df.to_excel(test_excel_file, index=False)

    # Extract websites
    extracted_data = extract_company_data(test_excel_file)
    print(f"Extracted Data: {extracted_data}")  # Expected Output

    # Clean up the temporary file (for testing)
    import os
    os.remove(test_excel_file)