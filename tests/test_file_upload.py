import unittest
from io import BytesIO
from unittest.mock import patch, MagicMock
from salute_speech.speech_recognition import SberSpeechRecognition
import datetime
from time import time
from salute_speech.utils.const import SALUTE_SPEECH_HTTP_TIMEOUT

from salute_speech.utils.package import get_config_path


class TestSberSpeechRecognition(unittest.TestCase):
    def setUp(self):
        self.client_credentials = "Base64EncodedClientCredentials"
        self.sber_speech = SberSpeechRecognition(self.client_credentials)
        self.sber_speech.token = "some-token"
        self.sber_speech.token_expiry = time() * 1000 + 10000

    @patch('requests.post')
    def test_upload_file(self, mock_post):
        # Prepare a mock response object
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": 200,
            "result": {
                "request_file_id": "1234-5678"
            }
        }
        mock_post.return_value = mock_response

        # Create a dummy file object
        dummy_file = BytesIO(b"test audio data")

        # Call the method
        response = self.sber_speech.upload_file(dummy_file)

        # Assert the request was called correctly
        mock_post.assert_called_with(
            "https://smartspeech.sber.ru/rest/v1/data:upload",
            timeout=SALUTE_SPEECH_HTTP_TIMEOUT,
            headers={"Authorization": f"Bearer {self.sber_speech.token}"},
            data=dummy_file,
            verify=get_config_path('russian.pem')
        )

        # Assert the response is as expected
        self.assertEqual(response, "1234-5678")

# Run the tests
if __name__ == '__main__':
    unittest.main()