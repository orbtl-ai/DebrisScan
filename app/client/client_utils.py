"""This module contains the API client's utility functions."""

from os.path import join
import json

from PIL import Image, UnidentifiedImageError

import aiofiles


def save_tmp_with_pil(task_path, file_uploads):
    """
    This function is designed to be encapsulated in some sort of threadpool or
    task queue for async processing.

    Parameters:
    - task_path: The directory on disk to save the file_uploads.
    - file_uploads: a list of NamedTemporaryFile wrappers received by Gradio's input
        "File" component.

    Returns:
    - None

    TODO:
    - Could this be an async def that runs an async for loop? It is intended to run
        in a asyncio threadpool...
    - Error handling for if destination doesn't exist OR if not an image (important!)
    """

    for upload in file_uploads:
        try:
            img = Image.open(upload.name)
        except UnidentifiedImageError:
            print(f"File {upload.name} is not a supported image. Skipping...")
            continue

        file_path = join(task_path, upload.orig_name)
        img.save(file_path, format=img.format)
        print(f"Saved {upload.orig_name}...")

    return None


async def async_dump_user_submission_to_json(
    task_id, output_path, aerial_images, resample, flight_agl, sensor_platform,
    confidence_threshold,
):
    """A simple function designed to a list of user submission parameters, make a pretty
    dictionary, and dump it to a JSON file.

    Inputs:
    - TODO

    Returns:
    - None

    TODO: error handling for if the destination directory does not exist...
    """

    user_sub = {
        "task_id": str(task_id),
        "number_of_images": str(len(aerial_images)),
        "resample_images": str(resample),
        "flight_agl_meters": str(flight_agl),
        "sensor_platform": str(sensor_platform),
        "confidence_threshold": str(confidence_threshold),
    }

    json_path = join(output_path, "user_submission.json")
    async with aiofiles.open(json_path, "w") as f:
        await f.write(json.dumps(user_sub, indent=1))

    return None
