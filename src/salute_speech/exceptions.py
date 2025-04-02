"""
Exceptions for the salute_speech package.
"""
from __future__ import annotations


class SberSpeechError(Exception):
    """Base exception for all errors related to Sber Speech Recognition API."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class APIError(SberSpeechError):
    """Exception raised for errors related to API calls."""


class UploadError(APIError):
    """Exception raised for errors during file upload."""


class InvalidResponseError(APIError):
    """Exception raised for errors related to invalid API responses."""


class InvalidAudioFormatError(APIError):
    """Exception raised for errors related to invalid audio formats."""


class TokenRequestError(APIError):
    """Exception raised for errors during token requests."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message, status_code)


class TokenParsingError(APIError):
    """Exception raised for errors during token parsing."""


class FileUploadError(APIError):
    """Exception raised for errors during file uploads."""


class SpeechRecognitionResponseError(APIError):
    """Exception raised for errors within the speech recognition response."""


class TaskStatusResponseError(APIError):
    """Exception raised for errors within the task status response."""


class ValidationError(SberSpeechError):
    """Exception raised for validation errors."""
