import unittest
import io
import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from salute_speech.utils.audio import AudioValidator
from salute_speech.exceptions import ValidationError


class TestAudioValidator(unittest.TestCase):
    def test_format_mapping(self):
        """Test format mapping dictionary"""
        self.assertEqual(AudioValidator.FORMAT_MAP['MP3'], 'MP3')
        self.assertEqual(AudioValidator.FORMAT_MAP['WAV'], 'PCM_S16LE')
        self.assertEqual(AudioValidator.FORMAT_MAP['PCM'], 'PCM_S16LE')
        self.assertEqual(AudioValidator.FORMAT_MAP['FLAC'], 'FLAC')
        
    def test_valid_encodings(self):
        """Test valid encodings dictionary"""
        self.assertEqual(AudioValidator.VALID_ENCODINGS['PCM_S16LE']['max_channels'], 8)
        self.assertEqual(AudioValidator.VALID_ENCODINGS['MP3']['max_channels'], 2)
        self.assertEqual(AudioValidator.VALID_ENCODINGS['OPUS']['max_channels'], 1)
        self.assertEqual(AudioValidator.VALID_ENCODINGS['PCM_S16LE']['sample_rate_range'], (8000, 96000))
        
    @patch('salute_speech.utils.audio.mediainfo')
    @patch('tempfile.NamedTemporaryFile')
    def test_detect_params_mp3(self, mock_temp_file, mock_mediainfo):
        """Test detection of MP3 audio parameters"""
        # Setup mocks
        mock_file = MagicMock()
        mock_file.tell.return_value = 0
        mock_file.read.return_value = b'mock mp3 data'
        
        temp_file_instance = MagicMock()
        temp_file_instance.__enter__.return_value = temp_file_instance
        temp_file_instance.name = '/tmp/test.audio'
        mock_temp_file.return_value = temp_file_instance
        
        # Mock mediainfo to return MP3 info
        mock_mediainfo.return_value = {
            'codec_name': 'mp3', 
            'sample_rate': '44100', 
            'channels': '2'
        }
        
        # Call the method
        encoding, sample_rate, channels = AudioValidator._detect_params(mock_file)
        
        # Assertions
        self.assertEqual(encoding, 'MP3')
        self.assertEqual(sample_rate, 44100)
        self.assertEqual(channels, 2)
        mock_file.seek.assert_called_with(0)
        temp_file_instance.write.assert_called_with(b'mock mp3 data')
        
    @patch('salute_speech.utils.audio.mediainfo')
    @patch('tempfile.NamedTemporaryFile')
    def test_detect_params_wav(self, mock_temp_file, mock_mediainfo):
        """Test detection of WAV audio parameters"""
        # Setup mocks
        mock_file = MagicMock()
        mock_file.tell.return_value = 0
        mock_file.read.return_value = b'mock wav data'
        
        temp_file_instance = MagicMock()
        temp_file_instance.__enter__.return_value = temp_file_instance
        temp_file_instance.name = '/tmp/test.audio'
        mock_temp_file.return_value = temp_file_instance
        
        # Mock mediainfo to return WAV info
        mock_mediainfo.return_value = {
            'codec_name': 'WAV', 
            'sample_rate': '16000', 
            'channels': '1'
        }
        
        # Call the method
        encoding, sample_rate, channels = AudioValidator._detect_params(mock_file)
        
        # Assertions
        self.assertEqual(encoding, 'PCM_S16LE')  # WAV maps to PCM_S16LE
        self.assertEqual(sample_rate, 16000)
        self.assertEqual(channels, 1)
        
    def test_validate_params_valid_pcm(self):
        """Test validation of valid PCM parameters"""
        # Valid PCM: 8 channels, 16000Hz sample rate
        encoding, sample_rate, channels = AudioValidator._validate_params('PCM_S16LE', 16000, 8)
        self.assertEqual(encoding, 'PCM_S16LE')
        self.assertEqual(sample_rate, 16000)
        self.assertEqual(channels, 8)
        
        # Valid PCM: 1 channel, 48000Hz sample rate
        encoding, sample_rate, channels = AudioValidator._validate_params('PCM_S16LE', 48000, 1)
        self.assertEqual(encoding, 'PCM_S16LE')
        self.assertEqual(sample_rate, 48000)
        self.assertEqual(channels, 1)
        
    def test_validate_params_invalid_encoding(self):
        """Test validation with invalid encoding"""
        with self.assertRaises(ValidationError) as context:
            AudioValidator._validate_params('UNSUPPORTED_FORMAT', 16000, 1)
        self.assertIn('Invalid audio encoding', str(context.exception))
        
    def test_validate_params_too_many_channels(self):
        """Test validation with too many channels"""
        # PCM_S16LE has max 8 channels
        with self.assertRaises(ValidationError) as context:
            AudioValidator._validate_params('PCM_S16LE', 16000, 9)
        self.assertIn('Too many channels', str(context.exception))
        
        # MP3 has max 2 channels
        with self.assertRaises(ValidationError) as context:
            AudioValidator._validate_params('MP3', 44100, 3)
        self.assertIn('Too many channels', str(context.exception))
        
        # OPUS has max 1 channel
        with self.assertRaises(ValidationError) as context:
            AudioValidator._validate_params('OPUS', 48000, 2)
        self.assertIn('Too many channels', str(context.exception))
        
    def test_validate_params_invalid_sample_rate(self):
        """Test validation with invalid sample rate"""
        # PCM_S16LE sample rate range is 8000-96000
        with self.assertRaises(ValidationError) as context:
            AudioValidator._validate_params('PCM_S16LE', 7999, 1)
        self.assertIn('Sample rate', str(context.exception))
        self.assertIn('out of valid range', str(context.exception))
        
        with self.assertRaises(ValidationError) as context:
            AudioValidator._validate_params('PCM_S16LE', 96001, 1)
        self.assertIn('Sample rate', str(context.exception))
        self.assertIn('out of valid range', str(context.exception))
        
    def test_validate_params_mp3_no_sample_rate_check(self):
        """Test that MP3 doesn't check sample rate range"""
        # MP3 doesn't have sample rate restriction, so any rate should pass
        encoding, sample_rate, channels = AudioValidator._validate_params('MP3', 4000, 2)
        self.assertEqual(encoding, 'MP3')
        self.assertEqual(sample_rate, 4000)
        self.assertEqual(channels, 2)
        
        encoding, sample_rate, channels = AudioValidator._validate_params('MP3', 192000, 1)
        self.assertEqual(encoding, 'MP3')
        self.assertEqual(sample_rate, 192000)
        self.assertEqual(channels, 1)
        
    @patch('salute_speech.utils.audio.AudioValidator._detect_params')
    @patch('salute_speech.utils.audio.AudioValidator._validate_params')
    def test_detect_and_validate(self, mock_validate, mock_detect):
        """Test the detect_and_validate method that combines detection and validation"""
        # Setup mocks
        mock_file = MagicMock()
        mock_detect.return_value = ('PCM_S16LE', 16000, 1)
        mock_validate.return_value = ('PCM_S16LE', 16000, 1)
        
        # Call the method
        encoding, sample_rate, channels = AudioValidator.detect_and_validate(mock_file)
        
        # Assertions
        self.assertEqual(encoding, 'PCM_S16LE')
        self.assertEqual(sample_rate, 16000)
        self.assertEqual(channels, 1)
        mock_detect.assert_called_once_with(mock_file)
        mock_validate.assert_called_once_with('PCM_S16LE', 16000, 1)
        
    @patch('salute_speech.utils.audio.AudioValidator._detect_params')
    def test_detect_and_validate_with_real_validation(self, mock_detect):
        """Test detect_and_validate with the real validation function"""
        # Setup mock for detection
        mock_file = MagicMock()
        mock_detect.return_value = ('PCM_S16LE', 16000, 1)
        
        # Call the method with real validation
        encoding, sample_rate, channels = AudioValidator.detect_and_validate(mock_file)
        
        # Assertions
        self.assertEqual(encoding, 'PCM_S16LE')
        self.assertEqual(sample_rate, 16000)
        self.assertEqual(channels, 1)
        
    @patch('salute_speech.utils.audio.AudioValidator._detect_params')
    def test_detect_and_validate_validation_failure(self, mock_detect):
        """Test detect_and_validate when validation fails"""
        # Setup mock for detection with invalid parameters
        mock_file = MagicMock()
        mock_detect.return_value = ('PCM_S16LE', 7000, 1)  # Invalid sample rate
        
        # Verify validation error is raised
        with self.assertRaises(ValidationError):
            AudioValidator.detect_and_validate(mock_file)
            
    @patch('salute_speech.utils.audio.os.unlink')
    @patch('salute_speech.utils.audio.mediainfo')
    @patch('tempfile.NamedTemporaryFile')
    def test_detect_params_cleanup_error(self, mock_temp_file, mock_mediainfo, mock_unlink):
        """Test cleanup error handling in _detect_params"""
        # Setup mocks
        mock_file = MagicMock()
        mock_file.tell.return_value = 0
        
        temp_file_instance = MagicMock()
        temp_file_instance.__enter__.return_value = temp_file_instance
        temp_file_instance.name = '/tmp/test.audio'
        mock_temp_file.return_value = temp_file_instance
        
        # Mock mediainfo
        mock_mediainfo.return_value = {
            'codec_name': 'WAV', 
            'sample_rate': '16000', 
            'channels': '1'
        }
        
        # Make unlink fail
        mock_unlink.side_effect = OSError("Cleanup failed")
        
        # Call the method - this should not raise an exception, just log a warning
        encoding, sample_rate, channels = AudioValidator._detect_params(mock_file)
        
        # Assertions
        self.assertEqual(encoding, 'PCM_S16LE')
        self.assertEqual(sample_rate, 16000)
        self.assertEqual(channels, 1)
        mock_unlink.assert_called_once_with('/tmp/test.audio')


if __name__ == '__main__':
    unittest.main() 