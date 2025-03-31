 # tests/utils/test_excel_writer_to_save_data.py
import pytest
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, ANY

# Import the function to test and its dependencies
from src.utils.excel_writer_to_save_data import save_processed_data
# Need TargetCompanyData from core
from src.core.target_company_data import TargetCompanyData
# Need CooperationPoint if creating TargetCompanyData instances
from src.core.developing_letter import CooperationPoint

# --- Test Fixtures ---

@pytest.fixture
def sample_processed_companies() -> list[TargetCompanyData]:
    """Provides a list of sample TargetCompanyData objects."""
    return [
        TargetCompanyData(
            website="http://companya.com", recipient_email="a@companya.com",
            company_name="Company A", contact_person="Alice", process_flag="yes",
            main_business="Software", cooperation_points_str="Point A1; Point A2",
            generated_letter_subject="Subject A", generated_letter_body="<p>Body A</p>",
            processing_status="Success", draft_id="draft_a1"
        ),
        TargetCompanyData(
            website="http://companyb.net", recipient_email="b@companyb.net",
            company_name="Company B", contact_person="Bob", process_flag="no", # Note: process_flag doesn't affect saving
            main_business="Hardware", cooperation_points_str="Point B1",
            generated_letter_subject=None, generated_letter_body=None, # Test None values
            processing_status="Skipped", draft_id=None
        )
    ]

@pytest.fixture
def mock_datetime():
    """Fixture to mock datetime.now()"""
    frozen_time = datetime(2025, 3, 30, 8, 0, 0) # Use current date from prompt context
    with patch('src.utils.excel_writer_to_save_data.datetime') as mock_dt:
        mock_dt.now.return_value = frozen_time
        yield frozen_time # Return the frozen time for assertions

# --- Test Cases ---

# Patch pandas DataFrame and its methods globally for this test file if desired,
# or patch within specific tests. Patching to_excel is key.
@patch('src.utils.excel_writer_to_save_data.pd.DataFrame')
def test_save_processed_data_success(mock_dataframe_cls, sample_processed_companies, tmp_path, mock_datetime, caplog):
    """Test successful saving of data to Excel."""
    mock_df_instance = MagicMock()
    mock_dataframe_cls.return_value = mock_df_instance
    output_path = tmp_path / "output" / "results.xlsx"

    with caplog.at_level(logging.INFO):
        # Mock mkdir to avoid actual directory creation if needed,
        # though tmp_path handles cleanup. Patching avoids potential permission issues.
        with patch.object(Path, 'mkdir') as mock_mkdir:
             save_processed_data(sample_processed_companies, output_path)

    # 1. Check DataFrame Creation
    mock_dataframe_cls.assert_called_once()
    call_args, call_kwargs = mock_dataframe_cls.call_args
    data_passed = call_args[0]
    columns_passed = call_kwargs.get('columns')

    # Check number of records
    assert len(data_passed) == len(sample_processed_companies)

    # Check timestamp in data (using the frozen time)
    expected_timestamp = mock_datetime.strftime("%Y/%m/%d %H:%M:%S")
    assert data_passed[0]['saving_file_time'] == expected_timestamp
    assert data_passed[1]['saving_file_time'] == expected_timestamp

    # Check some key data points and None handling
    assert data_passed[0]['company_name'] == "Company A"
    assert data_passed[0]['draft_id'] == "draft_a1"
    assert data_passed[1]['company_name'] == "Company B"
    assert data_passed[1]['generated_letter_subject'] is None # Check None is preserved
    assert data_passed[1]['draft_id'] is None

    # Check columns passed to DataFrame constructor
    expected_columns = [
        'saving_file_time', 'company_name', 'website', 'main_business',
        'recipient_email', 'contact_person', 'cooperation_points_str',
        'generated_letter_subject', 'generated_letter_body',
        'processing_status', 'draft_id'
    ]
    assert columns_passed == expected_columns

    # 2. Check Directory Creation
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    # 3. Check Excel Saving
    mock_df_instance.to_excel.assert_called_once_with(
        output_path, index=False, engine='openpyxl'
    )

    # 4. Check Logging
    assert f"Successfully saved processed data for {len(sample_processed_companies)} companies" in caplog.text
    assert str(output_path) in caplog.text


@patch('src.utils.excel_writer_to_save_data.pd.DataFrame')
def test_save_processed_data_empty_list(mock_dataframe_cls, tmp_path, caplog):
    """Test behavior when the input list is empty."""
    mock_df_instance = MagicMock()
    mock_dataframe_cls.return_value = mock_df_instance
    output_path = tmp_path / "empty_results.xlsx"

    with caplog.at_level(logging.INFO):
         save_processed_data([], output_path)

    # Verify DataFrame constructor and to_excel were NOT called
    mock_dataframe_cls.assert_not_called()
    mock_df_instance.to_excel.assert_not_called()

    # Verify log message
    assert "No processed company data to save." in caplog.text


@patch('src.utils.excel_writer_to_save_data.pd.DataFrame')
def test_save_processed_data_exception(mock_dataframe_cls, sample_processed_companies, tmp_path, caplog):
    """Test error handling when df.to_excel fails."""
    mock_df_instance = MagicMock()
    mock_dataframe_cls.return_value = mock_df_instance
    output_path = tmp_path / "error_output" / "results.xlsx"
    error_message = "Permission denied"
    mock_df_instance.to_excel.side_effect = Exception(error_message)

    with caplog.at_level(logging.ERROR):
        with patch.object(Path, 'mkdir'): # Mock mkdir as well
             save_processed_data(sample_processed_companies, output_path)

    # Verify to_excel was called
    mock_df_instance.to_excel.assert_called_once()

    # Verify error log
    assert f"Failed to save processed data to Excel file '{output_path}'" in caplog.text
    assert error_message in caplog.text