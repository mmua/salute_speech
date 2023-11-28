from time import time
from io import FileIO
import uuid
from urllib.parse import urlencode
from salute_speech.utils.russian_certs import russian_secure_get, russian_secure_post


class UploadError(Exception):
    """Exception raised for errors during the file upload process."""
    pass

class InvalidResponseError(Exception):
    """Exception raised for invalid responses received from the server."""
    pass

class InvalidAudioFormatError(Exception):
    """Exception raised for invalid responses received from the server."""
    pass


class SpeechRecognitionTask:
    def __init__(self, result_data):
        self.id = result_data.get('id')
        self.created_at = result_data.get('created_at')
        self.updated_at = result_data.get('updated_at')
        self.status = result_data.get('status')


class SberSpeechRecognition:
    def __init__(self, client_credentials, base_url="https://smartspeech.sber.ru/rest/v1/"):
        """
        Initialize the Sber Speech Recognition client.

        :param api_key: API key for authentication.
        :param base_url: Base URL for the Sber Speech Recognition service.
        """
        self.client_credentials = client_credentials
        self.base_url = base_url
        self.token = None
        self.token_expiry = None


    def _get_headers(self, raw: bool=False) -> dict:
        """
        Generate the headers for the request.

        :param raw: No content type
        :return: A dictionary with the required headers.
        """
        if self.token_expiry is None or time() * 1000 > self.token_expiry:  # token_expiry in milliseconds
            self._get_token()
        
        headers = {
            "Authorization": f"Bearer {self.token}"    
        }
        if not raw:
            headers["Content-Type"] = "application/json"
        return headers

    def _get_token(self, scope="SALUTE_SPEECH_PERS", request_uid=None):
        """
        Retrieve the OAuth token.
        https://developers.sber.ru/docs/ru/salutespeech/authentication

        :return: The access token.
        """

        if request_uid is None:
            request_uid = str(uuid.uuid4())  # need hyphens in uuid

        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        headers = {
            "Authorization": f"Basic {self.client_credentials}",
            "RqUID": request_uid,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = urlencode({
            "scope": scope
        })
        response = russian_secure_post(url, headers=headers, data=data)
        if response.status_code != 200:
            raise Exception(f"Failed to request auth token: {response.text}")
        response_json = response.json()
        self.token = response_json["access_token"]
        self.token_expiry = int(response_json["expires_at"])
        return self.token, self.token_expiry

    def _handle_upload_response_errors(self, response):
        """Handle potential errors in the response."""
        if response.status_code != 200:
            raise UploadError(f"Failed to upload file, HTTP Status Code: {response.status_code}, Response: {response.text}")

        response_json = response.json()
        if response_json.get('status') != 200:
            raise UploadError(f"Failed to upload file, Response Status: {response_json.get('status')}, Response: {response.text}")

        if 'result' not in response_json or 'request_file_id' not in response_json['result']:
            raise InvalidResponseError(f"Unexpected response format: {response_json}")

        return response_json

    def upload_file(self, audio_file: FileIO) -> str:
        """
        Upload an audio file to the Sber Speech Recognition service.

        :param audio_file_path: Path to the audio file.
        :return: request_file_id.
        """
        url = self.base_url + "data:upload"
        headers = self._get_headers(raw=True)

        response = russian_secure_post(url, headers=headers, data=audio_file)
        if response.status_code != 200:
            raise Exception(f"Failed to upload file: {response.text}")
        
        response_json = self._handle_upload_response_errors(response)
        return response_json['result']['request_file_id']


    def _validate_audio_params(self, audio_encoding, sample_rate, channels_count):
        """
        Validate audio parameters according to the Sber Speech API documentation.
        https://developers.sber.ru/docs/ru/salutespeech/recognition/encodings

        :param audio_encoding: The encoding of the audio file.
        :param sample_rate: The sample rate of the audio file.
        :param channels_count: The number of channels in the audio file.
        """
        valid_encodings = ['PCM_S16LE', 'OPUS', 'MP3', 'FLAC', 'ALAW', 'MULAW']
        if audio_encoding not in valid_encodings:
            raise ValueError(f"Invalid audio encoding: {audio_encoding}")

        if audio_encoding in ['PCM_S16LE', 'ALAW', 'MULAW']:
            if not (8000 <= sample_rate <= 96000):
                raise ValueError(f"Invalid sample rate for {audio_encoding}: {sample_rate}")
            if channels_count > 8:
                raise ValueError(f"Too many channels for {audio_encoding}: {channels_count}")

        if audio_encoding == 'OPUS' and channels_count != 1:
            raise ValueError("OPUS supports only single channel audio.")

        if audio_encoding == 'MP3' and channels_count > 2:
            raise ValueError("MP3 supports up to 2 channels only.")

        if audio_encoding == 'FLAC' and channels_count > 8:
            raise ValueError(f"Too many channels for FLAC: {channels_count}")

    def async_recognize(self, request_file_id, language="ru-RU", audio_encoding="PCM_S16LE", sample_rate=16000, 
                        hypotheses_count=1, enable_profanity_filter=False, max_speech_timeout="20s", 
                        channels_count=2, no_speech_timeout="7s", hints=None, insight_models=None, 
                        speaker_separation_options=None):
        """
        Transcribe audio using Sber Speech Recognition service.

        :param request_file_id: ID of the uploaded file.
        :param language: Language for speech recognition.
        :param audio_encoding: Audio codec.
        :param sample_rate: Sample rate.
        :param hypotheses_count: Number of alternative hypotheses.
        :param enable_profanity_filter: Enable profanity filter.
        :param max_speech_timeout: Max speech timeout.
        :param channels_count: Number of channels in multi-channel audio.
        :param no_speech_timeout: No speech timeout.
        :param hints: Hints for speech recognition.
        :param insight_models: Insight models.
        :param speaker_separation_options: Speaker separation options.
        :return: Response from the server.
        """

        self._validate_audio_params(audio_encoding, sample_rate, channels_count)
        url = self.base_url + "speech:async_recognize"
        headers = self._get_headers()

        data = {
            "options": {
                "language": language,
                "audio_encoding": audio_encoding,
                "sample_rate": sample_rate,
                "hypotheses_count": hypotheses_count,
                "enable_profanity_filter": enable_profanity_filter,
                "max_speech_timeout": max_speech_timeout,
                "channels_count": channels_count,
                "no_speech_timeout": no_speech_timeout,
                "hints": hints or {},
                "insight_models": insight_models or [],
                "speaker_separation_options": speaker_separation_options or {}
            },
            "request_file_id": request_file_id
        }

        response = russian_secure_post(url, headers=headers, json=data)

        if response.status_code != 200:
            raise Exception(f"Failed to initiate speech recognition: {response.text}")

        response_json = response.json()
        if 'status' in response_json and response_json['status'] != 200:
            raise Exception(f"Failed to initiate speech recognition: {response.text}")

        return SpeechRecognitionTask(response_json.get('result'))

    def get_task_status(self, task_id):
        """
        Retrieve the status of a speech recognition task.

        :param task_id: The ID of the task.
        :return: The status of the task along with additional information.
        """
        url = self.base_url + "task:get"
        params = {'id': task_id}
        headers = self._get_headers()

        response = russian_secure_get(url, headers=headers, params=params)

        if response.status_code != 200:
            raise Exception(f"Failed to get task status: {response.text}")

        response_json = response.json()
        if 'status' in response_json and response_json['status'] != 200:
            raise Exception(f"Failed to get task status: {response.text}")

        return response_json.get('result')

    def download_result(self, response_file_id: str, output_file: FileIO):
        """
        Download the result file from the Sber Speech Recognition service.

        :param response_file_id: The ID of the file to download.
        :param output_path: Path where the downloaded file will be saved.
        """
        url = self.base_url + "data:download"
        params = {'response_file_id': response_file_id}
        headers = self._get_headers()

        response = russian_secure_get(url, headers=headers, params=params)

        if response.status_code != 200:
            raise Exception(f"Failed to download the file: {response.text}")

        # Save the file content to output_file
        output_file.write(response.content)
