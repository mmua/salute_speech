import os
import click
from dotenv import load_dotenv, find_dotenv
from salute_speech.speech_recognition import SberSpeechRecognition

_ = load_dotenv(find_dotenv())


@click.command()
@click.argument("response_file_id", nargs=1)
@click.argument("transcript_file_path", nargs=1, default="")
def download_result(response_file_id: str, transcript_file_path: str):
    if (api_key := os.getenv("SBER_SPEECH_API_KEY")) is None:
        click.echo(
            click.style("Error: env variable SBER_SPEECH_API_KEY is not set", fg="red")
        )
        raise click.Abort

    sr = SberSpeechRecognition(api_key)
    transcript_data = sr.download_result(response_file_id)
    if transcript_file_path:
        with open(transcript_file_path, "w", encoding="utf-8") as transcript_file:
            transcript_file.write(transcript_data)
    else:
        click.echo(transcript_data)
