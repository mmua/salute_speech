# Sber Salute Speech Python API

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

