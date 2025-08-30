"""
Audio handling utilities for Sber Speech Recognition service.
"""

from __future__ import annotations

import os
import tempfile
from typing import BinaryIO, Optional, Tuple, TypedDict, Dict
from pydub.utils import mediainfo  # type: ignore[import-untyped]

from salute_speech.exceptions import ValidationError
from salute_speech.utils.logging import setup_logger


# Configure logging
logger = setup_logger(__name__)


class ValidEncodingRule(TypedDict, total=True):
    max_channels: int
    sample_rate_range: Optional[Tuple[int, int]]
    default_rate: Optional[int]


class AudioValidator:
    VALID_ENCODINGS: Dict[str, ValidEncodingRule] = {
        "PCM_S16LE": {
            "max_channels": 8,
            "sample_rate_range": (8000, 96000),
            "default_rate": 16000,
        },
        "OPUS": {"max_channels": 1, "sample_rate_range": None, "default_rate": None},
        "MP3": {"max_channels": 2, "sample_rate_range": None, "default_rate": None},
        "FLAC": {"max_channels": 8, "sample_rate_range": None, "default_rate": None},
        "ALAW": {
            "max_channels": 8,
            "sample_rate_range": (8000, 96000),
            "default_rate": 16000,
        },
        "MULAW": {
            "max_channels": 8,
            "sample_rate_range": (8000, 96000),
            "default_rate": 16000,
        },
    }

    FORMAT_MAP: Dict[str, str] = {
        "MP3": "MP3",
        "OPUS": "OPUS",
        "FLAC": "FLAC",
        "PCM": "PCM_S16LE",
        "ALAW": "ALAW",
        "MULAW": "MULAW",
        "WAV": "PCM_S16LE",
    }

    @classmethod
    def detect_and_validate(cls, file: BinaryIO) -> tuple[str, int, int]:
        """
        Detect audio parameters and validate them according to Sber requirements.

        Args:
            file: Audio file-like object

        Returns:
            tuple: (audio_encoding, sample_rate, channels_count)

        Raises:
            ValidationError: If audio format cannot be validated
        """
        params = cls._detect_params(file)
        return cls._validate_params(*params)

    @classmethod
    def _detect_params(cls, file: BinaryIO) -> tuple[str, int, int]:
        """Detect raw audio parameters from file."""
        current_pos = file.tell()
        file.seek(0)

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".audio", delete=False
            ) as temp_file:
                temp_file.write(file.read())
                temp_path = temp_file.name

            try:
                info = mediainfo(temp_path)
                codec_raw = (info.get("codec_name") or info.get("format_name") or "").upper()
                if not codec_raw:
                    raise ValidationError(
                        "Unable to detect audio encoding. The file may be empty or invalid."
                    )
                try:
                    sample_rate = int(info.get("sample_rate", 0))
                    channels_count = int(info.get("channels", 0))
                except (TypeError, ValueError):
                    raise ValidationError(
                        "Unable to detect audio parameters. The file may be empty or invalid."
                    )

                if not sample_rate or not channels_count:
                    raise ValidationError(
                        "Unable to detect audio parameters. The file may be empty or invalid."
                    )

                # Map to Sber format
                audio_encoding = cls.FORMAT_MAP.get(codec_raw, "PCM_S16LE")

                return audio_encoding, sample_rate, channels_count

            finally:
                try:
                    os.unlink(temp_path)
                except OSError as e:
                    logger.warning(
                        "Failed to remove temporary file %s: %s", temp_path, e
                    )

        finally:
            file.seek(current_pos)

    @classmethod
    def _validate_params(
        cls, audio_encoding: str, sample_rate: int, channels_count: int
    ) -> tuple[str, int, int]:
        """
        Validate audio parameters according to Sber requirements.

        Args:
            audio_encoding: The encoding of the audio file
            sample_rate: The sample rate of the audio file
            channels_count: The number of channels in the audio file

        Returns:
            tuple: (audio_encoding, sample_rate, channels_count) if validation passes

        Raises:
            ValidationError: If any parameter is invalid according to Sber requirements
        """
        if audio_encoding not in cls.VALID_ENCODINGS:
            raise ValidationError(f"Invalid audio encoding: {audio_encoding}")

        rules = cls.VALID_ENCODINGS[audio_encoding]

        # Validate channels count
        if channels_count > rules["max_channels"]:
            raise ValidationError(
                f"Too many channels ({channels_count}) for {audio_encoding}. "
                f"Maximum allowed channels is {rules['max_channels']}. "
                f"Please convert the audio to mono or stereo before processing."
            )

        # Validate sample rate
        if rules["sample_rate_range"]:
            min_rate, max_rate = rules["sample_rate_range"]
            if not (min_rate <= sample_rate <= max_rate):
                raise ValidationError(
                    f"Sample rate {sample_rate}Hz is out of valid range [{min_rate}-{max_rate}]Hz "
                    f"for {audio_encoding} encoding. Please resample the audio file before processing."
                )

        logger.debug(
            "Validated audio parameters: %s, %sHz, %s channels",
            audio_encoding,
            sample_rate,
            channels_count,
        )

        return audio_encoding, sample_rate, channels_count
