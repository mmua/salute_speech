"""
This module provides a client for interacting with the Sber Speech Recognition service.

The SberSpeechRecognition class offers methods to upload audio files, start speech recognition tasks,
and retrieve their results. It handles authentication and token management internally.
It also performs validation on audio parameters to ensure compatibility with the Sber Speech API.

This module also includes utility functions for making secure HTTP requests to the Sber service,
taking into account the necessary SSL certificate verification.

Example:
    To use the SberSpeechRecognition class, initialize it with client credentials and
    use its methods to upload audio files and initiate transcription tasks:

        from salute_speech.speech_recognition import SberSpeechRecognition

        sr_client = SberSpeechRecognition(client_credentials='YourClientCredentials')
        file_id = sr_client.upload_file(audio_file)
        task = sr_client.async_recognize(file_id)
        result = sr_client.get_task_status(task.id)
"""
from __future__ import annotations

import json
import logging
from time import time
from io import FileIO
import uuid
from urllib.parse import urlencode
from dataclasses import dataclass
from typing import Optional, BinaryIO
import asyncio
from salute_speech.utils.russian_certs import russian_secure_get, russian_secure_post
from dataclasses import dataclass
from typing import Optional, BinaryIO
import asyncio


import tempfile
import os
from pydub.utils import mediainfo

def _detect_audio_params(file: BinaryIO) -> tuple[str, int, int]:
    """
    Detect audio format parameters using pydub's mediainfo.
    Returns tuple of (audio_encoding, sample_rate, channels_count).
    
    Args:
        file: Audio file-like object
        
    Returns:
        tuple: (audio_encoding, sample_rate, channels_count)
        
    Raises:
        ValueError: If audio format is not supported
    """
    # Save current position
    current_pos = file.tell()
    file.seek(0)
    
    try:
        # Create a temporary file to handle the audio data
        with tempfile.NamedTemporaryFile(suffix='.audio', delete=False) as temp_file:
            temp_file.write(file.read())
            temp_path = temp_file.name
        
        try:
            # Get audio info using mediainfo
            info = mediainfo(temp_path)
            
            # Extract basic parameters
            audio_encoding = info['codec_name'].upper()
            sample_rate = int(info['sample_rate'])
            channels_count = int(info['channels'])
            
            # Map common codec names to Sber formats
            format_map = {
                'MP3': 'MP3',
                'OPUS': 'OPUS',
                'FLAC': 'FLAC',
                'PCM': 'PCM_S16LE',
                'ALAW': 'ALAW',
                'MULAW': 'MULAW',
                'WAV': 'PCM_S16LE'
            }
            
            # Map the codec to Sber format
            audio_encoding = format_map.get(audio_encoding, 'PCM_S16LE')
            
            # Validate parameters according to Sber's requirements
            if audio_encoding in ['PCM_S16LE', 'ALAW', 'MULAW']:
                if not (8000 <= sample_rate <= 96000):
                    logger.warning(
                        f"Sample rate {sample_rate}Hz out of range for {audio_encoding}, "
                        "resampling to 16000Hz"
                    )
                    sample_rate = 16000
                if channels_count > 8:
                    logger.warning(
                        f"Too many channels ({channels_count}) for {audio_encoding}, "
                        "using first 8 channels"
                    )
                    channels_count = 8
                    
            elif audio_encoding == 'OPUS':
                if channels_count != 1:
                    logger.warning("OPUS requires mono audio, using first channel")
                    channels_count = 1
                    
            elif audio_encoding == 'MP3':
                if channels_count > 2:
                    logger.warning(
                        f"Too many channels ({channels_count}) for MP3, using first 2 channels"
                    )
                    channels_count = 2
                    
            elif audio_encoding == 'FLAC':
                if channels_count > 8:
                    logger.warning(
                        f"Too many channels ({channels_count}) for FLAC, using first 8 channels"
                    )
                    channels_count = 8
            
            logger.debug(
                f"Detected audio parameters: {audio_encoding}, "
                f"{sample_rate}Hz, {channels_count} channels"
            )
            
            return audio_encoding, sample_rate, channels_count
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {temp_path}: {e}")
                
    finally:
        # Restore original file position
        file.seek(current_pos)

class UploadError(Exception):
    """Exception raised for errors during the file upload process."""


class InvalidResponseError(Exception):
    """Exception raised for invalid responses received from the server."""


class InvalidAudioFormatError(Exception):
    """Exception raised for invalid responses received from the server."""


class TokenRequestError(Exception):
    """Exception raised when the OAuth token request fails."""
    def __init__(self, status_code, message):
        super().__init__(f"Token request failed with status {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class TokenParsingError(Exception):
    """Exception raised when there is an issue parsing the token response."""


class FileUploadError(Exception):
    """Exception raised when file upload fails."""

    def __init__(self, message):
        super().__init__(message)


class SpeechRecognitionResponseError(Exception):
    """Exception raised for errors within the speech recognition response."""
    def __init__(self, message):
        super().__init__(message)


class TaskStatusResponseError(Exception):
    """Exception raised for errors within the task status response."""
    def __init__(self, message):
        super().__init__(message)


class SpeechRecognitionTask:
    def __init__(self, result_data):
        self.id = result_data.get('id')
        self.created_at = result_data.get('created_at')
        self.updated_at = result_data.get('updated_at')
        self.status = result_data.get('status')


class SpeechRecognitionConfig:
    def __init__(self, hypotheses_count: int = 1, enable_profanity_filter: bool = False,
                 max_speech_timeout: str = "20s", no_speech_timeout: str = "7s",
                 hints: (None | dict) = None, insight_models: (None | list) = None,
                 speaker_separation_options: (None | dict) = None):
        self.hypotheses_count = hypotheses_count
        self.enable_profanity_filter = enable_profanity_filter
        self.max_speech_timeout = max_speech_timeout
        self.no_speech_timeout = no_speech_timeout
        self.hints = hints or {}
        self.insight_models = insight_models or []
        self.speaker_separation_options = speaker_separation_options or {}


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

    def _get_headers(self, raw: bool = False) -> dict:
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
            raise TokenRequestError(response.status_code, response.text)

        try:
            response_json = response.json()
            self.token = response_json["access_token"]
            self.token_expiry = int(response_json["expires_at"])
        except (KeyError, ValueError) as e:
            raise TokenParsingError(f"Failed to parse token response: {e}") from e

        return self.token, self.token_expiry

    def _handle_upload_response_errors(self, response):
        """Handle potential errors in the response."""
        if response.status_code != 200:
            raise UploadError(f"Failed to upload file, HTTP Status Code: {response.status_code}, Response: {response.text}")

        response_json = response.json()
        if response_json.get('status') != 200:
            raise UploadError("Failed to upload file, "
                              f"Response Status: {response_json.get('status')}, Response: {response.text}")

        if 'result' not in response_json or 'request_file_id' not in response_json['result']:
            raise InvalidResponseError(f"Unexpected response format: {response_json}")

        return response_json

    def upload_file(self, audio_file: FileIO) -> str:
        """
        Upload an audio file to the Sber Speech Recognition service.

        :param audio_file: File-like object representing the audio file to be uploaded.
        :return: request_file_id of the uploaded file.
        """
        url = self.base_url + "data:upload"
        headers = self._get_headers(raw=True)

        response = russian_secure_post(url, headers=headers, data=audio_file)
        if response.status_code != 200:
            raise FileUploadError(f"Failed to upload file: {response.text}")

        response_json = self._handle_upload_response_errors(response)
        return response_json['result']['request_file_id']

    def _validate_audio_params(self, audio_encoding: str, sample_rate: int, channels_count: int):
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

        if audio_encoding in set(['PCM_S16LE', 'ALAW', 'MULAW']):
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

    def async_recognize(self, request_file_id: str, language: str = "ru-RU",
                        audio_encoding: str = "PCM_S16LE", sample_rate: int = 16000, channels_count: int = 1,
                        config: SpeechRecognitionConfig = SpeechRecognitionConfig()):
        """
        Transcribe audio using Sber Speech Recognition service.

        :param request_file_id: ID of the uploaded file.
        :param language: Language for speech recognition.
        :param audio_encoding: Audio codec.
        :param sample_rate: Sample rate.
        :param channels_count: Number of channels in multi-channel audio.
        :param config: Salute Speech model tuning config.
        :return: Response from the server.
        """

        self._validate_audio_params(audio_encoding, sample_rate, channels_count)
        url = self.base_url + "speech:async_recognize"
        headers = self._get_headers()

        options = vars(config)
        data = {
            "options": {
                "language": language,
                "audio_encoding": audio_encoding,
                "sample_rate": sample_rate,
                "channels_count": channels_count,
                **options
            },
            "request_file_id": request_file_id
        }

        response = russian_secure_post(url, headers=headers, json=data)
        response.raise_for_status()

        response_json = response.json()
        if 'status' in response_json and response_json['status'] != 200:
            raise SpeechRecognitionResponseError(f"Failed to initiate speech recognition: {response.text}")

        return SpeechRecognitionTask(response_json.get('result'))

    def get_task_status(self, task_id: str):
        """
        Retrieve the status of a speech recognition task.

        :param task_id: The ID of the task.
        :return: The status of the task along with additional information.
        """
        url = self.base_url + "task:get"
        params = {'id': task_id}
        headers = self._get_headers()

        response = russian_secure_get(url, headers=headers, params=params)
        response.raise_for_status()

        response_json = response.json()
        if 'status' in response_json and response_json['status'] != 200:
            raise TaskStatusResponseError(f"Failed to get task status: {response.text}")

        return response_json.get('result')

    def download_result(self, response_file_id: str) -> bytes:
        """
        Download the result file from the Sber Speech Recognition service.

        :param response_file_id: The ID of the file to download.
        """
        url = self.base_url + "data:download"
        params = {'response_file_id': response_file_id}
        headers = self._get_headers()

        response = russian_secure_get(url, headers=headers, params=params)
        response.raise_for_status()

        # Save the file content to output_file
        return response.text


@dataclass
class TranscriptionResponse:
    """Response object similar to OpenAI's API response"""
    text: str
    status: str
    task_id: str


# Configure logging
logger = logging.getLogger('SaluteSpeechClient')

def _parse_result(json_str: str) -> str:
    """Extract normalized text from JSON response"""
    try:
        data = json.loads(json_str)
        return data[0]['results'][0]['normalized_text']
    except Exception as e:
        logger.error("Error parsing result: %s", e)
        raise

class SaluteSpeechClient:
    """A simplified interface for Sber Speech Recognition, similar to OpenAI's Whisper API"""
    
    def __init__(self, client_credentials: str):
        """Initialize the client with credentials"""
        logger.debug("Initializing SimpleSpeechClient")
        self.client = SberSpeechRecognition(client_credentials=client_credentials)
        self.audio = self.Audio(self.client)

    class Audio:
        def __init__(self, client: SberSpeechRecognition):
            self.client = client
            self.transcriptions = self.Transcriptions(client)

        class Transcriptions:
            def __init__(self, client: SberSpeechRecognition):
                self.client = client

            async def create(
                self,
                file: BinaryIO,
                model: str = "general",
                language: str = "ru-RU",
                response_format: str = "text",
                prompt: Optional[str] = None,
                poll_interval: float = 1.0
            ) -> TranscriptionResponse:
                """Create a transcription for the given audio file."""
                try:
                    logger.debug("Starting transcription process")

                    # Detect audio format parameters
                    audio_encoding, sample_rate, channels_count = _detect_audio_params(file)
                    logger.debug(f"Detected audio params: {audio_encoding}, {sample_rate}Hz, {channels_count} channels")    

                    # First, ensure we have a valid token
                    logger.debug("Getting authentication token")
                    self.client._get_token()
                    logger.debug("Token obtained successfully")

                    # Configure recognition
                    logger.debug("Configuring recognition parameters")
                    config = SpeechRecognitionConfig(
                        hints={"words": [prompt]} if prompt else None
                    )

                    # Upload the file
                    logger.debug("Uploading audio file")
                    file_id = self.client.upload_file(file)
                    logger.debug("File uploaded successfully. File ID: %s", file_id)

                    # Start async recognition
                    logger.debug("Starting async recognition")
                    task = self.client.async_recognize(
                        request_file_id=file_id,
                        language=language,
                        audio_encoding=audio_encoding,
                        sample_rate=sample_rate,
                        channels_count=channels_count,
                        config=config
                    )
                    logger.debug("Recognition task created. Task ID: %s", task.id)

                    # Poll for results
                    attempt = 0
                    while True:
                        attempt += 1
                        try:
                            logger.debug("Polling attempt %s for task %s", attempt, task.id)
                            result = self.client.get_task_status(task.id)
                            status = result.get('status')
                            logger.debug("Current status: %s", status)

                            if status == 'ERROR':
                                error_msg = result.get('error_message', 'Unknown error')
                                logger.error("Transcription failed: %s", error_msg)
                                raise Exception(f"Transcription failed: {error_msg}")
                            
                            if status == 'DONE':
                                logger.debug("Task completed successfully")
                                if response_format == "text":
                                    response_file_id = result.get('response_file_id')
                                    logger.debug("Downloading result file: %s", response_file_id)
                                    raw_result = self.client.download_result(response_file_id)
                                    text = _parse_result(raw_result)
                                    logger.debug("Result downloaded successfully")
                                    return TranscriptionResponse(
                                        text=text,
                                        status=status,
                                        task_id=task.id
                                    )
                                else:
                                    raise ValueError(f"Unsupported response format: {response_format}")

                            logger.debug("Waiting %s seconds before next poll", poll_interval)
                            await asyncio.sleep(poll_interval)

                        except TaskStatusResponseError as e:
                            logger.error("Error checking task status: %s", str(e))
                            raise Exception(f"Error checking task status: {str(e)}") from e
                        except Exception as e:
                            logger.error("Unexpected error: %s", str(e), exc_info=True)
                            raise

                except Exception as e:
                    logger.error("Error in transcription process: %s", str(e), exc_info=True)
                    raise
