import os
import json
import click
from dotenv import load_dotenv, find_dotenv
from salute_speech.speech_recognition import SberSpeechRecognition

_ = load_dotenv(find_dotenv())


@click.command()
@click.argument('audio_file_path', nargs=1)
def upload_audio(audio_file_path: click.Path(exists=True)):
    if (api_key := os.getenv('SBER_SPEECH_API_KEY')) is None:
        click.echo(click.style('Error: env variable SBER_SPEECH_API_KEY is not set', fg='red'))
        raise click.Abort
    sr = SberSpeechRecognition(api_key)
    with open(audio_file_path, "rb") as audio_file:
        file_id = sr.upload_file(audio_file)
        click.echo(json.dumps(file_id))
