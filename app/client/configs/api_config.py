"""This module is where the DART-API's configuration settings are defined."""


class BaseConfig:
    """
    Base configuration for development.
    """

    # Specify a local directory to store the task data when running locally.
    APP_DATA = "/home/ross/Documents/gradio-app-data"

    # Specify the API's object detection model input image's geospatial ground spacing
    # distance (GSD) in centimeters:
    TARGET_GSD_CM = 2.0

    # Specify the API's object deteciton model input image dimensions (kernel) in
    # pixels(height, width):
    CHIP_SIZE = (512, 512)

    # Specify the supported UAV/camera models (dict key) with their corresponding sensor
    # parameters in a list (dict value). The list should be in the order of:
    # [focal_length(mm), sensor_height(cm), sensor_width(cm)]
    SUPPORTED_SENSORS_JSON = "/app/client/configs/supported_sensors.json"

    # Specify the name of a Tensorflow Label Map (.pbtxt) file that contains a mapping
    # of class integer ID to string name. This should match the target object detection
    # model being served by Tensorflow Serving. The label map should be stored alongside
    # this module in the /client/configs directory.
    LABEL_MAP_PBTXT = "/app/client/configs/md_labelmap_v6_20210810.pbtxt"

    # Specify a color scheme for the API to use when plotting the object detection
    # results. This list needs to be long enough to cover the total number of classes
    # in the API's label_map.pbtxt.
    COLOR_MAP_JSON = "/app/client/configs/color_map.json"


api_configs = BaseConfig()
