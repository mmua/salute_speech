import os
import sys
import click
from dotenv import load_dotenv, find_dotenv
from salute_speech.speech_recognition import SberSpeechRecognition

_ = load_dotenv(find_dotenv())


@click.command()
@click.argument('response_file_id', nargs=1)
@click.argument('audio_file_path', nargs=1, default='')
def download_result(response_file_id: str, audio_file_path: click.Path()):
    api_key = os.getenv("SBER_SPEECH_API_KEY")
    if api_key is None:
        click.echo(click.style(f'Error: env variable SBER_SPEECH_API_KEY is not set', fg='red'))
        raise click.Abort

    sr = SberSpeechRecognition(api_key)
    transcript_data = sr.download_result(response_file_id)
    if audio_file_path:
        with open(audio_file_path, "w") as audio_file:
            audio_file.write(transcript_data)
    else:
        click.echo(transcript_data)