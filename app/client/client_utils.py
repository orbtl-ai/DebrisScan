"""This module contains the API client's utility functions."""

from os.path import join, splitext
from io import BytesIO
import json

from PIL import Image

import aiofiles
from aiofiles import os


async def async_file_save(task_id, dest, file_uploads):
    """A simple function designed to save a list of files to a destination
    using both async read and async write operations, this should be awaited.

    Parameters:
    - task_id: A string representing the task_id of the current task.
    - file_uploads: A list of UploadFile objects from the FastAPI request.
    - dest: A string representing the destination path to save the files to.

    Returns:
    - None

    TODO:
      - Add error handling for if the destination directory does not exist,
        return result.
      - Allow the upload limit to be passed as param, handle if too large (pass?)
    """

    task_path = join(dest, task_id)
    await aiofiles.os.mkdir(task_path)

    for upload in file_uploads:  # TODO: asyncio.gather() this??
        upload.file.seek(0)

        img = Image.open(BytesIO(upload.file.read())).tobytes()
        print(f" img type: {type(img)}")

        file_path = join(task_path, splitext(upload.orig_name)[0] + ".jpg")
        print(file_path)
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(img)

    return task_path


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
