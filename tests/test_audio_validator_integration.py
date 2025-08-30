import unittest
import os
import io
import tempfile
import wave
import numpy as np
from salute_speech.utils.audio import AudioValidator
from salute_speech.exceptions import ValidationError


class TestAudioValidatorIntegration(unittest.TestCase):
    """
    Integration tests for AudioValidator with real audio data.
    """

    def setUp(self):
        """Create test audio files for testing"""
        # Create a temp directory for our test files
        self.temp_dir = tempfile.mkdtemp()

        # Create a simple WAV file (PCM_S16LE) with 1 channel at 16000 Hz
        self.wav_path = os.path.join(self.temp_dir, "test_mono.wav")
        self._create_test_wav(self.wav_path, channels=1, sample_rate=16000)

        # Create a stereo WAV file
        self.stereo_wav_path = os.path.join(self.temp_dir, "test_stereo.wav")
        self._create_test_wav(self.stereo_wav_path, channels=2, sample_rate=44100)

    def tearDown(self):
        """Clean up the test files"""
        for f in [self.wav_path, self.stereo_wav_path]:
            if os.path.exists(f):
                os.unlink(f)
        os.rmdir(self.temp_dir)

    def _create_test_wav(self, filepath, channels=1, sample_rate=16000, duration=1.0):
        """Helper to create a test WAV file with sine wave"""
        # Generate a simple sine wave
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        audio_data = np.sin(2 * np.pi * 440 * t) * 32767  # 440 Hz tone
        audio_data = audio_data.astype(np.int16)

        # For stereo, duplicate the data
        if channels == 2:
            audio_data = np.column_stack((audio_data, audio_data))

        # Write to WAV file
        with wave.open(filepath, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())

    def test_detect_and_validate_wav_mono(self):
        """Test detect_and_validate with real mono WAV file"""
        # Open the file in binary mode
        with open(self.wav_path, "rb") as audio_file:
            # Call the method
            encoding, sample_rate, channels = AudioValidator.detect_and_validate(
                audio_file
            )

            # Check results
            self.assertEqual(encoding, "PCM_S16LE")
            self.assertEqual(sample_rate, 16000)
            self.assertEqual(channels, 1)

    def test_detect_and_validate_wav_stereo(self):
        """Test detect_and_validate with real stereo WAV file"""
        # Open the file in binary mode
        with open(self.stereo_wav_path, "rb") as audio_file:
            # Call the method
            encoding, sample_rate, channels = AudioValidator.detect_and_validate(
                audio_file
            )

            # Check results
            self.assertEqual(encoding, "PCM_S16LE")
            self.assertEqual(sample_rate, 44100)
            self.assertEqual(channels, 2)

    def test_file_position_preserved(self):
        """Test that file position is preserved after detect_and_validate"""
        # Open the file in binary mode
        with open(self.wav_path, "rb") as audio_file:
            # Read first 10 bytes to move the position
            audio_file.read(10)
            current_pos = audio_file.tell()
            self.assertEqual(current_pos, 10)

            # Call the method
            AudioValidator.detect_and_validate(audio_file)

            # Check that position was restored
            self.assertEqual(audio_file.tell(), current_pos)

    def test_empty_file(self):
        """Test with an empty file"""
        # Create an empty file
        empty_file_path = os.path.join(self.temp_dir, "empty.wav")
        with open(empty_file_path, "wb"):
            pass

        try:
            # Try to validate the empty file
            with open(empty_file_path, "rb") as audio_file:
                # This should raise some kind of error
                with self.assertRaises(Exception):
                    AudioValidator.detect_and_validate(audio_file)
        finally:
            if os.path.exists(empty_file_path):
                os.unlink(empty_file_path)

    def test_seekable_io_buffer(self):
        """Test with io.BytesIO buffer"""
        # Read WAV file into memory
        with open(self.wav_path, "rb") as f:
            wav_data = f.read()

        # Create a BytesIO object
        buffer = io.BytesIO(wav_data)

        # Call the method
        encoding, sample_rate, channels = AudioValidator.detect_and_validate(buffer)

        # Check results
        self.assertEqual(encoding, "PCM_S16LE")
        self.assertEqual(sample_rate, 16000)
        self.assertEqual(channels, 1)

        # Check that position was reset to beginning
        self.assertEqual(buffer.tell(), 0)

    def test_validation_sample_rate_too_low(self):
        """Test validation fails with sample rate that's too low"""
        # Create a WAV with sample rate that's too low
        low_rate_path = os.path.join(self.temp_dir, "low_rate.wav")
        self._create_test_wav(low_rate_path, sample_rate=7000)  # Below 8000 Hz minimum

        try:
            with open(low_rate_path, "rb") as audio_file:
                # Should raise ValidationError
                with self.assertRaises(ValidationError) as context:
                    AudioValidator.detect_and_validate(audio_file)
                self.assertIn("Sample rate", str(context.exception))
                self.assertIn("out of valid range", str(context.exception))
        finally:
            if os.path.exists(low_rate_path):
                os.unlink(low_rate_path)


if __name__ == "__main__":
    unittest.main()
