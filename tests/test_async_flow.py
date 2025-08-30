import asyncio
import json
from io import BytesIO
 

from salute_speech.speech_recognition import (
    SaluteSpeechClient,
    SpeechRecognitionTask,
    TranscriptionResponse,
)


def _sample_sber_json():
    return json.dumps(
        [
            {"results": [{"normalized_text": "Hello", "start": "0s", "end": "1.2s"}]},
            {"results": [{"normalized_text": "world", "start": "1.2s", "end": "2.5s"}]},
        ]
    )


def test_transcriptions_create_happy_path(monkeypatch):
    client = SaluteSpeechClient("dummy-key")

    # Bypass audio probing
    monkeypatch.setattr(
        "salute_speech.speech_recognition.AudioValidator.detect_and_validate",
        lambda f: ("PCM_S16LE", 16000, 1),
    )

    # Mock low-level client methods
    monkeypatch.setattr(client.sr, "upload_file", lambda f: "req_123")
    monkeypatch.setattr(
        client.sr,
        "async_recognize",
        lambda **kwargs: SpeechRecognitionTask(
            {"id": "task_123", "status": "RUNNING", "created_at": "t", "updated_at": "t"}
        ),
    )

    # Simulate polling: RUNNING -> DONE
    status_sequence = [
        {"status": "RUNNING"},
        {"status": "DONE", "response_file_id": "res_456"},
    ]

    def _get_task_status(_task_id):
        return status_sequence.pop(0)

    monkeypatch.setattr(client.sr, "get_task_status", _get_task_status)
    monkeypatch.setattr(client.sr, "download_result", lambda _fid: _sample_sber_json())

    # Speed up polling (TaskPoller uses module-level sleep)
    monkeypatch.setattr("salute_speech.speech_recognition.sleep", lambda _s: None)

    async def run():
        return await client.audio.transcriptions.create(
            file=BytesIO(b"\x00\x01"), language="en-US", poll_interval=0.0
        )

    result: TranscriptionResponse = asyncio.run(run())

    assert result.text == "Hello world"
    assert result.language == "en"
    assert result.duration == 2.5
    assert result.status == "DONE"
    assert result.task_id == "task_123"
    assert result.segments is not None and len(result.segments) == 2
