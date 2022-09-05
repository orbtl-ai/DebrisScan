""" This module spins up the main Gradio/FastAPI web app."""

from os import getenv, mkdir
from os.path import join
import json
import uuid

from celery import states
from celery.result import AsyncResult

from fastapi.responses import JSONResponse, FileResponse
import gradio as gr

from client.client_utils import (
    security_checkpoint,
    nonasync_file_save,
    #async_file_save,
    dump_user_submission_to_json,
    prep_sensor_params,
)
from geoprocessor.tasks import celery_app
from client.configs.api_config import api_configs

# Load some API configs

# NOTE: for the time being this is falling back on the default set here...
APP_DATA = getenv("DOCKER_APP_DATA", "/app_data")

with open(api_configs.SUPPORTED_SENSORS_JSON, "rb") as f:
    supported_sensors = json.load(f)

label_map_path = api_configs.LABEL_MAP_PBTXT

color_map_path = api_configs.COLOR_MAP_JSON


def async_object_detection(
    aerial_images, skip_resampling, flight_agl, sensor_platform, confidence_threshold
):
    """
    Takes a user-submission, verifies it, returns a task-id,
    and kicks off a Celery worker.
    """
    # Create a unique task id
    task_id = str(uuid.uuid4())

    # Security check
    security_report = security_checkpoint(
        task_id, aerial_images, api_configs.APPROVED_IMAGE_TYPES
    )

    # NOTE: the api is currently strict on security, if a single file upload fails the
    # security_checkpoint() then the entire submission is rejected.
    if int(security_report['NUM_REJECTED_UPLOADS']) > 0:
        print(f"Security report failed! Task {task_id} was rejected.")
        return JSONResponse(
            status_code=400,
            content={
                "status": "ERROR!",
                "task-id": task_id,
                "error": f"The API has rejected your upload for the following \
                    reasons: {security_report['REJECTED_UPLOADS']}. Please check your \
                    upload and try again.",
            },
        )
    else:
        # Set up a task directory and save files
        task_path = join(APP_DATA, str(task_id))
        mkdir(task_path)

        # Save the user-submitted images to the processing directory
        nonasync_file_save(task_id, aerial_images, task_path)
        #async_file_save(task_id, aerial_images, task_path)

        # extract neccecary parameters from the json file
        sensor_params = prep_sensor_params(supported_sensors, sensor_platform)

        # save task metadata (user selections, key API config options, etc.)
        dump_user_submission_to_json(
            aerial_images, skip_resampling, flight_agl, sensor_platform,
            sensor_params, confidence_threshold,
            api_configs.TARGET_GSD_CM, api_configs.CHIP_SIZE,
            task_path
        )

        # kick-off the heavy processing with Celery...
        celery_app.send_task(
            "object_detection",
            args=[
                task_path, security_report['ACCEPTED_IMAGES'], sensor_platform,
                sensor_params, color_map_path, label_map_path
            ],
            task_id=task_id,
        )

        print(f"Task {task_id} has been sent to Celery!")

    return JSONResponse(
            status_code=200,
            content={
                "status": "Upload Successful!",
                "task-id": task_id,
                "error": "NONE. Please check the status of your task at the Task \
                    Status page using your task-id. When your task succeeds retrieve \
                    the results at the Task Results page..",
            },
        )


async def get_task_status(task_id):
    """This function returns the status of a Celery task when provided with a task_id.
    The task_id is provided in the URL as a path parameter.

    Inputs:
    - task_id: A string representation of a unique task_id associated with a
        Celery task.

    Returns:
    - JSONResponse with information about the job's status, errors, and/or results.
    """
    result = AsyncResult(task_id, app=celery_app)

    output = {
        "task_id": result.id,
        "status": result.state,
        "error": str(result.info) if result.failed() else None,
        "results": str(result.get()) if result.state == states.SUCCESS else None,
    }

    return JSONResponse(status_code=200, content=output)


async def get_task_results(task_id: str):
    """This function returns the results of a Celery task when provided with a task_id.
    The task_id is provided in the URL as a path parameter.

    Inputs:
    - task_id: A string representation of a unique task_id associated with a
        Celery task.

    Returns:
    - FileResponse with the a zip file containing the results of the task.
    """
    result = AsyncResult(task_id)

    if result.state != states.SUCCESS:
        return JSONResponse(
            status_code=204, content={"status": result.state, "error": str(result.info)}
        )
    elif result.state == states.SUCCESS:
        return FileResponse(
            result.get(),
            media_type="application/octet-stream",
            filename=f"{result.id}_results.zip",
        )


with gr.Blocks() as demo:
    gr.Markdown("Markdown Placeholder.")
    with gr.Tabs():
        with gr.TabItem("Object Detection"):
            in_aerial_images = gr.File(
                label="Aerial Images",
                file_count="multiple",
            )
            in_skip_resampling = gr.Checkbox(label="Skip Resampling")
            in_flight_agl = gr.Slider(
                label="Flight AGL (meters)",
                minimum=3,
                maximum=122,
                value=76,
                step=1,
            )
            in_sensor_platform = gr.Dropdown(
                label="Sensor Platform",
                choices=list(supported_sensors.keys()),
                value=list(supported_sensors.keys())[0],
            )
            confidence_threshold = gr.Slider(
                label="Confidence Threshold",
                minimum=0.0,
                maximum=1.0,
                value=api_configs.CONFIDENCE_THRESHOLD,
                step=0.1,
            )
            submit_button = gr.Button(value="Submit Object Detection Job")
            #out_task_id = gr.Text(label="Task ID")
            out_json = gr.JSON(label="JSON Results")
        submit_button.click(
            async_object_detection,
            inputs=[
                in_aerial_images,
                in_skip_resampling,
                in_flight_agl,
                in_sensor_platform,
                confidence_threshold,
            ],
            #outputs=[out_task_id],
            outputs=[out_json],
        )
    with gr.Tabs():
        with gr.TabItem("Job Status"):
            in_task_id = gr.Text(label="Task ID")
            status_button = gr.Button(value="Get Job Status")
            out_status = gr.JSON(label="Status")
        status_button.click(get_task_status, inputs=[in_task_id], outputs=[out_status])

# gr.close_all()

# conc_count: "Number of worker threads that will be processing requests concurrently."
#demo.queue(concurrency_count=2)
demo.launch(server_name="0.0.0.0", server_port=8080, debug=True)
