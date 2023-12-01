import os
import click
from dotenv import load_dotenv, find_dotenv
from salute_speech.speech_recognition import SberSpeechRecognition
from salute_speech.utils.audio import get_audio_params


_ = load_dotenv(find_dotenv())


@click.command()
@click.argument('audio_file_path', nargs=1)
@click.argument('file_id', nargs=1)
def recognize_audio(audio_file_path: click.Path(exists=True), file_id: str):
    if (api_key := os.getenv('SBER_SPEECH_API_KEY')) is None:
        click.echo(click.style('Error: env variable SBER_SPEECH_API_KEY is not set', fg='red'))
        raise click.Abort

    audio_encoding, sample_rate, channels_count = get_audio_params(audio_file_path)
    sr = SberSpeechRecognition(api_key)
    task = sr.async_recognize(file_id, audio_encoding=audio_encoding, sample_rate=sample_rate, channels_count=channels_count)
    print("speech recognition task created with id: ", task.id)
