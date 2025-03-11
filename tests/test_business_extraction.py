# tests/test_business_extraction.py
import unittest
from unittest.mock import patch
import requests
import requests_mock
from src.models.business_extraction import extract_main_business

class TestBusinessExtraction(unittest.TestCase):
    def setUp(self):
        """Setup method to create common test data."""
        self.api_url = "https://testapi.example.com/extract_business"
        self.api_key = "test_api_key"

    @patch('src.models.business_extraction.requests.post')
    def test_extract_main_business_success(self, mock_post):
        """Test successful extraction of main business."""
        mock_post.return_value.json.return_value = {"business_name": "Test Business"}
        mock_post.return_value.raise_for_status.return_value = None  # Mock successful status
        main_business = extract_main_business(self.api_url, self.api_key)
        self.assertEqual(main_business, "Test Business")
        mock_post.assert_called_once_with(self.api_url, headers={'Authorization': 'Bearer test_api_key'})

    @patch('src.models.business_extraction.requests.post')
    def test_extract_main_business_empty_response(self, mock_post): # test_extract_main_business_empty_response(self, mock_post) is a test method that tests the extract_main_business function when the API response is empty
        """Test handling of empty API response."""
        mock_post.return_value.json.return_value = {}  # Empty response
        mock_post.return_value.raise_for_status.return_value = None
        main_business = extract_main_business(self.api_url, self.api_key)
        self.assertEqual(main_business, "Unknown")
        mock_post.assert_called_once_with(self.api_url, headers={'Authorization': 'Bearer test_api_key'})

    @patch('src.models.business_extraction.requests.post')
    def test_extract_main_business_api_error(self, mock_post):
        """Test handling of API error (e.g., 500 Internal Server Error)."""
        mock_post.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        main_business = extract_main_business(self.api_url, self.api_key)
        self.assertIsNone(main_business)
        mock_post.assert_called_once_with(self.api_url, headers={'Authorization': 'Bearer test_api_key'})

    @patch('src.models.business_extraction.requests.post')
    def test_extract_main_business_connection_error(self, mock_post):
        """Test handling of connection error."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Mock Connection Error")
        main_business = extract_main_business(self.api_url, self.api_key)
        self.assertIsNone(main_business)
        mock_post.assert_called_once_with(self.api_url, headers={'Authorization': 'Bearer test_api_key'})

    def test_extract_main_business_with_mock_success(self):
        """Test successful extraction with requests_mock."""
        with requests_mock.Mocker() as m:
            # Mock a successful response
            m.post(self.api_url, json={'business_name': 'Mock Business Info'}, status_code=200)

            # Test with a successful response
            result_success = extract_main_business(self.api_url, self.api_key)
            self.assertEqual(result_success, 'Mock Business Info')

    def test_extract_main_business_with_mock_error(self):#
        """Test error handling with requests_mock."""
        with requests_mock.Mocker() as m:
            # Mock an error response
            mock_response = requests.Response()
            mock_response.status_code = 500
            mock_response._content = b'Internal Server Error'
            m.post(self.api_url, exc=requests.exceptions.HTTPError("500 Server Error", response=mock_response))

            # Test with an error response
            result_error = extract_main_business(self.api_url, self.api_key)
            self.assertIsNone(result_error)