# tests/test_workflow.py
import unittest
from unittest.mock import patch
from src.models.extract_company_data import extract_company_websites
from src.data.skyfend_business import read_skyfend_business
from src.models.business_extraction import extract_main_business
from src.models.identify_cooperation_points import identify_cooperation_points
from src.utils.generate_developing_letters import generate_developing_letter

class TestWorkflow(unittest.TestCase):

    def setUp(self):
        """Setup method to create common test data."""
        self.api_url = "https://testapi.example.com/extract_business"
        self.api_key = "test_api_key"

    def test_extract_company_websites(self):
        # Use the sample Excel file for testing
        sample_excel = "data/raw/test_to_read_website.xlsx"
        websites = extract_company_websites(sample_excel)
        self.assertIsInstance(websites, list)
        self.assertGreater(len(websites), 0)

    def test_read_skyfend_business(self):
        # Use the sample Word document for testing
        sample_docx = "data/raw/test_main Business of Skyfend.docx"
        business_description = read_skyfend_business(sample_docx)
        self.assertIsInstance(business_description, str)
        self.assertGreater(len(business_description), 0)

    @patch('src.models.business_extraction.requests.post')
    def test_extract_main_business(self, mock_post):
        # Mock a successful API response
        mock_post.return_value.json.return_value = {"business_name": "Test Business"}
        mock_post.return_value.raise_for_status.return_value = None  # Mock successful status

        # Corrected call to extract_main_business
        result = extract_main_business(self.api_url, self.api_key)  # Ensure only two arguments

        # Assertions to verify the output
        self.assertEqual(result, "Test Business")
        mock_post.assert_called_once_with(self.api_url, headers={'Authorization': 'Bearer ' + self.api_key})

    @patch('src.models.identify_cooperation_points.requests.post')
    def test_identify_cooperation_points(self, mock_post):
        # Mock the API response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'cooperation_points': 'Sample Cooperation Points'}

        result = identify_cooperation_points("Skyfend Business", "Target Business", "api_url", "api_key")
        self.assertEqual(result, 'Sample Cooperation Points')

    @patch('src.utils.generate_developing_letters.requests.post')
    def test_generate_developing_letter(self, mock_post):
        # Mock the API response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'letter_content': 'Sample Letter Content'}

        result = generate_developing_letter("Instructions", "Cooperation Points", "api_url", "api_key")
        self.assertEqual(result, 'Sample Letter Content')

if __name__ == '__main__':
    unittest.main()