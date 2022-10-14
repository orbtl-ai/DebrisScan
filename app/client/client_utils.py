"""This module contains the API client's utility functions."""

from os.path import join, splitext
import json

from PIL import Image

import aiofiles


def security_checkpoint(
    task_id, file_uploads, approved_content_types
):
    """A simple function designed to screen user uploads to check if they meet the API's
    specifications. This function does not act on the files themselves, but rather just
    issues a report on if any files are in violation and returns that information to
    the user (along with info on accepted files). Currently this function checks the
    following:
    1) All files are of an approved image content type.

    There are other file upload checks performed outside of this function. For reference
    here they are:
    1) File # upload limit is handled by Gradio frontend.
    2) Individual file size limit is handled by async_file_save (currently 1.2 GB).

    Inputs:
    - task_id: A string representing the task_id of the current task.
    - file_uploads: A list of UploadFile objects from the FastAPI request.
    - approved_content_types: A list of strings representing the supported image file
        types (e.g. ["image/jpeg", "image/png"]).

    Returns:
    - security_dict: A dictionary with information about the entire group of
        UploadFile objects from the FastAPI request.
    """

    num_rejected_uploads = 0
    rejected_uploads = {}
    accepted_images = []
    for upload in file_uploads:
        target_basename, target_ext = splitext(upload.orig_name)
        print(target_basename, target_ext)
        if target_ext.strip(".").lower() not in approved_content_types:
            num_rejected_uploads += 1
            rejected_uploads[upload.orig_name] = "UNAPPROVED_FILE_TYPE"
            # add detailed output to logfile?
            print(f"File upload {upload.orig_name} will not be processed because \
                content is not an approved file type ({approved_content_types})")
        else:
            accepted_images.append(upload.orig_name)

    security_dict = {
        "task-id": task_id,
        "NUM_REJECTED_UPLOADS": num_rejected_uploads,
        "REJECTED_UPLOADS": rejected_uploads,
        "ACCEPTED_IMAGES": accepted_images,
    }

    return security_dict


async def async_file_save(task_id, file_uploads, dest):
    """A simple function designed to save a list of files to a destination
    asynchronously.
    Inputs:
    - task_id: A string representing the task_id of the current task.
    - file_uploads: A list of UploadFile objects from the FastAPI request.
    - dest: A string representing the destination path to save the files to.
    Returns:
    - None
    TODO: Add error handling for if the destination directory does not exist,
        return result.
    """
    saved_images = 0
    for upload in file_uploads:
        image_path = join(dest, upload.orig_name)
        async with aiofiles.open(image_path, "wb") as to_write:
            await to_write.write(
                await upload.read(1200000000)
            )  # async read, async write, 1.2 GB upload limit per image to start
        saved_images += 1
    print(f"{task_id}: Saved {saved_images} of {len(file_uploads)} images.")
    return None

def nonasync_file_save(task_id, file_uploads, dest):
    """A simple function designed to save a list of files to a destination.

    Inputs:
    - task_id: A string representing the task_id of the current task.
    - file_uploads: A list of UploadFile objects from the FastAPI request.
    - dest: A string representing the destination path to save the files to.

    Returns:
    - None

    TODO: Add error handling for if the destination directory does not exist,
        return result.
    """

    print(type(file_uploads[0].name), file_uploads[0].name)
    saved_images = 0
    for upload in file_uploads:
        image_path = join(dest, upload.orig_name)
        with Image.open(upload.name) as tmp_img:
            tmp_img.save(image_path)

        saved_images += 1

    print(f"{task_id}: Saved {saved_images} of {len(file_uploads)} images.")

    return None


def dump_user_submission_to_json(
    aerial_images, resample, flight_agl, sensor_platform, confidence_threshold,
    output_path
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
        "number_of_images": str(len(aerial_images)),
        "resample_images": str(resample),
        "flight_agl": str(flight_agl),
        "sensor_platform": str(sensor_platform),
        "confidence_threshold": str(confidence_threshold),
    }

    json_path = join(output_path, "user_submission.json")
    with open(json_path, "w") as f:
        json.dump(user_sub, f, indent=1)

    return None
