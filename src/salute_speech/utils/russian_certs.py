import requests
from salute_speech.utils.package import get_config_path
from salute_speech.utils.const import SALUTE_SPEECH_HTTP_TIMEOUT


def russian_secure_post(url, timeout=SALUTE_SPEECH_HTTP_TIMEOUT, **kwargs):
    pem_path = get_config_path("russian.pem")
    return requests.post(url, timeout=timeout, verify=pem_path, **kwargs)


def russian_secure_get(url, timeout=SALUTE_SPEECH_HTTP_TIMEOUT, **kwargs):
    pem_path = get_config_path("russian.pem")
    return requests.get(url, timeout=timeout, verify=pem_path, **kwargs)
