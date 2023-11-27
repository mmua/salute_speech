from pkg_resources import resource_filename

def get_config_path(config_name):
    return resource_filename('salute_speech', f'../conf/{config_name}')