"""
Sber Salute Speech Recognition API Client

This module provides a comprehensive client for the Sber Salute Speech Recognition service,
offering both a low-level API (SberSpeechRecognition) and a high-level, OpenAI Whisper-like
interface (SaluteSpeechClient) for easy integration.

Features:
- Automatic audio format detection and validation
- Secure authentication and token management
- Asynchronous API for better performance
- Comprehensive error handling
- Support for multiple audio formats (MP3, WAV, FLAC, OPUS, etc.)

The module handles all the complexities of interacting with the Sber API, including:
- Audio parameter validation
- Token refresh and management
- Secure HTTP requests with proper certificate verification
- Task status polling and result retrieval

Basic Usage:
    # Using the OpenAI-like interface (recommended)
    from salute_speech.speech_recognition import SaluteSpeechClient
    import asyncio

    async def transcribe():
        client = SaluteSpeechClient(client_credentials="YOUR_API_KEY")
        with open("audio.mp3", "rb") as audio_file:
            result = await client.audio.transcriptions.create(
                file=audio_file,
                language="ru-RU"
            )
            print(result.text)

    asyncio.run(transcribe())

Advanced Usage:
    # Using the low-level API
    from salute_speech.speech_recognition import SberSpeechRecognition

    client = SberSpeechRecognition(client_credentials="YOUR_CREDENTIALS")

    # Upload audio file
    with open("audio.mp3", "rb") as audio_file:
        file_id = client.upload_file(audio_file)

    # Start recognition task
    task = client.async_recognize(
        request_file_id=file_id,
        audio_encoding="MP3",
        sample_rate=44100,
        channels_count=2
    )

    # Check task status and get results
    status = client.get_task_status(task.id)
    if status.get("status") == "COMPLETED":
        response_file_id = status.get("response_file_id")
        result = client.download_result(response_file_id)
        print(result)
"""

from __future__ import annotations

import json
from time import sleep
import os
from io import FileIO
from dataclasses import dataclass
from typing import BinaryIO, Optional, List, Any
import asyncio
from salute_speech.utils.russian_certs import russian_secure_get, russian_secure_post
from salute_speech.utils.audio import AudioValidator
from salute_speech.utils.token import TokenManager
from salute_speech.utils.logging import setup_logger
from salute_speech.exceptions import (
    APIError,
    InvalidResponseError,
    ValidationError,
    TaskStatusResponseError,
)

# Configure logging
logger = setup_logger(__name__)


class SpeechRecognitionTask:
    def __init__(self, result_data):
        self.id = result_data.get("id")
        self.created_at = result_data.get("created_at")
        self.updated_at = result_data.get("updated_at")
        self.status = result_data.get("status")


@dataclass
class SpeechRecognitionConfig:
    """Configuration for speech recognition tasks."""

    hypotheses_count: int = 1
    enable_profanity_filter: bool = False
    max_speech_timeout: str = "20s"
    no_speech_timeout: str = "7s"
    hints: dict | None = None
    insight_models: list | None = None
    speaker_separation_options: dict | None = None

    def __post_init__(self):
        """Validate configuration parameters after initialization."""
        if self.hypotheses_count < 1 or self.hypotheses_count > 10:
            raise ValidationError("hypotheses_count must be between 1 and 10")

        if not self._validate_timeout(self.max_speech_timeout):
            raise ValidationError(
                "max_speech_timeout must be in format 'Xs' where X is a number"
            )

        if not self._validate_timeout(self.no_speech_timeout):
            raise ValidationError(
                "no_speech_timeout must be in format 'Xs' where X is a number"
            )

        if self.hints is None:
            self.hints = {}

        if self.insight_models is None:
            self.insight_models = []

        if self.speaker_separation_options is None:
            self.speaker_separation_options = {}

    def _validate_timeout(self, timeout: str) -> bool:
        """Validate timeout string format."""
        try:
            seconds = int(timeout[:-1])
            return timeout.endswith("s") and seconds > 0
        except (ValueError, IndexError):
            return False

    def to_dict(self) -> dict:
        """Convert config to dictionary format for API request."""
        return {
            "hypotheses_count": self.hypotheses_count,
            "enable_profanity_filter": self.enable_profanity_filter,
            "max_speech_timeout": self.max_speech_timeout,
            "no_speech_timeout": self.no_speech_timeout,
            "hints": self.hints,
            "insight_models": self.insight_models,
            "speaker_separation_options": self.speaker_separation_options,
        }


class ResponseParser:
    """Handles parsing and validation of API responses."""

    @staticmethod
    def parse_response(response: Any, expected_status: int = 200) -> dict:
        """
        Parse and validate an API response.

        Args:
            response: The response object from the API
            expected_status: The expected HTTP status code

        Returns:
            dict: Parsed response data

        Raises:
            APIError: If the response is invalid or contains an error
        """
        if response.status_code != expected_status:
            raise APIError(
                f"API request failed with status {response.status_code}: {response.text}",
                response.status_code,
            )

        try:
            response_json = response.json()
        except json.JSONDecodeError as e:
            raise InvalidResponseError(f"Failed to parse response as JSON: {e}") from e

        if response_json.get("status") != expected_status:
            raise APIError(
                f"API returned error status {response_json.get('status')}: {response.text}",
                response_json.get("status"),
            )

        return response_json

    @staticmethod
    def extract_result(response_json: dict, required_fields: list[str]) -> dict:
        """
        Extract and validate result fields from response.

        Args:
            response_json: Parsed response JSON
            required_fields: List of required field names

        Returns:
            dict: Validated result data

        Raises:
            InvalidResponseError: If required fields are missing
        """
        if "result" not in response_json:
            raise InvalidResponseError("Response missing 'result' field")

        result = response_json["result"]
        if missing_fields := [
            field for field in required_fields if field not in result
        ]:
            raise InvalidResponseError(
                f"Result missing required fields: {missing_fields}"
            )

        return result


class SberSpeechRecognition:
    def __init__(
        self, client_credentials, base_url="https://smartspeech.sber.ru/rest/v1/"
    ):
        """
        Initialize the Sber Speech Recognition client.

        :param client_credentials: Base64 encoded client credentials for authentication.
        :param base_url: Base URL for the Sber Speech Recognition service.
        """
        self.base_url = base_url
        self.token_manager = TokenManager(client_credentials)
        self.response_parser = ResponseParser()

    def _get_headers(self, raw: bool = False) -> dict:
        """
        Generate the headers for the request.

        :param raw: No content type
        :return: A dictionary with the required headers.
        """
        headers = {"Authorization": f"Bearer {self.token_manager.get_valid_token()}"}
        if not raw:
            headers["Content-Type"] = "application/json"
        return headers

    def upload_file(self, audio_file: BinaryIO) -> str:
        """
        Upload an audio file to the Sber Speech Recognition service.

        :param audio_file: File-like object representing the audio file to be uploaded.
        :return: request_file_id of the uploaded file.
        """
        url = self.base_url + "data:upload"
        headers = self._get_headers(raw=True)
        headers["Content-Type"] = "application/octet-stream"

        response = russian_secure_post(url, headers=headers, data=audio_file)
        response_json = self.response_parser.parse_response(response)
        result = self.response_parser.extract_result(response_json, ["request_file_id"])
        return result["request_file_id"]

    # pylint: disable=too-many-positional-arguments
    def async_recognize(
        self,
        request_file_id: str,
        audio_encoding: str,
        sample_rate: int,
        channels_count: int,
        language: str = "ru-RU",
        config: Optional[SpeechRecognitionConfig] = None,
    ) -> SpeechRecognitionTask:
        """
        Transcribe audio using Sber Speech Recognition service.

        :param request_file_id: ID of the uploaded file.
        :param audio_encoding: Audio codec.
        :param sample_rate: Sample rate.
        :param channels_count: Number of channels in multi-channel audio.
        :param language: Language for speech recognition.
        :param config: Salute Speech model tuning config.
        :return: Response from the server.
        """
        # Validate audio parameters
        _ = AudioValidator._validate_params(audio_encoding, sample_rate, channels_count)

        url = self.base_url + "speech:async_recognize"
        headers = self._get_headers()

        if config is None:
            config = SpeechRecognitionConfig()

        data = {
            "options": {
                "language": language,
                "audio_encoding": audio_encoding,
                "sample_rate": sample_rate,
                "channels_count": channels_count,
                **config.to_dict(),
            },
            "request_file_id": request_file_id,
        }

        response = russian_secure_post(url, headers=headers, json=data)
        response_json = self.response_parser.parse_response(response)
        result = self.response_parser.extract_result(
            response_json, ["id", "status", "created_at", "updated_at"]
        )
        return SpeechRecognitionTask(result)

    def get_task_status(self, task_id: str) -> dict:
        """
        Retrieve the status of a speech recognition task.

        :param task_id: The ID of the task.
        :return: The status of the task along with additional information.
        """
        url = self.base_url + "task:get"
        params = {"id": task_id}
        headers = self._get_headers()

        response = russian_secure_get(url, headers=headers, params=params)
        response_json = self.response_parser.parse_response(response)
        return self.response_parser.extract_result(response_json, ["status"])

    def download_result(self, response_file_id: str) -> str:
        """
        Download the result file from the Sber Speech Recognition service.

        :param response_file_id: The ID of the file to download.
        """
        url = self.base_url + "data:download"
        params = {"response_file_id": response_file_id}
        headers = self._get_headers()

        response = russian_secure_get(url, headers=headers, params=params)
        response.raise_for_status()

        return response.text


@dataclass
class TranscriptionSegment:
    """Whisper-like segment structure."""

    id: int
    start: float
    end: float
    text: str


@dataclass
class TranscriptionResponse:
    """Response object aligned with OpenAI's TranscriptionVerbose API response"""

    duration: float
    """The duration of the input audio."""

    language: str
    """The language of the input audio."""

    text: str
    """The transcribed text."""

    segments: Optional[List[TranscriptionSegment]] = None
    """Segments of the transcribed text and their corresponding details."""

    # Sber-specific fields (not in OpenAI API)
    status: str = ""
    task_id: str = ""


def _load_result_items(json_str: str) -> list:
    """Load recognition items from Sber JSON array response.

    Expected shape: a JSON array; each item contains a 'results' array with
    the first element holding 'normalized_text', 'start', 'end', etc.
    """
    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse recognition result: {e}") from e

    if not isinstance(parsed, list):
        raise ValueError("Unexpected recognition result format: expected a JSON array")

    return parsed


def _parse_result(json_str: str) -> str:
    """Extract concatenated normalized text from JSON/JSONL response."""
    items = _load_result_items(json_str)
    texts: list[str] = []
    for item in items:
        try:
            res0 = item.get("results", [{}])[0]
            t = (res0.get("normalized_text") or "").strip()
            if t:
                texts.append(t)
        except Exception:  # noqa: BLE001
            continue
    return " ".join(texts).strip()


def _convert_to_whisper(
    json_str: str, language: str | None = None
) -> tuple[str, List[TranscriptionSegment], str, float]:
    """Convert Sber JSON response into Whisper-like (text, segments, language, duration)."""
    try:
        data = _load_result_items(json_str)
        segments: List[TranscriptionSegment] = []
        full_text_parts = []
        max_end_time = 0.0
        
        for idx, item in enumerate(data):
            # Sber structure: item['results'][0] has 'start', 'end' with 'Xs' and 'normalized_text'
            res0 = item.get("results", [{}])[0]
            text = res0.get("normalized_text", "") or ""
            start = res0.get("start", "0s").replace("s", "")
            end = res0.get("end", "0s").replace("s", "")
            try:
                start_f = float(start)
            except (TypeError, ValueError):
                start_f = 0.0
            try:
                end_f = float(end)
            except (TypeError, ValueError):
                end_f = start_f

            segments.append(
                TranscriptionSegment(
                    id=idx,
                    start=start_f,
                    end=end_f,
                    text=text.strip(),
                )
            )
            if text:
                full_text_parts.append(text.strip())
            
            # Track the maximum end time for duration calculation
            max_end_time = max(max_end_time, end_f)

        # Default to 'ru' (Russian) if no language specified, as this is Sber's primary language
        lang_code = "ru"
        if language:
            try:
                lang_code = language.split("-")[0].lower()
            except Exception:  # noqa: BLE001
                lang_code = "ru"

        return " ".join(full_text_parts).strip(), segments, lang_code, max_end_time
    except (json.JSONDecodeError, TypeError) as e:
        logger.error("Error converting result: %s", e)
        raise ValueError(f"Failed to convert result: {e}") from e


class TaskPoller:
    """Handles polling for task completion."""

    def __init__(self, client: SberSpeechRecognition, poll_interval: float = 10.0):
        """
        Initialize the task poller.

        Args:
            client: SberSpeechRecognition client instance
            poll_interval: Time between polling attempts in seconds
        """
        self.client = client
        self.poll_interval = poll_interval
        self.logger = setup_logger(__name__)

    def poll_for_result(self, task_id: str) -> str:
        """
        Poll for task completion and return the response file ID.

        Args:
            task_id: ID of the task to poll

        Returns:
            str: Response file ID when task is complete

        Raises:
            TaskStatusResponseError: If task fails or polling fails
        """
        while True:
            task_status = self.client.get_task_status(task_id)
            status = task_status.get("status")

            if status == "ERROR":
                error_msg = task_status.get("error_message", "Unknown error")
                self.logger.error("Task failed: %s", error_msg)
                raise TaskStatusResponseError(f"Task failed: {error_msg}")

            if status == "DONE":
                if not (response_file_id := task_status.get("response_file_id")):
                    raise TaskStatusResponseError(
                        "Task completed but no response file ID found"
                    )
                return response_file_id

            self.logger.debug(
                "Task %s status: %s, waiting %s seconds",
                task_id,
                status,
                self.poll_interval,
            )
            sleep(self.poll_interval)


class Audio:
    """Handles audio operations like transcription"""

    class Transcriptions:
        """Audio transcription operations"""

        def __init__(self, client):
            """
            Initialize the transcriptions client.

            Args:
                client: Parent client instance
            """
            self.client = client

        async def create(
            self,
            file: BinaryIO,
            language: str = "ru-RU",
            poll_interval: float = 1.0,
            config: SpeechRecognitionConfig | None = None,
            debug_dump: str | None = None,
            **kwargs,  # pylint: disable=unused-argument
        ) -> TranscriptionResponse:
            """
            Create a transcription of the given audio file.

            Args:
                file: Audio file to transcribe
                language: Language code (e.g., "ru-RU", "en-US")
                poll_interval: How often to check for task completion
                config: Optional SpeechRecognitionConfig for advanced tuning
                kwargs: Additional keyword arguments

            Returns:
                TranscriptionResponse with transcribed text
            """
            # Detect audio parameters
            try:
                audio_encoding, sample_rate, channels_count = (
                    AudioValidator.detect_and_validate(file)
                )
                self.client.logger.debug(
                    "Detected audio parameters: %s, %s Hz, %s channels",
                    audio_encoding,
                    sample_rate,
                    channels_count,
                )

                # Upload the file first
                file_id = await asyncio.to_thread(self.client.sr.upload_file, file)

                # Start asynchronous transcription
                task = await asyncio.to_thread(
                    self.client.sr.async_recognize,
                    request_file_id=file_id,
                    audio_encoding=audio_encoding,
                    sample_rate=sample_rate,
                    channels_count=channels_count,
                    language=language,
                    config=config if config is not None else SpeechRecognitionConfig(),
                )

                # Poll for completion and get result
                poller = TaskPoller(self.client.sr, poll_interval=poll_interval)
                response_file_id = await asyncio.to_thread(
                    poller.poll_for_result, task.id
                )

                # Download and parse the result
                result_data = await asyncio.to_thread(
                    self.client.sr.download_result, response_file_id
                )

                # Optional raw dump for debugging
                if debug_dump:
                    try:
                        dump_path = debug_dump
                        if os.path.isdir(debug_dump):
                            dump_path = os.path.join(debug_dump, f"{task.id}.json")
                        os.makedirs(os.path.dirname(dump_path) or ".", exist_ok=True)
                        with open(dump_path, "w", encoding="utf-8") as f_out:
                            f_out.write(result_data)
                        self.client.logger.debug("Raw result dumped to %s", dump_path)
                    except Exception as dump_err:  # noqa: BLE001
                        self.client.logger.error(
                            "Failed to dump raw result: %s", dump_err
                        )

                text_full, segments, lang_code, duration = _convert_to_whisper(
                    result_data, language=language
                )
                return TranscriptionResponse(
                    duration=duration,
                    language=lang_code,
                    text=text_full,
                    segments=segments,
                    status="DONE",
                    task_id=task.id,
                )
            except json.JSONDecodeError as e:
                self.client.logger.error("Failed to parse JSON result: %s", e)
                raise ValueError(f"Failed to parse transcription result: {e}") from e
            except TaskStatusResponseError as e:
                self.client.logger.error("Task error: %s", e)
                raise

    def __init__(self, client):
        """
        Initialize the audio client.

        Args:
            client: Parent client instance
        """
        self.client = client
        self.transcriptions = self.Transcriptions(client)


class SaluteSpeechClient:
    """
    High-level client for Sber Salute Speech API, similar to OpenAI API.

    Provides an easy-to-use interface for transcribing audio files.
    """

    def __init__(self, client_credentials: str):
        """
        Initialize the Salute Speech client.

        Args:
            client_credentials: Authentication token (API key)
        """
        self.sr = SberSpeechRecognition(client_credentials)
        self.token_manager = self.sr.token_manager
        self.audio = Audio(self)
        self.logger = setup_logger(__name__)
