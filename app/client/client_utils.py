"""This module contains the API client's utility functions."""

from os.path import join
import json

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
        print(upload.content_type)
        if upload.content_type not in approved_content_types:
            num_rejected_uploads += 1
            rejected_uploads[upload.filename] = "UNAPPROVED_FILE_TYPE"
            # add detailed output to logfile?
            print(f"File upload {upload.filename} will not be processed because \
                content is not an approved file type ({approved_content_types})")
        else:
            accepted_images.append(upload.filename)

    security_dict = {
        "task-id": task_id,
        "NUM_REJECTED_UPLOADS": num_rejected_uploads,
        "REJECTED_UPLOADS": rejected_uploads,
        "ACCEPTED_IMAGES": accepted_images,
    }

    return security_dict


async def async_file_save(task_id, list_of_files, dest):
    """A simple function designed to save a list of files to a destination
    asynchronously.

    Inputs:
    - task_id: A string representing the task_id of the current task.
    - list_of_files: A list of UploadFile objects from the FastAPI request.
    - dest: A string representing the destination path to save the files to.

    Returns:
    - None

    TODO: Add error handling for if the destination directory does not exist,
        return result.
    """
    saved_images = 0
    for target_file in list_of_files:
        image_path = join(dest, target_file.filename)
        async with aiofiles.open(image_path, "wb") as to_write:
            await to_write.write(
                await target_file.read(1200000000)
            )  # async read, async write, 1.2 GB upload limit per image to start
        saved_images += 1

    print(f"{task_id}: Saved {saved_images} of {len(list_of_files)} images.")

    return None


def dump_user_submission_to_json(
    aerial_images, skip_resampling, flight_agl, sensor_platform, sensor_params,
    confidence_threshold, target_gsd, output_path
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
        "skip_resampling": str(skip_resampling),
        "flight_agl": str(flight_agl),
        "sensor_platform": str(sensor_platform),
        "api_sensor_params": str(sensor_params),
        "api_target_gsd": str(target_gsd),
        "confidence_threshold": str(confidence_threshold),
    }

    json_path = join(output_path, "user_submission.json")
    with open(json_path, "w") as f:
        json.dump(user_sub, f, indent=1)

    return None


def prep_sensor_params(supported_sensors, selected_sensor):
    """A simple function designed to load the selected sensor parameters from a JSON
    file.
    """
    sensor_params = (
            float(supported_sensors[selected_sensor]['focal_length_mm']),
            float(supported_sensors[selected_sensor]['sensor_height_cm']),
            float(supported_sensors[selected_sensor]['sensor_width_cm']),
    )

    return sensor_params
