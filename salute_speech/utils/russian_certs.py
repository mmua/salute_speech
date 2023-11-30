import requests
from salute_speech.utils.package import get_config_path


def russian_secure_post(url, timeout=(5, 60), **kwargs):
    pem_path = get_config_path('russian.pem')
    return requests.post(url, timeout=timeout, verify=pem_path, **kwargs)

def russian_secure_get(url, timeout=(5, 60), **kwargs):
    pem_path = get_config_path('russian.pem')
    return requests.get(url, timeout=timeout, verify=pem_path, **kwargs)
