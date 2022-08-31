""" This module spins up the main Gradio/FastAPI web app."""

from os import makedirs, listdir
from os.path import join
from shutil import copy
import json
import uuid

from celery import states
from celery.result import AsyncResult

from fastapi.responses import JSONResponse, FileResponse
import gradio as gr

from geoprocessor.tasks import celery_app
from configs.api_config import api_configs

# Load API's configuration settings
sensor_parameters = api_configs.sensor_parameters
app_data = api_configs.app_data


def object_detection(aerial_images, skip_resampling, flight_agl, sensor_platform):
    """
    Takes a user-submission, returns a task-id, and kicks off a Celery worker.
    """
    # Create a unique task id
    task_id = str(uuid.uuid4())

    # Create a directory to store task data
    task_dir = join(app_data, task_id)
    makedirs(task_dir)

    # Save the user image uploads
    for im in aerial_images:
        basename = im.name.split("/")[-1]
        copy(im.name, join(task_dir, basename))

    # Save the user parameters
    user_sub = {
        "number_of_images": str(len(aerial_images)),
        "skip_resampling": str(skip_resampling),
        "flight_agl": str(flight_agl),
        "sensor_platform": str(sensor_platform),
    }

    json_path = join(task_dir, "user_submission.json")
    with open(json_path, "w") as f:
        json.dump(user_sub, f, indent=1)

    # Kick off the Celery worker
    # TODO: clean this up and implement a proper security_checkpoint()
    # that runs async and doesn't clog this funciton.
    folder_path = join(task_dir)

    accepted_uploads = [
        join(folder_path, f)
        for f in listdir(folder_path)
        if f.endswith(".jpg") or f.endswith(".png") or f.endswith(".tif")
    ]

    # TODO: build a function to handle this, probably in Celery
    camera_params = sensor_parameters[sensor_platform]

    celery_app.send_task(
        "object_detection",
        args=[folder_path, accepted_uploads, camera_params],
        task_id=task_id,
    )

    print(f"Task {task_id} created")

    return task_id


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
                choices=list(sensor_parameters.keys()),
            )
            submit_button = gr.Button(value="Submit Object Detection Job")
            out_task_id = gr.Text(label="Task ID")

        submit_button.click(
            object_detection,
            inputs=[
                in_aerial_images,
                in_skip_resampling,
                in_flight_agl,
                in_sensor_platform,
            ],
            outputs=[out_task_id],
        )
    with gr.Tabs():
        with gr.TabItem("Job Status"):
            in_task_id = gr.Text(label="Task ID")
            status_button = gr.Button(value="Get Job Status")
            out_status = gr.JSON(label="Status")
        status_button.click(get_task_status, inputs=[in_task_id], outputs=[out_status])

# gr.close_all()
demo.launch(server_name="0.0.0.0", debug=True)
