# Sber Salute Speech Python API

A Python client for Sber's Salute Speech Recognition service with a simple, async-first API.

## Features

- OpenAI Whisper-like API for ease of use
- Asynchronous API for compatibility and better performance
- Comprehensive error handling
- Support for multiple audio formats
- Command-line interface for quick transcription

> Quick CLI

```bash
export SBER_SPEECH_API_KEY=your_key_here
ffmpeg -i input.mp3 -ac 1 -ar 16000 audio.wav
salute_speech transcribe-audio audio.wav -o transcript.txt
```

## Installation

```bash
pip install salute_speech
```

Prerequisites (recommended):

- ffmpeg (for best results and simple conversion to mono 16 kHz)

macOS (Homebrew): `brew install ffmpeg`
Ubuntu/Debian: `sudo apt-get install ffmpeg`

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
- `language` (str, optional): Language code for transcription. Supported: `ru-RU`, `en-US`, `kk-KZ`. Defaults to "ru-RU"
- `poll_interval` (float, optional): Interval between status checks in seconds. Defaults to 1.0
- `config` (SpeechRecognitionConfig, optional): Advanced recognition tuning passed to the SberSpeech async API
- `prompt` (str, optional): Optional prompt to guide transcription (not yet supported)
- `response_format` (str, optional): Format of the response (not yet supported)

**Returns:**

- `TranscriptionResponse` object

### TranscriptionResponse

Shape of the result object returned by `client.audio.transcriptions.create()` (aligned with OpenAI's TranscriptionVerbose):

- `duration` (float): The duration of the input audio in seconds
- `language` (str): The language of the input audio (e.g., `ru`, `en`)
- `text` (str): The full transcribed text (concatenation of segment texts)
- `segments` (List[TranscriptionSegment] | None): Segments of the transcribed text with timestamps
- `status` (str): Sber-specific job status (e.g., `DONE`)
- `task_id` (str): Sber-specific task identifier

OpenAI alignment: This structure matches OpenAI Whisper's `TranscriptionVerbose` response format, with additional Sber-specific fields for internal tracking.

Programmatic usage (iterate segments):

```python
for seg in result.segments or []:
    print(f"[{seg.start:.2f} - {seg.end:.2f}] {seg.text}")
```

TranscriptionSegment:

- `id` (int): Segment index
- `start` (float): Start time in seconds
- `end` (float): End time in seconds
- `text` (str): Segment text

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
except InvalidResponseError as e:
    print(f"Invalid API response: {e}")
except APIError as e:
    print(f"API error: {e}")
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

Options:

- `--language` (`ru-RU` | `en-US` | `kk-KZ`) Default: `ru-RU`
- `--channels` Number of channels expected in the input (validated)
- `-f, --output_format` One of: `txt`, `vtt`, `srt`, `tsv`, `json` (usually inferred from `-o`)
- `-o, --output_file` Path to write the transcription
- `--debug_dump` Path or directory to dump raw JSON result (for debugging)

Examples:

```bash
# JSON (timed segments)
salute_speech transcribe-audio audio.wav -o transcript.json

# SRT subtitles
salute_speech transcribe-audio audio.wav -o subtitles.srt

# Dump raw Sber result for inspection
salute_speech transcribe-audio audio.wav -o transcript.txt --debug_dump res.json
```

**Supported output formats:**

- `txt` - Plain text
- `vtt` - WebVTT subtitles
- `srt` - SubRip subtitles
- `tsv` - Tab-separated values
- `json` - JSON format with detailed information:
  - `text` (str)
  - `duration` (float)
  - `language` (str)
  - `segments` (array of `{id, start, end, text}`)

**Note:** Each audio channel is transcribed separately, so converting to mono is recommended for most cases.

### About the API flow

This library uses the asynchronous REST API flow (upload → create task → poll status → download result).
See Sber docs for details:

- Async recognition flow: [developers.sber.ru/docs/ru/salutespeech/rest/async-general](https://developers.sber.ru/docs/ru/salutespeech/rest/async-general)

## Advanced Configuration

For advanced use cases, you can customize the speech recognition parameters:

```python
from salute_speech.speech_recognition import SpeechRecognitionConfig

config = SpeechRecognitionConfig(
    hypotheses_count=3,              # Number of transcription variants
    enable_profanity_filter=True,    # Filter out profanity
    max_speech_timeout="30s",        # Maximum timeout for speech segments
    # speaker_separation_options={...} # Optional: see official docs for available options
)

result = await client.audio.transcriptions.create(
    file=audio_file,
    language="ru-RU",
    config=config
)
```

### Tuning parameters

You can fine‑tune recognition behavior through `SpeechRecognitionConfig` passed to the async API. The most relevant fields are:

- `hypotheses_count` (int): Number of transcription variants to generate (1–10)
- `enable_profanity_filter` (bool): Replace offensive words
- `max_speech_timeout` (str): Max duration for a single speech segment, e.g. `"20s"`
- `no_speech_timeout` (str): Timeout for no-speech detection, e.g. `"7s"`
- `hints` (dict): Domain terms/pronunciations to bias decoding
- `insight_models` (list): Enable extra models (if available for your account)
- `speaker_separation_options` (dict): Speaker separation-related options (service-dependent)

See the official SaluteSpeech async recognition documentation for the complete, up-to-date list of supported options and expected formats:

- Async recognition flow: [developers.sber.ru/docs/ru/salutespeech/rest/async-general](https://developers.sber.ru/docs/ru/salutespeech/rest/async-general)

Note: `language`, `audio_encoding`, `sample_rate`, and `channels_count` are set automatically from your input or via CLI and are not part of the `SpeechRecognitionConfig` object.
