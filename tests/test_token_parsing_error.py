import unittest
from unittest.mock import patch, MagicMock
from salute_speech.utils.token import TokenManager
from salute_speech.exceptions import TokenParsingError


class TestTokenParsingError(unittest.TestCase):
    """
    Tests specifically focused on the TokenParsingError scenarios.

    These tests ensure that errors in parsing the token response are
    properly caught and raised as TokenParsingError exceptions.
    """

    def setUp(self):
        self.token_manager = TokenManager("test_credentials")

    @patch("salute_speech.utils.token.russian_secure_post")
    def test_missing_access_token(self, mock_post):
        """Test TokenParsingError when access_token is missing"""
        # Mock response with missing access_token
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            # No access_token
            "expires_at": "1600000000000"
        }
        mock_post.return_value = mock_response

        # Verify that TokenParsingError is raised
        with self.assertRaises(TokenParsingError):
            self.token_manager._refresh_token("SALUTE_SPEECH_PERS")

        # Check that the error message includes the specific KeyError
        with self.assertRaises(TokenParsingError) as ctx2:
            self.token_manager._refresh_token("SALUTE_SPEECH_PERS")
        self.assertIn("'access_token'", str(ctx2.exception))

    @patch("salute_speech.utils.token.russian_secure_post")
    def test_missing_expires_at(self, mock_post):
        """Test TokenParsingError when expires_at is missing"""
        # Mock response with missing expires_at
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token"
            # No expires_at
        }
        mock_post.return_value = mock_response

        # Verify that TokenParsingError is raised
        with self.assertRaises(TokenParsingError):
            self.token_manager._refresh_token("SALUTE_SPEECH_PERS")

        # Check that the error message includes the specific KeyError
        with self.assertRaises(TokenParsingError) as ctx3:
            self.token_manager._refresh_token("SALUTE_SPEECH_PERS")
        self.assertIn("'expires_at'", str(ctx3.exception))

    @patch("salute_speech.utils.token.russian_secure_post")
    def test_invalid_expires_at_format(self, mock_post):
        """Test TokenParsingError when expires_at is not a numeric string"""
        # Mock response with invalid expires_at
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_at": "not-a-number",  # Invalid format
        }
        mock_post.return_value = mock_response

        # Verify that TokenParsingError is raised
        with self.assertRaises(TokenParsingError) as ctx:
            self.token_manager._refresh_token("SALUTE_SPEECH_PERS")

        # Check that the exception is a TokenParsingError that wraps a ValueError
        self.assertEqual(ValueError, type(ctx.exception.__cause__))

    @patch("salute_speech.utils.token.russian_secure_post")
    def test_invalid_json_response(self, mock_post):
        """Test TokenParsingError when response is not valid JSON"""
        # Mock response with json method that raises ValueError
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        # Verify that TokenParsingError is raised
        with self.assertRaises(TokenParsingError) as ctx:
            self.token_manager._refresh_token("SALUTE_SPEECH_PERS")

        # Check that the error message includes the specific ValueError
        self.assertIn("Invalid JSON", str(ctx.exception))

    @patch("salute_speech.utils.token.russian_secure_post")
    def test_empty_response(self, mock_post):
        """Test TokenParsingError when response is empty"""
        # Mock response with empty dict
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        # Verify that TokenParsingError is raised
        with self.assertRaises(TokenParsingError):
            self.token_manager._refresh_token("SALUTE_SPEECH_PERS")


if __name__ == "__main__":
    unittest.main()
