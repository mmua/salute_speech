import unittest
import os
from unittest.mock import patch
from dotenv import load_dotenv, find_dotenv
from salute_speech.utils.token import TokenManager


class TestTokenIntegration(unittest.TestCase):
    """
    Integration tests for TokenManager.

    These tests check the interaction between TokenManager and
    SberSpeechRecognition client.

    Note: To run these tests, you need a valid SBER_SPEECH_API_KEY in your environment
    or .env file. Without it, tests will be skipped.
    """

    @classmethod
    def setUpClass(cls):
        # Try to load API key from env file
        load_dotenv(find_dotenv())
        cls.api_key = os.getenv("SBER_SPEECH_API_KEY")

    def setUp(self):
        if not self.api_key:
            self.skipTest(
                "No API key found. Set SBER_SPEECH_API_KEY in your environment or .env file."
            )
        self.token_manager = TokenManager(self.api_key)

    @patch("salute_speech.utils.token.logger")
    def test_token_refresh_integration(self, mock_logger):
        """Test that token refresh works in an integration scenario"""
        # Get a token
        token = self.token_manager.get_valid_token()

        # Verify we got a non-empty token
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

        # Verify token expiry was set
        self.assertIsNotNone(self.token_manager.token_expiry)
        self.assertIsInstance(self.token_manager.token_expiry, int)

        # Check that debug log was called
        mock_logger.debug.assert_called_with("Token refreshed successfully")

    @patch("salute_speech.utils.token.time")
    def test_token_caching(self, mock_time):
        """Test that tokens are cached and not refreshed unnecessarily"""
        # Mock time to ensure token doesn't expire
        current_time = 1600000000.0  # Some fixed timestamp
        mock_time.return_value = current_time

        # Set up token_manager with a fake token and far-future expiry
        self.token_manager.token = "cached_token"
        self.token_manager.token_expiry = (
            int(current_time * 1000) + 3600000
        )  # 1 hour in the future

        # Replace _refresh_token with a mock that will fail if called
        original_refresh = self.token_manager._refresh_token

        def refresh_should_not_be_called(*args, **kwargs):
            self.fail("_refresh_token was called when it shouldn't have been")

        self.token_manager._refresh_token = refresh_should_not_be_called

        try:
            # Get the token - should use cached version
            token = self.token_manager.get_valid_token()
            self.assertEqual(token, "cached_token")
        finally:
            # Restore original method
            self.token_manager._refresh_token = original_refresh


if __name__ == "__main__":
    unittest.main()
