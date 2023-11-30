import os
import click
from dotenv import load_dotenv, find_dotenv
from salute_speech.speech_recognition import SberSpeechRecognition

_ = load_dotenv(find_dotenv())


@click.command()
@click.argument('task_id', nargs=1)
def get_task_status(task_id: str):
    if (api_key := os.getenv('SBER_SPEECH_API_KEY')) is None:
        click.echo(click.style('Error: env variable SBER_SPEECH_API_KEY is not set', fg='red'))
        raise click.Abort

    sr = SberSpeechRecognition(api_key)
    response = sr.get_task_status(task_id)
    print(response)

