"""This module is where the API's configuration settings are defined."""


class BaseConfig:
    """
    Base API configuration for local development.
    """

    # Specify a list of approved image file types (list of strings).
    APPROVED_IMAGE_TYPES = ['jpg', 'jpeg', 'png', 'tif', 'tiff']

    # Specify the API's object detection model input image's geospatial ground spacing
    # distance (GSD) in centimeters (float).
    TARGET_GSD_CM = 2.0

    # Specify the API's object detection model input image dimensions (kernel) in
    # pixels. Should be formatted as a python tuple such as:
    # (height_px (int), width_px (int)).
    CHIP_SIZE = (512, 512)

    # Specify the API's default confidence threshold (float). This should range from
    # 0.0 to 1.0 (0% to 100% confidence). All predicted objects below this threshold
    # will be dropped from the outputs. Turn this up for a more conservative set of
    # predictions (i.e., lower false positive rate, higher false negative rate).
    CONFIDENCE_THRESHOLD = 0.3

    # Specify the path to a JSON file which contains the API's supported UAV/camera
    # sensor parameters.
    SUPPORTED_SENSORS_JSON = "/app/client/configs/supported_sensors.json"

    # Specify the path to a Tensorflow PBTXT file which contains a mapping of
    # object class ids (ints) to object class names (strings).
    LABEL_MAP_PBTXT = "/app/client/configs/md_labelmap_v6_20210810.pbtxt"

    # Specify the path to a JSON file which contain a mapping of object
    # class ids (ints) to matplotlib named colors. Color choices:
    # (https://matplotlib.org/stable/gallery/color/named_colors.html)
    COLOR_MAP_JSON = "/app/client/configs/color_map.json"

api_configs = BaseConfig()
