"""
Token management utilities for Sber Speech Recognition service.
"""

from __future__ import annotations

import uuid
from time import time
from urllib.parse import urlencode

from salute_speech.utils.russian_certs import russian_secure_post
from salute_speech.exceptions import TokenRequestError, TokenParsingError
from salute_speech.utils.logging import setup_logger

# Configure logging
logger = setup_logger(__name__)


class TokenManager:
    """Manages OAuth token for Sber Speech Recognition service."""

    def __init__(self, client_credentials: str):
        """
        Initialize the token manager.

        Args:
            client_credentials: Base64 encoded client credentials
        """
        self.client_credentials: str = client_credentials
        self.token: str | None = None
        self.token_expiry: int | None = None

    def get_valid_token(self, scope: str = "SALUTE_SPEECH_PERS") -> str:
        """
        Get a valid token, refreshing if necessary.

        Args:
            scope: OAuth scope for the token

        Returns:
            str: Valid access token

        Raises:
            TokenRequestError: If token request fails
            TokenParsingError: If token response parsing fails
        """
        if self.token_expiry is None or time() * 1000 > self.token_expiry or not self.token:
            token_value, expiry_value = self._refresh_token(scope)
            # Ensure attributes are set even if method is mocked
            self.token = token_value
            self.token_expiry = expiry_value
        # At this point token must be set
        assert self.token is not None
        return self.token

    def _refresh_token(self, scope: str) -> tuple[str, int]:
        """
        Refresh the OAuth token.

        Args:
            scope: OAuth scope for the token

        Returns:
            Tuple[str, int]: (access_token, expires_at)

        Raises:
            TokenRequestError: If token request fails
            TokenParsingError: If token response parsing fails
        """
        request_uid = str(uuid.uuid4())
        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        headers = {
            "Authorization": f"Basic {self.client_credentials}",
            "RqUID": request_uid,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = urlencode({"scope": scope})

        response = russian_secure_post(url, headers=headers, data=data)
        if response.status_code != 200:
            raise TokenRequestError(response.status_code, response.text)

        try:
            response_json = response.json()
            token_value: str = response_json["access_token"]
            expiry_value: int = int(response_json["expires_at"])
            logger.debug("Token refreshed successfully")
            return token_value, expiry_value
        except (KeyError, ValueError) as e:
            raise TokenParsingError(f"Failed to parse token response: {e}") from e
