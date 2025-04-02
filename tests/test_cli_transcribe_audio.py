import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from click.testing import CliRunner
from salute_speech.commands.cmd_transcribe_audio import transcribe_audio
from salute_speech.speech_recognition import TranscriptionResponse

class TestTranscribeAudioCommand(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.test_dir = tempfile.mkdtemp()
        self.test_audio_path = os.path.join(self.test_dir, 'test_audio.wav')
        with open(self.test_audio_path, 'wb') as f:
            f.write(b'\x00')  # Writing dummy content
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch.dict('os.environ', {'SBER_SPEECH_API_KEY': 'test_api_key'})
    @patch('salute_speech.commands.cmd_transcribe_audio.SaluteSpeechClient')
    @patch('salute_speech.commands.cmd_transcribe_audio.AudioValidator')
    @patch('salute_speech.commands.cmd_transcribe_audio.get_writer')
    async def test_transcribe_audio_with_output_file(self, mock_get_writer, mock_audio_validator, mock_client_class):
        # Mock audio validation
        mock_audio_validator.detect_and_validate.return_value = ('PCM_S16LE', 16000, 1)

        # Mock client and response
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_transcriptions = MagicMock()
        mock_client.audio.transcriptions = mock_transcriptions
        
        # Create AsyncMock for the create method
        mock_create = AsyncMock()
        mock_transcriptions.create = mock_create
        mock_create.return_value = TranscriptionResponse(
            text="test transcription",
            status="DONE",
            task_id="task_123"
        )

        # Mock writer
        mock_writer = MagicMock()
        mock_get_writer.return_value = mock_writer

        # Running the command
        output_file = os.path.join(self.test_dir, 'output.txt')
        result = self.runner.invoke(transcribe_audio, [
            self.test_audio_path,
            '--output_file', output_file
        ])

        # Assertions
        self.assertEqual(result.exit_code, 0)
        mock_client_class.assert_called_once_with('test_api_key')
        mock_create.assert_called_once()
        mock_get_writer.assert_called_once()
        mock_writer.assert_called_once()

    @patch.dict('os.environ', {'SBER_SPEECH_API_KEY': 'test_api_key'})
    @patch('salute_speech.commands.cmd_transcribe_audio.SaluteSpeechClient')
    @patch('salute_speech.commands.cmd_transcribe_audio.AudioValidator')
    @patch('salute_speech.commands.cmd_transcribe_audio.get_writer')
    async def test_transcribe_audio_with_language(self, mock_get_writer, mock_audio_validator, mock_client_class):
        # Mock audio validation
        mock_audio_validator.detect_and_validate.return_value = ('PCM_S16LE', 16000, 1)

        # Mock client and response
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_transcriptions = MagicMock()
        mock_client.audio.transcriptions = mock_transcriptions
        
        # Create AsyncMock for the create method
        mock_create = AsyncMock()
        mock_transcriptions.create = mock_create
        mock_create.return_value = TranscriptionResponse(
            text="test transcription",
            status="DONE",
            task_id="task_123"
        )

        # Mock writer
        mock_writer = MagicMock()
        mock_get_writer.return_value = mock_writer

        # Running the command with language option
        result = self.runner.invoke(transcribe_audio, [
            self.test_audio_path,
            '--language', 'en-US'
        ])

        # Assertions
        self.assertEqual(result.exit_code, 0)
        mock_create.assert_called_once_with(
            file=unittest.mock.ANY,
            language='en-US'
        )

    @patch.dict('os.environ', {'SBER_SPEECH_API_KEY': 'test_api_key'})
    @patch('salute_speech.commands.cmd_transcribe_audio.SaluteSpeechClient')
    @patch('salute_speech.commands.cmd_transcribe_audio.AudioValidator')
    async def test_channels_mismatch(self, mock_audio_validator, mock_client_class):
        # Mock audio validation to return 2 channels
        mock_audio_validator.detect_and_validate.return_value = ('PCM_S16LE', 16000, 2)

        # Mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_transcriptions = MagicMock()
        mock_client.audio.transcriptions = mock_transcriptions
        mock_transcriptions.create = AsyncMock()

        # Running the command with channels set to 1 (mismatch)
        result = self.runner.invoke(transcribe_audio, [
            self.test_audio_path,
            '--channels', '1'
        ])

        # Assertions
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('Error: unexpected audio channels number', result.output)
        mock_transcriptions.create.assert_not_called()

    @patch.dict('os.environ', {})
    async def test_missing_api_key(self):
        # Running the command without API key
        result = self.runner.invoke(transcribe_audio, [
            self.test_audio_path
        ])

        # Assertions
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('Error: env variable SBER_SPEECH_API_KEY is not set', result.output)

if __name__ == '__main__':
    unittest.main()