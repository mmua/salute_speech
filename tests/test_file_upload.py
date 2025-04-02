import unittest
from io import BytesIO, FileIO
from unittest.mock import patch, MagicMock
from salute_speech.speech_recognition import SberSpeechRecognition
from salute_speech.exceptions import InvalidResponseError


class TestSberSpeechRecognition(unittest.TestCase):
    def setUp(self):
        self.client_credentials = "Base64EncodedClientCredentials"
        self.sber_speech = SberSpeechRecognition(self.client_credentials)

    @patch('salute_speech.utils.token.TokenManager.get_valid_token')
    @patch('salute_speech.speech_recognition.russian_secure_post')
    def test_upload_file(self, mock_post, mock_get_token):
        # Setup token manager mock
        mock_get_token.return_value = "test-token"

        # Prepare a mock response object
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status": 200, "result": {"request_file_id": "1234-5678"}}'
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
        request_file_id = self.sber_speech.upload_file(dummy_file)

        # Assert the request was called correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://smartspeech.sber.ru/rest/v1/data:upload")
        self.assertEqual(kwargs["headers"], {"Authorization": "Bearer test-token"})
        self.assertEqual(kwargs["data"], dummy_file)

        # Assert the response is as expected
        self.assertEqual(request_file_id, "1234-5678")

    @patch('salute_speech.utils.token.TokenManager.get_valid_token')
    @patch('salute_speech.speech_recognition.russian_secure_post')
    def test_upload_file_missing_fields(self, mock_post, mock_get_token):
        # Setup token manager mock
        mock_get_token.return_value = "test-token"

        # Prepare a mock response object with missing fields
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status": 200, "result": {}}'
        mock_response.json.return_value = {
            "status": 200,
            "result": {
                # Missing request_file_id
            }
        }
        mock_post.return_value = mock_response

        # Create a dummy file object
        dummy_file = BytesIO(b"test audio data")

        # Assert that InvalidResponseError is raised
        with self.assertRaises(InvalidResponseError):
            self.sber_speech.upload_file(dummy_file)

    @patch('salute_speech.utils.token.TokenManager.get_valid_token')
    @patch('salute_speech.speech_recognition.russian_secure_post')
    def test_upload_file_type_validation(self, mock_post, mock_get_token):
        # Setup token manager mock
        mock_get_token.return_value = "test-token"

        # Prepare a mock response object
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status": 200, "result": {"request_file_id": "1234-5678"}}'
        mock_response.json.return_value = {
            "status": 200,
            "result": {
                "request_file_id": "1234-5678"
            }
        }
        mock_post.return_value = mock_response

        # Create a FileIO object
        dummy_file = MagicMock(spec=FileIO)

        # Call the method
        request_file_id = self.sber_speech.upload_file(dummy_file)

        # Assert the response is as expected
        self.assertEqual(request_file_id, "1234-5678")


# Run the tests
if __name__ == '__main__':
    unittest.main()
