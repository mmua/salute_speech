import unittest
from unittest.mock import patch, MagicMock
import uuid
from salute_speech.speech_recognition import SberSpeechRecognition
from salute_speech.utils.token import TokenManager
from salute_speech.exceptions import TokenRequestError, TokenParsingError


class TestSberSpeechRecognitionTokenRetrieval(unittest.TestCase):
    def setUp(self):
        self.client_credentials = "Base64EncodedClientCredentials"
        self.sber_speech = SberSpeechRecognition(self.client_credentials)

    @patch('salute_speech.utils.token.russian_secure_post')
    def test_token_manager_get_valid_token(self, mock_post):
        # Prepare a mock response object for the token retrieval
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "expires_at": 1000000  # Arbitrary expiration time
        }
        mock_post.return_value = mock_response

        # Get a valid token
        token = self.sber_speech.token_manager.get_valid_token()

        # Assert the token is correct
        self.assertEqual(token, "test_access_token")
        
        # Verify the token manager has stored the token and expiry
        self.assertEqual(self.sber_speech.token_manager.token, "test_access_token")
        self.assertEqual(self.sber_speech.token_manager.token_expiry, 1000000)

    @patch('salute_speech.utils.token.russian_secure_post')
    def test_token_manager_refresh_token(self, mock_post):
        # Prepare a mock response object for the token retrieval
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_test_access_token",
            "expires_at": 2000000  # New expiration time
        }
        mock_post.return_value = mock_response

        # Force refresh the token
        self.sber_speech.token_manager._refresh_token("SALUTE_SPEECH_PERS")

        # Assert the token and expiry are updated
        self.assertEqual(self.sber_speech.token_manager.token, "new_test_access_token")
        self.assertEqual(self.sber_speech.token_manager.token_expiry, 2000000)

    @patch('salute_speech.utils.token.russian_secure_post')
    def test_token_request_error(self, mock_post):
        # Prepare a mock error response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "unauthorized"}
        mock_post.return_value = mock_response

        # Assert that TokenRequestError is raised
        with self.assertRaises(TokenRequestError):
            self.sber_speech.token_manager.get_valid_token()

    @patch('salute_speech.utils.token.russian_secure_post')
    def test_token_parsing_error(self, mock_post):
        # Prepare a mock response with missing fields
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"some_other_field": "value"}
        mock_post.return_value = mock_response

        # Assert that TokenParsingError is raised
        with self.assertRaises(TokenParsingError):
            self.sber_speech.token_manager.get_valid_token()


# Run the tests
if __name__ == '__main__':
    unittest.main()