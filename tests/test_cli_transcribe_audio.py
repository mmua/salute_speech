import os
import shutil
import tempfile
import unittest
from unittest.mock import patch
from click.testing import CliRunner
from salute_speech.commands import transcribe_audio 
from salute_speech.speech_recognition import SpeechRecognitionTask

class TestTranscribeAudioCommand(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.test_dir = tempfile.mkdtemp()
        self.test_audio_path = os.path.join(self.test_dir, 'test_audio.wav')
        with open(self.test_audio_path, 'wb') as f:
            f.write(b'\x00')  # Writing dummy content
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)


    @patch('salute_speech.commands.cmd_transcribe_audio.SberSpeechRecognition')
    @patch('salute_speech.commands.cmd_transcribe_audio.get_audio_params')
    @patch('salute_speech.commands.cmd_transcribe_audio.get_writer')
    def test_transcribe_audio(self, mock_get_writer, mock_get_audio_params, mock_SberSpeechRecognition):
        # Mocking the get_audio_params function
        mock_get_audio_params.return_value = ('PCM_S16LE', 16000, 1)

        # Mocking SberSpeechRecognition methods
        sr_instance = mock_SberSpeechRecognition.return_value
        sr_instance.upload_file.return_value = 'file_id'
        sr_instance.async_recognize.return_value = SpeechRecognitionTask({'id': 'task_id', 'status': 'NEW', 'created_at': 0, 'updated_at': 0})
        sr_instance.get_task_status.return_value = {'status': 'DONE', 'response_file_id': 'response_file_id'}
        sr_instance.download_result.return_value = '{"transcription": "test"}'

        # Mocking writer function
        mock_writer = mock_get_writer.return_value

        # Running the command
        result = self.runner.invoke(transcribe_audio, [self.test_audio_path, '--output_file', os.path.join(self.test_dir, 'output.txt')])
        assert result.exit_code == 0, result.output

        # Assertions
        self.assertEqual(result.exit_code, 0)
        mock_SberSpeechRecognition.assert_called_once_with(os.getenv("SBER_SPEECH_API_KEY"))
        sr_instance.upload_file.assert_called_once()
        sr_instance.async_recognize.assert_called_once()
        sr_instance.get_task_status.assert_called_once()
        sr_instance.download_result.assert_called_once()
        mock_writer.assert_called_once()

    @patch('salute_speech.commands.cmd_transcribe_audio.SberSpeechRecognition')
    @patch('salute_speech.commands.cmd_transcribe_audio.get_audio_params')
    @patch('salute_speech.commands.cmd_transcribe_audio.get_writer')
    def test_channels_mismatch(self, mock_get_writer, mock_get_audio_params, mock_SberSpeechRecognition):
        # Mocking the get_audio_params function to return different channels count
        mock_get_audio_params.return_value = ('PCM_S16LE', 16000, 2)  # Assuming 2 channels in the file

        # Mocking SberSpeechRecognition methods
        sr_instance = mock_SberSpeechRecognition.return_value

        # Running the command with channels set to 1 (mismatch)
        result = self.runner.invoke(transcribe_audio, [self.test_audio_path, '--channels', '1', '--output_file', os.path.join(self.test_dir, 'output.txt')])

        # Mocking writer function
        mock_writer = mock_get_writer.return_value

        # Assertions
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('Error: unexpected audio channels number', result.output)
        sr_instance.upload_file.assert_not_called()
        sr_instance.async_recognize.assert_not_called()
        mock_writer.assert_not_called()


# Run the tests
if __name__ == '__main__':
    unittest.main()