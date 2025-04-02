import os
import sys
import asyncio
import click
from dotenv import load_dotenv, find_dotenv
from salute_speech.speech_recognition import SaluteSpeechClient
from salute_speech.utils.audio import AudioValidator
from salute_speech.utils.result_writer import get_writer, filename_to_format

_ = load_dotenv(find_dotenv())


async def transcribe_audio_async(audio_file_path, channels: int, language: str, output_format: str, output_file: str):
    if (api_key := os.getenv('SBER_SPEECH_API_KEY')) is None:
        click.echo(click.style('Error: env variable SBER_SPEECH_API_KEY is not set', fg='red'))
        raise click.Abort

    client = SaluteSpeechClient(api_key)

    with open(audio_file_path, "rb") as audio_file:
        # Validate audio parameters
        _, _, channels_count = AudioValidator.detect_and_validate(audio_file)
        if channels_count != channels:
            click.echo(click.style(
                f'Error: unexpected audio channels number - {channels_count}. '
                '1 channel is recommended since Salute Speech transcribes each channel independently.',
                fg='red'))
            raise click.Abort

        # Create transcription
        response = await client.audio.transcriptions.create(
            file=audio_file,
            language=language
        )

        # Infer format from output file if necessary
        if not output_format and output_file:
            output_format = filename_to_format(output_file)

        if not output_format:
            output_format = 'txt'

        # Write output
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                writer = get_writer(output_format, f)
                writer(response.text)
        else:
            writer = get_writer(output_format, sys.stdout)
            writer(response.text)


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
    """Transcribe audio file using Sber Speech Recognition."""
    asyncio.run(transcribe_audio_async(
        audio_file_path=audio_file_path,
        channels=channels,
        language=language,
        output_format=output_format,
        output_file=output_file
    ))
