import importlib.resources


def get_config_path(config_name):
    path = importlib.resources.files("salute_speech") / "conf" / config_name
    return str(path)
