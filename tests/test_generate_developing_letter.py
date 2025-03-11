import requests # Import the requests library to access exceptions
import unittest
from unittest.mock import patch, Mock
from src.utils.generate_developing_letters import generate_developing_letter

class TestGenerateDevelopingLetter(unittest.TestCase):

    @patch('src.utils.generate_developing_letters.requests.post')
    def test_generate_developing_letter_success(self, mock_post):
        instructions = "Write a formal letter."
        cooperation_points = "Enhanced cybersecurity solutions."
        api_url = "https://api.example.com/generate_letter"
        api_key = "test_api_key"

        expected_response = {'letter_content': 'This is a formal developing letter.'}
        mock_post.return_value = Mock(status_code=200)
        mock_post.return_value.json.return_value = expected_response

        result = generate_developing_letter(instructions, cooperation_points, api_url, api_key)

        self.assertEqual(result, expected_response['letter_content'])
        mock_post.assert_called_once_with(
            api_url,
            json={"instructions": instructions, "cooperation_points": cooperation_points},
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        )

    @patch('src.utils.generate_developing_letters.requests.post')
    def test_generate_developing_letter_failure(self, mock_post):
        instructions = "Write a formal letter."
        cooperation_points = "Enhanced cybersecurity solutions."
        api_url = "https://api.example.com/generate_letter"
        api_key = "test_api_key"

        mock_post.side_effect = requests.exceptions.RequestException("API request failed")

        result = generate_developing_letter(instructions, cooperation_points, api_url, api_key)

        self.assertEqual(result, 'No letter content generated')
        mock_post.assert_called_once()

if __name__ == '__main__':
    unittest.main()
