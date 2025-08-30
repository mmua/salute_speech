import json
import pytest

from salute_speech.speech_recognition import _convert_to_whisper, TranscriptionSegment


@pytest.fixture()
def sample_sber_json():
    """Return a minimal multi-segment Sber JSON array similar to real response."""
    return json.dumps(
        [
            {
                "results": [
                    {
                        "normalized_text": "Hello",
                        "start": "0s",
                        "end": "1.2s",
                    }
                ]
            },
            {
                "results": [
                    {
                        "normalized_text": "world",
                        "start": "1.2s",
                        "end": "2.5s",
                    }
                ]
            },
        ]
    )


def test_convert_to_whisper_basic(sample_sber_json):
    text, segments, language, duration = _convert_to_whisper(sample_sber_json, language="en-US")

    # Full text should be concatenation with space
    assert text == "Hello world"

    # Segments list length and ordering
    assert isinstance(segments, list)
    assert len(segments) == 2
    assert segments[0] == TranscriptionSegment(id=0, start=0.0, end=1.2, text="Hello")
    assert segments[1] == TranscriptionSegment(id=1, start=1.2, end=2.5, text="world")

    # Language code extraction (lowercase lang part)
    assert language == "en"

    # Duration equals max end time
    assert duration == pytest.approx(2.5, rel=1e-3)
