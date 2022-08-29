'''This module is where the DART-API's configuration settings are defined.'''

class BaseConfig:
    """
    Base configuration for development.
    """
    
    # Specify a local directory to store the task data
    app_data = r"/home/ross/Documents/gradio-app-data"

    # Specify the supported UAV/camera models (dict key) with their corresponding sensor
    # parameters in a list (dict value). The list should be in the order of:
    # [focal_length(mm), sensor_height(cm), sensor_width(cm)]
    sensor_parameters = {
    'Skydio 2': [3.7, 0.462, 0.617],
    'Phantom 4 Pro': [8.8, 0.88, 1.32],
    }

api_configs = BaseConfig()
