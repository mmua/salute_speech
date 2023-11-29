# -*- coding: utf-8 -*-

"""Top-level package for Sber Salute Speech App"""

import click
from .commands import upload_audio, recognize_audio, get_task_status, download_result, transcribe_audio

@click.group()
def cli():
    """Sber Salute Speech"""

cli.add_command(upload_audio)
cli.add_command(recognize_audio)
cli.add_command(get_task_status)
cli.add_command(download_result)
cli.add_command(transcribe_audio)

