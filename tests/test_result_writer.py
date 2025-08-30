import io
import json
import pytest
from salute_speech.utils.result_writer import get_writer
from salute_speech.speech_recognition import TranscriptionResponse, TranscriptionSegment


@pytest.fixture()
def sample_response():
    return TranscriptionResponse(
        duration=5.0,
        language="en",
        text="Hello world",
        segments=[
            TranscriptionSegment(id=0, start=0.0, end=1.2, text="Hello"),
            TranscriptionSegment(id=1, start=1.2, end=2.5, text="world"),
        ],
        status="DONE",
        task_id="task123",
    )


@pytest.mark.parametrize(
    "ext,assert_fn",
    [
        (
            "txt",
            lambda data: (
                data.strip() == "Hello world"
            ),
        ),
        (
            "vtt",
            lambda data: (
                data.startswith("WEBVTT") and "00:00.000 --> 00:01.200" in data
            ),
        ),
        (
            "srt",
            lambda data: (
                "1" in data.splitlines()[0] and "00:00:00,000 --> 00:00:01,200" in data
            ),
        ),
        (
            "tsv",
            lambda data: (
                data.splitlines()[1].startswith("0\t1200\tHello")
            ),
        ),
        (
            "json",
            lambda data: (
                (lambda p: p["text"] == "Hello world" and p.get("duration") == 5.0)(json.loads(data))
            ),
        ),
    ],
)
def test_writers(sample_response, ext, assert_fn):
    buffer = io.StringIO()
    writer = get_writer(ext, buffer)
    writer(sample_response)
    buffer.seek(0)
    out = buffer.read()
    assert assert_fn(out)


def test_get_writer_unknown():
    with pytest.raises(ValueError):
        get_writer("unknown", io.StringIO())
