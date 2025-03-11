import unittest
from unittest.mock import patch, Mock
from src.models.identify_cooperation_points import identify_cooperation_points
from requests.exceptions import RequestException

class TestIdentifyCooperationPoints(unittest.TestCase):

    @patch('src.models.identify_cooperation_points.requests.post')
    def test_identify_cooperation_points_success(self, mock_post):
        skyfend_business = "Skyfend specializes in cybersecurity solutions."
        target_business = "The target company provides cloud storage services."
        api_url = "https://api.example.com/identify_cooperation"
        api_key = "test_api_key"

        expected_response = {'cooperation_points': 'Cybersecurity enhancements for cloud storage.'}
        mock_post.return_value = Mock(status_code=200)
        mock_post.return_value.json.return_value = expected_response

        result = identify_cooperation_points(skyfend_business, target_business, api_url, api_key)

        self.assertEqual(result, expected_response['cooperation_points'])
        mock_post.assert_called_once_with(
            api_url,
            json={"skyfend_business": skyfend_business, "target_business": target_business},
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        )

    @patch('src.models.identify_cooperation_points.requests.post')
    def test_identify_cooperation_points_failure(self, mock_post):
        skyfend_business = "Skyfend specializes in cybersecurity solutions."
        target_business = "The target company provides cloud storage services."
        api_url = "https://api.example.com/identify_cooperation"
        api_key = "test_api_key"

        mock_post.side_effect = RequestException("API request failed")

        result = identify_cooperation_points(skyfend_business, target_business, api_url, api_key)

        self.assertEqual(result, 'No cooperation points identified')
        mock_post.assert_called_once()

if __name__ == '__main__':
    unittest.main()
