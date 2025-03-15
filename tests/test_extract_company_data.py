import pytest
import pandas as pd
from src.models.extract_company_data import extract_company_data
import os

@pytest.fixture
def test_excel_file(tmp_path):
    # Create a temporary Excel file for testing
    data = {
        'Company': ['Company A', 'Company B', 'Company C', 'Company D', 'Company E'],
        'Website': ['example.com', '  http://example.org ', 'example.net', None, ''],
        'Recipient_Email': ['a@example.com', 'b@example.org', 'c@example.net', None, ''],
        'Contact Person': ['John Doe', 'Jane Smith', '  ', 'Peter Jones', ''],
        'Process' : ['yes', 'yes', 'no', 'yes', 'No']
    }
    df = pd.DataFrame(data)
    file_path = tmp_path / "test_data.xlsx"
    df.to_excel(file_path, index=False)
    return str(file_path)


def test_extract_company_data_success(test_excel_file):
    extracted_data = extract_company_data(test_excel_file)
    assert len(extracted_data) == 2  # Only 2 rows should be valid
    assert extracted_data[0]['website'] == 'https://example.com'
    assert extracted_data[0]['recipient_email'] == 'a@example.com'
    assert extracted_data[0]['contact person'] == 'John Doe'
    assert extracted_data[1]['website'] == 'http://example.org' # Check http
    assert extracted_data[1]['recipient_email'] == 'b@example.org'
    assert extracted_data[1]['contact person'] == 'Jane Smith'

def test_extract_company_data_file_not_found():
    result = extract_company_data("nonexistent_file.xlsx")
    assert result == []

def test_extract_company_data_missing_columns(tmp_path):
    # Create a test file without 'Website' column.
    data = {'Recipient_Email': ['test@test.com'], 'Contact Person': ['Test User']}
    df = pd.DataFrame(data)
    file_path = tmp_path / 'missing_col.xlsx'
    df.to_excel(file_path, index=False)
    result = extract_company_data(str(file_path))
    assert result == [] # Should return empty list if columns missing.

def test_extract_company_data_empty_file(tmp_path):
    # Create an empty excel file.
    file_path = tmp_path / "empty.xlsx"
    df = pd.DataFrame()
    df.to_excel(file_path, index=False)
    result = extract_company_data(str(file_path))
    assert result == [] 