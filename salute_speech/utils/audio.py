from pydub.utils import mediainfo


def get_audio_params(audio_file_path):
    info = mediainfo(audio_file_path)
    audio_encoding = info['codec_name'].upper()  # Default value, adjust as needed
    sample_rate = int(info['sample_rate'])
    channels_count = int(info['channels'])

    return audio_encoding, sample_rate, channels_count
