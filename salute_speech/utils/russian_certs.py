import requests
from salute_speech.utils.package import get_config_path


def russian_secure_post(url, **kwargs):
    pem_path = get_config_path('russian.pem')
    return requests.post(url, verify=pem_path, **kwargs)

def russian_secure_get(url, **kwargs):
    pem_path = get_config_path('russian.pem')
    return requests.get(url, verify=pem_path, **kwargs)
