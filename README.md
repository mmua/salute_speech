# Sber Salute Speech Python API

Here's a documentation section describing how to use the simplified Speech Recognition client:

## Speech Recognition API

The `SaluteSpeechClient` provides an easy-to-use interface for transcribing audio files, similar to OpenAI's Whisper API but with async support.

### Installation

```bash
pip install salute_speech
```

### Quick Start

```python
from simple_speech_client import SimpleSpeechClient
import asyncio

async def main():
    # Initialize the client
    client = SimpleSpeechClient(client_credentials="your_credentials_here")
    
    # Open and transcribe an audio file
    with open("audio.mp3", "rb") as audio_file:
        result = await client.audio.transcriptions.create(
            file=audio_file,
            language="ru-RU"
        )
        print(result.text)

# Run the async function
asyncio.run(main())
```

### API Reference

#### SimpleSpeechClient

##### `client.audio.transcriptions.create()`

Creates a transcription for the given audio file.

**Parameters:**
- `file` (BinaryIO): An audio file opened in binary mode
- `language` (str, optional): Language code for transcription. Defaults to "ru-RU"
- `prompt` (str, optional): Optional prompt to guide transcription
- `response_format` (str, optional): Format of the response. Currently only "text" is supported
- `poll_interval` (float, optional): Interval between status checks in seconds. Defaults to 1.0

**Returns:**
- `TranscriptionResponse` object with a `text` field containing the transcribed text

**Example:**
```python
async with open("meeting.mp3", "rb") as audio_file:
    result = await client.audio.transcriptions.create(
        file=audio_file,
        language="ru-RU",
        prompt="Important business meeting"
    )
    print(result.text)
```

### Supported Audio Formats

The service supports the following audio formats:
- PCM_S16LE (WAV)
- OPUS
- MP3
- FLAC
- ALAW
- MULAW

### Error Handling

The client may raise several types of exceptions:
- `TokenRequestError`: Issues with authentication
- `FileUploadError`: Problems during file upload
- `TaskStatusResponseError`: Errors while checking task status

It's recommended to wrap API calls in try-except blocks:

```python
try:
    result = await client.audio.transcriptions.create(file=audio_file)
except Exception as e:
    print(f"Transcription failed: {str(e)}")
```

## Command line interface 
* beware each audio channel is decoded so in many cases downmix to 1 channel is recommended

Usage:
```
salute_speech --help
```

Transcribe video to txt:
```
ffmpeg -i video.mp4 -ac 1 -ar 16000 audio.wav
salute_speech transcribe-audio audio.wav -o transcript.txt
```

Transcribe video to vtt:
```
ffmpeg -i video.mp4 -ac 1 -ar 16000 audio.wav
salute_speech transcribe-audio audio.wav -o transcript.vtt
```

Supported formats:
 * txt
 * vtt
 * srt
 * tsv

