import os
import shutil
import tempfile
import unittest
import click
from unittest.mock import patch, MagicMock, AsyncMock
from click.testing import CliRunner
from salute_speech.commands.cmd_transcribe_audio import transcribe_audio
from salute_speech.speech_recognition import TranscriptionResponse


class TestTranscribeAudioCommand(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.test_dir = tempfile.mkdtemp()
        self.test_audio_path = os.path.join(self.test_dir, "test_audio.wav")
        # Create a minimal valid WAV file to avoid audio validation errors
        # WAV header: RIFF + file size + WAVE + fmt chunk + data chunk
        wav_data = (
            b"RIFF"  # RIFF header
            b"\x24\x00\x00\x00"  # File size (36 bytes)
            b"WAVE"  # WAVE header
            b"fmt "  # fmt chunk header
            b"\x10\x00\x00\x00"  # fmt chunk size (16 bytes)
            b"\x01\x00"  # Audio format (PCM)
            b"\x01\x00"  # Number of channels (1)
            b"\x44\xAC\x00\x00"  # Sample rate (44100 Hz)
            b"\x88\x58\x01\x00"  # Byte rate
            b"\x02\x00"  # Block align
            b"\x10\x00"  # Bits per sample (16)
            b"data"  # data chunk header
            b"\x00\x00\x00\x00"  # data chunk size (0 bytes)
        )
        with open(self.test_audio_path, "wb") as f:
            f.write(wav_data)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch.dict("os.environ", {"SBER_SPEECH_API_KEY": "test_api_key"})
    @patch("salute_speech.commands.cmd_transcribe_audio.SaluteSpeechClient")
    @patch("salute_speech.commands.cmd_transcribe_audio.AudioValidator")
    @patch("salute_speech.commands.cmd_transcribe_audio.get_writer")
    def test_transcribe_audio_with_output_file(
        self, mock_get_writer, mock_audio_validator, mock_client_class
    ):
        # Mock audio validation
        mock_audio_validator.detect_and_validate.return_value = ("PCM_S16LE", 16000, 1)

        # Mock client and response
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_transcriptions = MagicMock()
        mock_client.audio.transcriptions = mock_transcriptions

        # Create AsyncMock for the create method
        mock_create = AsyncMock()
        mock_transcriptions.create = mock_create
        mock_create.return_value = TranscriptionResponse(
            duration=30.5,
            language="ru",
            text="test transcription",
            status="DONE",
            task_id="task_123"
        )

        # Mock writer
        mock_writer = MagicMock()
        mock_get_writer.return_value = mock_writer

        # Running the command
        output_file = os.path.join(self.test_dir, "output.txt")
        result = self.runner.invoke(
            transcribe_audio, [self.test_audio_path, "--output_file", output_file]
        )

        # Assertions
        self.assertEqual(result.exit_code, 0)
        mock_client_class.assert_called_once_with("test_api_key")
        mock_create.assert_called_once()
        mock_get_writer.assert_called_once()
        mock_writer.assert_called_once()

    @patch.dict("os.environ", {"SBER_SPEECH_API_KEY": "test_api_key"})
    @patch("salute_speech.commands.cmd_transcribe_audio.SaluteSpeechClient")
    @patch("salute_speech.commands.cmd_transcribe_audio.AudioValidator")
    @patch("salute_speech.commands.cmd_transcribe_audio.get_writer")
    def test_transcribe_audio_with_language(
        self, mock_get_writer, mock_audio_validator, mock_client_class
    ):
        # Mock audio validation
        mock_audio_validator.detect_and_validate.return_value = ("PCM_S16LE", 16000, 1)

        # Mock client and response
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_transcriptions = MagicMock()
        mock_client.audio.transcriptions = mock_transcriptions

        # Create AsyncMock for the create method
        mock_create = AsyncMock()
        mock_transcriptions.create = mock_create
        mock_create.return_value = TranscriptionResponse(
            duration=30.5,
            language="ru",
            text="test transcription",
            status="DONE",
            task_id="task_123"
        )

        # Mock writer
        mock_writer = MagicMock()
        mock_get_writer.return_value = mock_writer

        # Running the command with language option
        result = self.runner.invoke(
            transcribe_audio, [self.test_audio_path, "--language", "en-US"]
        )

        # Assertions
        self.assertEqual(result.exit_code, 0)
        mock_create.assert_called_once()
        _, kwargs = mock_create.call_args
        self.assertEqual(kwargs.get("language"), "en-US")
        self.assertIn("file", kwargs)

    @patch.dict("os.environ", {"SBER_SPEECH_API_KEY": "test_api_key"})
    @patch("salute_speech.commands.cmd_transcribe_audio.SaluteSpeechClient")
    @patch("salute_speech.commands.cmd_transcribe_audio.AudioValidator")
    def test_channels_mismatch(self, mock_audio_validator, mock_client_class):
        # Mock audio validation to return 2 channels
        mock_audio_validator.detect_and_validate.return_value = ("PCM_S16LE", 16000, 2)

        # Mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_transcriptions = MagicMock()
        mock_client.audio.transcriptions = mock_transcriptions
        mock_transcriptions.create = AsyncMock()

        # Running the command with channels set to 1 (mismatch)
        result = self.runner.invoke(
            transcribe_audio, [self.test_audio_path, "--channels", "1"]
        )

        # Assertions
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Error: unexpected audio channels number", result.output)
        mock_transcriptions.create.assert_not_called()

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_api_key(self):
        # Run the command with catch_exceptions=True (default) and check exit code and output
        result = self.runner.invoke(transcribe_audio, [self.test_audio_path])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Error: env variable SBER_SPEECH_API_KEY is not set", result.output)


if __name__ == "__main__":
    unittest.main()
