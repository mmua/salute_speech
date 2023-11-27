import os
import click
from dotenv import load_dotenv, find_dotenv
from salute_speech.speech_recognition import SberSpeechRecognition
from pydub.utils import mediainfo

_ = load_dotenv(find_dotenv())


def get_audio_params(audio_file_path):
    info = mediainfo(audio_file_path)
    audio_encoding = info['codec_name'].upper()  # Default value, adjust as needed
    sample_rate = int(info['sample_rate'])
    channels_count = int(info['channels'])

    return audio_encoding, sample_rate, channels_count


@click.command()
@click.argument('audio_file_path', nargs=1)
@click.argument('file_id', nargs=1)
def recognize_audio(audio_file_path: click.Path(exists=True), file_id: str):
    api_key = os.getenv("SBER_SPEECH_API_KEY")
    if api_key is None:
        click.echo(click.style(f'Error: env variable SBER_SPEECH_API_KEY is not set', fg='red'))
        raise click.Abort

    audio_encoding, sample_rate, channels_count = get_audio_params(audio_file_path)
    sr = SberSpeechRecognition(api_key)
    response = sr.async_recognize(file_id, audio_encoding=audio_encoding, sample_rate=sample_rate, channels_count=channels_count)
    print(response)

