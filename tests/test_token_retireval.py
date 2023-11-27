import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import urlencode
from salute_speech.speech_recognition import SberSpeechRecognition
from salute_speech.utils.package import get_config_path


class TestSberSpeechRecognitionTokenRetrieval(unittest.TestCase):
    def setUp(self):
        self.client_credentials = "Base64EncodedClientCredentials"
        self.sber_speech = SberSpeechRecognition(self.client_credentials)

    @patch('requests.post')
    def test_get_token(self, mock_post):
        # Prepare a mock response object for the token retrieval
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "expires_at": 1000000  # Arbitrary expiration time
        }
        mock_post.return_value = mock_response

        request_id = "unique-request-id"
        # Call the _get_token method
        self.sber_speech._get_token(request_uid=request_id)

        # Assert the request was called correctly
        mock_post.assert_called_with(
            "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            verify=get_config_path('russian.pem'),
            headers={
                "Authorization": f"Basic {self.client_credentials}",
                "RqUID": request_id,  # This should match the value in your class
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data=urlencode({
                "scope": "SALUTE_SPEECH_PERS"
            })
        )

        # Assert the token and expiry are set correctly
        self.assertEqual(self.sber_speech.token, "test_access_token")
        self.assertTrue(self.sber_speech.token_expiry is not None)

# Run the tests
if __name__ == '__main__':
    unittest.main()