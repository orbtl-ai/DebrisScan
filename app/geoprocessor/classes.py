import os

class UserSubmission:
    def __init__(self, project_dir):
        self.project_dir
        self.submission_metadata = os.path.join(self.project_dir, "user_submission.json")

        self._processors = {
            'geoexif': GeoExifProcessor(),
            'georef': GeoRefProcessor(),
            'nongeo': NonGeoProcessor()
        }

    # prepare project folders, label_map, and sensor_parameters
    def prep_project_dir(self):
        """Given the project_dir, create dirs for storing temporary results and outputs"""

    def prep_sensor_params(self):
        ""
    # load parameters
    def extract_metadata(self):
        """Given the submission_metadata, load all relevant parameters"""

    # loop over images
    def process_images(self):
        """Given the project_dir, loop over images, determine image type, and route to the 
        relevant processor"""
    
    def _determine_image_type(self, image):
        """Determine if an image is orthorectified, contains GeoExif metadata, or has neither."""

class BaseProcessor:
    def process(self, image):
        raise NotImplementedError

class NonGeoProcessor(BaseProcessor):
    def __init__(self, image):
        self.image = image

    # Downsample to GSD

    # Chip Image

    # Tensorflow Inference

    # Unchip Image

    # Plot Image Results

    # Save JSON Results

    # Save CSV Results

class GeoExifProcessor(BaseProcessor):
    def __init__(self, image):
        super().__init__(image)

    # Extract EXIF Info

    # Calculate EXIF-specific Results

class GeoRefProcessor(BaseProcessor):
    def __init__(self, image):
        super().__init__(image)

    # Calculate Geo-specific Results

