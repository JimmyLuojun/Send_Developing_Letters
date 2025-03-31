# tests/data_access/test_excel_reader.py
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock
# Ensure these imports are correct based on your actual file structure
from src.data_access.excel_reader import read_company_data
from src.core import TargetCompanyData

# Constants - represents the raw data in the fixture file
TEST_DATA_DICT = {
    'Company': [' Test A ', 'Company B', 'Company C', 'Company D', None, 'Company F'], # Row index 0-5
    ' Website ': [' example.com ', ' http://b.org ', 'c.net', None, 'e.com', 'f.com '],
    'recipient_email': ['a@a.com', ' b@b.org ', 'c@c.net', 'd@d.com', 'e@e.com', None],
    ' contact person ': [' Alice ', ' Bob ', ' ', ' Dave ', ' Eve ', ' Frank '],
    ' Process ': [' yes ', 'YES', 'no', 'Yes', ' Yes ', 'YES']
}

@pytest.fixture
def temp_excel_file(tmp_path):
    """Create a temporary Excel file with standard test data."""
    file_path = tmp_path / "test_data.xlsx"
    df = pd.DataFrame(TEST_DATA_DICT)
    df.to_excel(file_path, index=False)
    return file_path

@pytest.fixture
def temp_excel_missing_cols(tmp_path):
    """Create a temporary Excel file with missing required columns."""
    file_path = tmp_path / "missing_cols.xlsx"
    data = { # Missing email, contact, process
        'Company': ['Company A'],
        ' Website ': ['example.com'],
    }
    df = pd.DataFrame(data)
    df.to_excel(file_path, index=False)
    return file_path

@pytest.fixture
def temp_excel_empty(tmp_path):
    """Create a temporary empty Excel file (only headers)."""
    file_path = tmp_path / "empty.xlsx"
    # Ensure columns match what the function expects to avoid key errors if file was not truly empty
    df = pd.DataFrame(columns=[col.strip().lower() for col in TEST_DATA_DICT.keys()])
    df.to_excel(file_path, index=False)
    return file_path

# --- Test Cases ---

def test_read_company_data_success(temp_excel_file):
    """Test reading valid rows meeting all criteria."""
    result = read_company_data(temp_excel_file)

    # EXPECTED VALID ROWS from TEST_DATA_DICT (Based on refined function logic):
    # Row 0 (A): All valid, process='yes' -> KEEP
    # Row 1 (B): All valid, process='YES' -> KEEP
    # Row 2 (C): process='no' -> SKIP
    # Row 3 (D): website=None -> SKIP
    # Row 4 (E): company=None -> SKIP
    # Row 5 (F): email=None -> SKIP
    # --> Expected Length = 2

    assert len(result) == 2 # FIX: Correct expected length
    assert all(isinstance(c, TargetCompanyData) for c in result)

    # Test Company A (should be present)
    comp_a = next((c for c in result if c.company_name == 'Test A'), None)
    assert comp_a is not None
    assert comp_a.website == "https://example.com"
    assert comp_a.recipient_email == "a@a.com"
    assert comp_a.company_name == "Test A"
    assert comp_a.contact_person == "Alice"
    assert comp_a.process_flag == "yes"

    # Test Company B (should be present)
    comp_b = next((c for c in result if c.company_name == 'Company B'), None)
    assert comp_b is not None
    assert comp_b.website == "http://b.org"
    assert comp_b.recipient_email == "b@b.org"
    assert comp_b.contact_person == "Bob"
    assert comp_b.process_flag == "YES"

    # Verify others were skipped (optional but good)
    assert not any(c.company_name == 'Company C' for c in result)
    assert not any(c.company_name == 'Company D' for c in result)
    assert not any(c.company_name == 'Company F' for c in result) # Name was 'Company F' in data

def test_read_company_data_file_not_found():
    """Test reading a non-existent file."""
    non_existent_path = Path("non/existent/file.xlsx")
    result = read_company_data(non_existent_path)
    assert result == []

def test_read_company_data_missing_columns(temp_excel_missing_cols):
    """Test reading a file with missing required columns."""
    result = read_company_data(temp_excel_missing_cols)
    assert result == []

def test_read_company_data_empty_file(temp_excel_empty):
    """Test reading an Excel file with headers but no data rows."""
    result = read_company_data(temp_excel_empty)
    assert result == []

@patch('pandas.read_excel', side_effect=Exception("Mocked pandas read error"))
def test_read_company_data_pandas_error(mock_read_excel, tmp_path):
    """Test handling of errors during pandas read_excel call."""
    dummy_path = tmp_path / "error.xlsx"
    dummy_path.touch()
    with patch('src.data_access.excel_reader.Path.is_file', return_value=True):
        result = read_company_data(dummy_path)
    assert result == []
    mock_read_excel.assert_called_once_with(dummy_path)

def test_read_company_data_invalid_process_flag():
    """Test that rows with invalid process flags are skipped."""
    df = pd.DataFrame(TEST_DATA_DICT)
    # Change flags: A='invalid', C='invalid', E='maybe'
    # Expected survivors based *only* on process flag: B(YES), D(Yes), F(YES)
    df.loc[df['Company'] == ' Test A ', ' Process '] = 'invalid'
    df.loc[df['Company'] == 'Company C', ' Process '] = 'invalid'
    df.loc[df['Company'] == 'Company E', ' Process '] = 'maybe' # E fails validation anyway

    dummy_path = Path("dummy_path_process.xlsx")
    # Patch read_excel AND the file existence check
    with patch('pandas.read_excel', return_value=df), \
         patch('src.data_access.excel_reader.Path.is_file', return_value=True):
        result = read_company_data(dummy_path)

    # Verify which ones actually pass ALL checks:
    # A: Skipped (process='invalid')
    # B: Keep (process='YES', valid fields)
    # C: Skipped (process='invalid')
    # D: Skipped (website=None)
    # E: Skipped (company=None, process='maybe')
    # F: Skipped (email=None)
    # --> Expected Length = 1 (Only B)

    assert len(result) == 1 # FIX: Expect only B
    assert result[0].company_name == 'Company B'
    # This check should now pass as only 'yes' (case-insensitive) flags survive
    assert all(c.process_flag.lower() == 'yes' for c in result)

def test_read_company_data_duplicate_emails():
    """Test that rows with duplicate emails are read if otherwise valid."""
    df = pd.DataFrame(TEST_DATA_DICT)
    # Make B's email same as A's ('a@a.com').
    # Both A and B have process='yes' and valid fields.
    df.loc[df['Company'] == 'Company B', 'recipient_email'] = ' a@a.com '

    dummy_path = Path("dummy_path_duplicates.xlsx")
    # Patch read_excel AND the file existence check
    with patch('pandas.read_excel', return_value=df), \
         patch('src.data_access.excel_reader.Path.is_file', return_value=True):
        result = read_company_data(dummy_path)

    # Verify both A and B are returned (D, E, F, C skipped for other reasons)
    assert len(result) == 2 # Correct: Expect A and B

    emails = [c.recipient_email for c in result]
    # Check that the duplicate email appears twice
    assert emails.count('a@a.com') == 2 # Correct
    # Ensure others are absent
    assert 'c@c.net' not in emails # Correct
    assert 'd@d.com' not in emails # Correct (D is skipped due to validation)

def test_read_company_data_malformed_urls():
    """Test handling of URLs during processing (prefixing)."""
    df = pd.DataFrame(TEST_DATA_DICT)
    # Change URLs for rows that should be processed (A, B)
    # A: 'no-scheme.com' -> becomes 'https://no-scheme.com'
    # B: 'http://already-has-scheme.org' -> remains unchanged
    df.loc[df['Company'] == ' Test A ', ' Website '] = 'no-scheme.com'
    df.loc[df['Company'] == 'Company B', ' Website '] = 'http://already-has-scheme.org'

    dummy_path = Path("dummy_path_urls.xlsx")
    # Patch read_excel AND the file existence check
    with patch('pandas.read_excel', return_value=df), \
         patch('src.data_access.excel_reader.Path.is_file', return_value=True):
        result = read_company_data(dummy_path)

    # Expected results: A and B (D, E, F, C skipped for other reasons)
    assert len(result) == 2 # Correct

    comp_a = next((c for c in result if c.company_name == 'Test A'), None)
    comp_b = next((c for c in result if c.company_name == 'Company B'), None)

    assert comp_a is not None # Correct
    assert comp_b is not None # Correct

    # Assert the actual prefixed/preserved values
    assert comp_a.website == 'https://no-scheme.com' # Correct
    assert comp_b.website == 'http://already-has-scheme.org' # Correct