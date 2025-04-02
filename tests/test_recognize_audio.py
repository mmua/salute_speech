import unittest
from time import time
from unittest.mock import patch, MagicMock
from salute_speech.speech_recognition import SberSpeechRecognition, SpeechRecognitionTask, SpeechRecognitionConfig
from salute_speech.utils.audio import AudioValidator
from salute_speech.exceptions import InvalidResponseError


class TestSberSpeechRecognitionAsyncRecognize(unittest.TestCase):
    def setUp(self):
        self.client_credentials = "Base64EncodedClientCredentials"
        self.sber_speech = SberSpeechRecognition(self.client_credentials)

    @patch('salute_speech.utils.token.TokenManager.get_valid_token')
    @patch('salute_speech.speech_recognition.russian_secure_post')
    def test_async_recognize(self, mock_secure_post, mock_get_token):
        # Setup token manager mock
        mock_get_token.return_value = "test-token"
        
        # Prepare a mock response object for async recognize
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status": 200, "result": {"id": "some-task-id", "created_at": "2021-07-15T17:35:17.182454861+03:00", "updated_at": "2021-07-15T17:35:57.18245504+03:00", "status": "NEW"}}'
        mock_response.json.return_value = {
            "status": 200,
            "result": {
                "id": "some-task-id",
                "created_at": "2021-07-15T17:35:17.182454861+03:00",
                "updated_at": "2021-07-15T17:35:57.18245504+03:00",
                "status": "NEW"
             }
        }
        mock_secure_post.return_value = mock_response

        # Call the async_recognize method
        response = self.sber_speech.async_recognize("test-file-id", "PCM_S16LE", 16000, 1, "ru-RU")

        # Assert the request was called correctly
        expected_data = {
            "options": {
                "language": "ru-RU",
                "audio_encoding": "PCM_S16LE",
                "sample_rate": 16000,
                "channels_count": 1,
                "hypotheses_count": 1,
                "enable_profanity_filter": False,
                "max_speech_timeout": "20s",
                "no_speech_timeout": "7s",
                "hints": {},
                "insight_models": [],
                "speaker_separation_options": {}
            },
            "request_file_id": "test-file-id"
        }
        
        mock_secure_post.assert_called_once()
        args, kwargs = mock_secure_post.call_args
        self.assertEqual(args[0], f"{self.sber_speech.base_url}speech:async_recognize")
        self.assertEqual(kwargs["headers"], {"Authorization": "Bearer test-token", "Content-Type": "application/json"})
        self.assertEqual(kwargs["json"], expected_data)

        # Assert the response is as expected
        self.assertEqual(response.id, "some-task-id")

# Run the tests
if __name__ == '__main__':
    unittest.main()
