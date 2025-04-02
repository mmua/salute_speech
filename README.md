# Sber Salute Speech Python API

A Python client for Sber's Salute Speech Recognition service with a simple, async-first API.

## Features

- OpenAI Whisper-like API for ease of use
- Asynchronous API for compatibility and better performance
- Comprehensive error handling
- Support for multiple audio formats
- Command-line interface for quick transcription

## Installation

```bash
pip install salute_speech
```

## Quick Start

```python
from salute_speech.speech_recognition import SaluteSpeechClient
import asyncio
import os

async def main():
    # Initialize the client (from environment variable)
    client = SaluteSpeechClient(client_credentials=os.getenv("SBER_SPEECH_API_KEY"))
    
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

## API Reference

### SaluteSpeechClient

The main client class that provides access to the Sber Speech API.

```python
client = SaluteSpeechClient(client_credentials="your_credentials_here")
```

#### `client.audio.transcriptions.create()`

Creates a transcription for the given audio file.

**Parameters:**
- `file` (BinaryIO): An audio file opened in binary mode
- `language` (str, optional): Language code for transcription. Defaults to "ru-RU"
- `prompt` (str, optional): Optional prompt to guide transcription
- `response_format` (str, optional): Format of the response. Currently only "text" is supported
- `poll_interval` (float, optional): Interval between status checks in seconds. Defaults to 1.0

**Returns:**
- `TranscriptionResponse` object with:
  - `text`: The transcribed text
  - `status`: Status of the transcription job
  - `task_id`: ID of the transcription task

**Example:**
```python
async with open("meeting.mp3", "rb") as audio_file:
    result = await client.audio.transcriptions.create(
        file=audio_file,
        language="ru-RU"
    )
    print(result.text)
```

### Supported Audio Formats

The service supports the following audio formats:

| Format | Max Channels | Sample Rate Range |
|--------|-------------|-------------------|
| PCM_S16LE (WAV) | 8 | 8,000 - 96,000 Hz |
| OPUS | 1 | Any |
| MP3 | 2 | Any |
| FLAC | 8 | Any |
| ALAW | 8 | 8,000 - 96,000 Hz |
| MULAW | 8 | 8,000 - 96,000 Hz |

Audio parameters are automatically detected and validated using the `AudioValidator` class.

### Error Handling

The client provides structured error handling with specific exception classes:

```python
try:
    result = await client.audio.transcriptions.create(file=audio_file)
except TokenRequestError as e:
    print(f"Authentication error: {e}")
except FileUploadError as e:
    print(f"Upload failed: {e}")
except TaskStatusResponseError as e:
    print(f"Transcription task failed: {e}")
except ValidationError as e:
    print(f"Audio validation failed: {e}")
except SberSpeechError as e:
    print(f"General API error: {e}")
```

### Token Management

Authentication tokens are automatically managed by the `TokenManager` class, which:
- Caches tokens to minimize API requests
- Refreshes tokens when they expire
- Validates token format and expiration

## Command Line Interface

The package includes a command-line interface for quick transcription tasks:

```bash
# Set your API key as an environment variable
export SBER_SPEECH_API_KEY=your_key_here
```

**Basic Usage:**
```bash
salute_speech --help
```

**Transcribe to text:**
```bash
# Prepare audio (recommended: convert to mono)
ffmpeg -i video.mp4 -ac 1 -ar 16000 audio.wav

# Transcribe to text
salute_speech transcribe-audio audio.wav -o transcript.txt
```

**Transcribe to WebVTT:**
```bash
salute_speech transcribe-audio audio.wav -o transcript.vtt
```

**Supported output formats:**
- `txt` - Plain text
- `vtt` - WebVTT subtitles
- `srt` - SubRip subtitles
- `tsv` - Tab-separated values
- `json` - JSON format with detailed information

**Note:** Each audio channel is transcribed separately, so converting to mono is recommended for most cases.

## Advanced Configuration

For advanced use cases, you can customize the speech recognition parameters:

```python
from salute_speech.speech_recognition import SpeechRecognitionConfig

config = SpeechRecognitionConfig(
    hypotheses_count=3,              # Number of transcription variants
    enable_profanity_filter=True,    # Filter out profanity
    max_speech_timeout="30s",        # Maximum timeout for speech segments
    speaker_separation=True          # Enable speaker separation
)

result = await client.audio.transcriptions.create(
    file=audio_file,
    language="ru-RU",
    config=config
)
```

