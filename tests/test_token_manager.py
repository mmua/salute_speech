import unittest
from unittest.mock import patch, MagicMock
import time
import uuid
from salute_speech.utils.token import TokenManager
from salute_speech.exceptions import TokenRequestError, TokenParsingError


class TestTokenManager(unittest.TestCase):
    def setUp(self):
        self.test_credentials = "test_credentials"
        self.token_manager = TokenManager(self.test_credentials)

    def test_init(self):
        """Test initialization of TokenManager"""
        self.assertEqual(self.token_manager.client_credentials, self.test_credentials)
        self.assertIsNone(self.token_manager.token)
        self.assertIsNone(self.token_manager.token_expiry)

    @patch("salute_speech.utils.token.russian_secure_post")
    def test_refresh_token_success(self, mock_post):
        """Test successful token refresh"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_at": str(int(time.time() * 1000) + 3600000),  # 1 hour from now
        }
        mock_post.return_value = mock_response

        # Call the method
        token, expiry = self.token_manager._refresh_token("SALUTE_SPEECH_PERS")

        # Verify the result (pure function contract)
        self.assertEqual(token, "test_token")
        self.assertEqual(expiry, int(mock_response.json.return_value["expires_at"]))

        # Verify the API call
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://ngw.devices.sberbank.ru:9443/api/v2/oauth")
        self.assertEqual(
            kwargs["headers"]["Authorization"], f"Basic {self.test_credentials}"
        )
        self.assertEqual(
            kwargs["headers"]["Content-Type"], "application/x-www-form-urlencoded"
        )
        self.assertTrue(
            uuid.UUID(kwargs["headers"]["RqUID"])
        )  # Check that RqUID is a valid UUID
        self.assertEqual(kwargs["data"], "scope=SALUTE_SPEECH_PERS")

    @patch("salute_speech.utils.token.russian_secure_post")
    def test_refresh_token_http_error(self, mock_post):
        """Test token refresh with HTTP error"""
        # Mock response with error
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        # Verify that TokenRequestError is raised
        with self.assertRaises(TokenRequestError) as context:
            self.token_manager._refresh_token("SALUTE_SPEECH_PERS")

        # Check error details
        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(str(context.exception), "Unauthorized")

    @patch("salute_speech.utils.token.russian_secure_post")
    def test_refresh_token_parsing_error(self, mock_post):
        """Test token refresh with parsing error"""
        # Mock response with missing fields
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            # Missing access_token
            "expires_at": str(int(time.time() * 1000) + 3600000)
        }
        mock_post.return_value = mock_response

        # Verify that TokenParsingError is raised
        with self.assertRaises(TokenParsingError):
            self.token_manager._refresh_token("SALUTE_SPEECH_PERS")

    @patch("salute_speech.utils.token.TokenManager._refresh_token")
    def test_get_valid_token_no_token(self, mock_refresh):
        """Test get_valid_token when no token exists"""
        # Setup mock
        mock_refresh.return_value = ("new_token", int(time.time() * 1000) + 3600000)

        # Call the method
        self.token_manager.get_valid_token()

        # Verify refresh was called
        mock_refresh.assert_called_once_with("SALUTE_SPEECH_PERS")

    @patch("salute_speech.utils.token.TokenManager._refresh_token")
    def test_get_valid_token_expired(self, mock_refresh):
        """Test get_valid_token with expired token"""
        # Set expired token
        self.token_manager.token = "expired_token"
        self.token_manager.token_expiry = (
            int(time.time() * 1000) - 100000
        )  # In the past

        # Setup mock
        mock_refresh.return_value = ("new_token", int(time.time() * 1000) + 3600000)

        # Call the method
        self.token_manager.get_valid_token()

        # Verify refresh was called
        mock_refresh.assert_called_once_with("SALUTE_SPEECH_PERS")

    @patch("salute_speech.utils.token.TokenManager._refresh_token")
    def test_get_valid_token_not_expired(self, mock_refresh):
        """Test get_valid_token with valid token"""
        # Set unexpired token
        self.token_manager.token = "valid_token"
        self.token_manager.token_expiry = (
            int(time.time() * 1000) + 3600000
        )  # 1 hour in the future

        # Call the method
        token = self.token_manager.get_valid_token()

        # Verify result and that refresh was not called
        self.assertEqual(token, "valid_token")
        mock_refresh.assert_not_called()

    @patch("salute_speech.utils.token.TokenManager._refresh_token")
    def test_get_valid_token_custom_scope(self, mock_refresh):
        """Test get_valid_token with custom scope"""
        # Setup mock
        mock_refresh.return_value = ("new_token", int(time.time() * 1000) + 3600000)

        # Call the method with custom scope
        self.token_manager.get_valid_token(scope="CUSTOM_SCOPE")

        # Verify custom scope was used
        mock_refresh.assert_called_once_with("CUSTOM_SCOPE")


if __name__ == "__main__":
    unittest.main()
