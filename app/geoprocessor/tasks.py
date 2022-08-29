import os
import time

from celery import Celery

print('=== TASKS.PY ===')
print(f'CELERY_CONFIG_MODULE: {os.getenv("CELERY_CONFIG_MODULE")}')

celery_app = Celery()
celery_app.config_from_envvar('CELERY_CONFIG_MODULE')
#celery.config_from_object(celery_config)

@celery_app.task(name='object_detection') # Named task
def non_georef_object_detection(
    input_path, 
    images_to_process,
    sensor_parameters):
    '''
    Given a batch of images:
    1. Resample to target GSD
    2. Chip image
    3. Run the object detection
    4. Un-chip the results
    5. Format the results:
        - Image Plots
        - CSV of detections
          - corners, centerpoints, size
        - JSON of detections
        - Per-class debris counts, cumulative sum, average size 
    '''

    for current_image in images_to_process:
        print(f"Processing: {current_image}")

    time.sleep(10)
    return {'status': 'SUCCESS'}
