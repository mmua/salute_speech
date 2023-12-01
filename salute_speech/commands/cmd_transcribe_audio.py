import json
import os
import sys
import time
import click
from dotenv import load_dotenv, find_dotenv
from salute_speech.speech_recognition import SberSpeechRecognition, TaskStatusResponseError
from salute_speech.utils.audio import get_audio_params
from salute_speech.utils.result_writer import get_writer


_ = load_dotenv(find_dotenv())


def polling_get_result_file_id(sr: SberSpeechRecognition, task_id):
    # Polling loop
    while True:
        task_status = sr.get_task_status(task_id)
        if task_status['status'] == 'ERROR':
            # Handle error
            click.echo("An error occurred during transcription.", err=True)
            raise TaskStatusResponseError("Failed to transcribe file: " + task_id + "\nError" + task_status['error'])

        if task_status['status'] == 'DONE':
            return task_status['response_file_id']

        time.sleep(10)


def filename_to_format(output_file: str):
    ext = os.path.splitext(output_file)[1].lower()
    format_from_ext = {
        '.txt': 'txt',
        '.vtt': 'vtt',
        '.srt': 'srt',
        '.tsv': 'tsv',
        '.json': 'json'
    }
    output_format = format_from_ext.get(ext, 'txt')  # Default to 'txt' if extension is not recognized
    return output_format


@click.command()
@click.argument('audio_file_path', nargs=1, type=click.Path(exists=True))
@click.option('--channels', type=int, default=1, help='Number of channels for transcription. Default: 1')
@click.option('--language', type=click.Choice(['ru-RU', 'en-US', 'kk-KZ']), default='ru-RU',
              help='Language for speech recognition. Default: ru-RU')
@click.option('--output_format', '-f', type=click.Choice(['txt', 'vtt', 'srt', 'tsv', 'json', ''], case_sensitive=False),
              default='', help='Output format of the transcription.')
@click.option('--output_file', '-o', type=click.Path(),
              default='', help='Output path of the transcription.')
def transcribe_audio(audio_file_path, channels: int, language: str, output_format: str, output_file: str):
    if (api_key := os.getenv('SBER_SPEECH_API_KEY')) is None:
        click.echo(click.style('Error: env variable SBER_SPEECH_API_KEY is not set', fg='red'))
        raise click.Abort

    audio_encoding, sample_rate, channels_count = get_audio_params(audio_file_path)
    if channels_count != channels:
        click.echo(click.style('Error: unexpected audio channels number - {channels_count}.'
                               '1 channel is recommended since Salute Speech transcribes each channel independently.',
                               fg='red'))
        raise click.Abort

    sr = SberSpeechRecognition(api_key)

    with open(audio_file_path, "rb") as audio_file:
        file_id = sr.upload_file(audio_file)

    transcription_task = sr.async_recognize(file_id, audio_encoding=audio_encoding, sample_rate=sample_rate,
                                            channels_count=channels_count, language=language)

    result_file_id = polling_get_result_file_id(sr, transcription_task.id)

    transcript_data = sr.download_result(result_file_id)
    transcript = json.loads(transcript_data)

    # Infer format from output file if necessary
    if not output_format and output_file:
        output_format = filename_to_format(output_file)

    if not output_format:
        output_format = 'txt'

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            writer = get_writer(output_format, f)
            writer(transcript)
    else:
        writer = get_writer(output_format, sys.stdout)
        writer(transcript)
