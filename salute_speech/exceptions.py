"""
Exceptions for the salute_speech package.
"""
from typing import Optional


class SberSpeechError(Exception):
    """Base exception for all errors related to Sber Speech Recognition API."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class APIError(SberSpeechError):
    """Exception raised for errors related to API calls."""
    pass


class UploadError(APIError):
    """Exception raised for errors during file upload."""
    pass


class InvalidResponseError(APIError):
    """Exception raised for errors related to invalid API responses."""
    pass


class InvalidAudioFormatError(APIError):
    """Exception raised for errors related to invalid audio formats."""
    pass


class TokenRequestError(APIError):
    """Exception raised for errors during token requests."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message, status_code)


class TokenParsingError(APIError):
    """Exception raised for errors during token parsing."""
    pass


class FileUploadError(APIError):
    """Exception raised for errors during file uploads."""
    pass


class SpeechRecognitionResponseError(APIError):
    """Exception raised for errors within the speech recognition response."""
    pass


class TaskStatusResponseError(APIError):
    """Exception raised for errors within the task status response."""
    pass


class ValidationError(SberSpeechError):
    """Exception raised for validation errors."""
    pass
