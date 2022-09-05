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
    # async_file_save,
    dump_user_submission_to_json,
)
from geoprocessor.tasks import celery_app
from configs.api_config import api_configs


APP_DATA = getenv("DOCKER_APP_DATA", "/app_data")

supported_sensors = json.load(open(api_configs.SUPPORTED_SENSORS_JSON, "r"))


def async_object_detection(
    aerial_images, resample, flight_agl, sensor_platform, confidence_threshold
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
        return {
            upload_results: gr.update(visible=True),
            out_payload: "UPLOAD FAILED! Please check your submission and try again.",
            out_message: str(security_report['REJECTED_UPLOADS'])
        }
    else:
        # Set up a task directory and save files
        task_path = join(APP_DATA, str(task_id))
        mkdir(task_path)

        # Save the user-submitted images to the processing directory
        nonasync_file_save(task_id, aerial_images, task_path)
        # await async_file_save(task_id, aerial_images, task_path)

        # save task metadata (user selections, key API config options, etc.)
        dump_user_submission_to_json(
            aerial_images, resample, flight_agl, sensor_platform,
            confidence_threshold, task_path
        )

        # kick-off the heavy processing with Celery...
        celery_app.send_task(
            "object_detection",
            args=[task_path, security_report['ACCEPTED_IMAGES']],
            task_id=task_id,
        )

        print(f"Task {task_id} has been sent to Celery!")

    return {
        upload_results: gr.update(visible=True),
        out_payload: str(task_id),
        out_message: "Upload Successful! However it may take awhile to count all that debris. Luckily you don't need to wait around for us! Please save your Task ID and return at any time to check your Task Status at the tab above!"
    }


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


def toggle_resampling(choice):
    if choice == "False":
        return {
            in_flight_agl: gr.update(
                visible=False, value=76
            ),
            in_sensor_platform: gr.update(
                visible=False, value=list(supported_sensors.keys())[0],
            )
        }
    elif choice is True:
        return {
            in_flight_agl: gr.update(
                visible=True, value=76
            ),
            in_sensor_platform: gr.update(
                visible=True, value=list(supported_sensors.keys())[0],
            ),
        }
    else:
        return {
            in_flight_agl: gr.update(visible=False),
            in_sensor_platform: gr.update(visible=False),
        }

with gr.Blocks() as demo:
    gr.Markdown("# Welcome to the DebrisScan Demo!")
    gr.Markdown("This is a **Markdown** description! A really good one!")

    with gr.Tab("Start Object Detection Task"):
        with gr.Row():
            with gr.Column():
                gr.Markdown("## Aerial Image Upload")
                in_aerial_images = gr.File(
                    label="Aerial Image Upload",
                    file_count="multiple",
                )

                gr.Markdown("## Optional Settings")

                with gr.Column():
                    gr.Markdown("### Auto-resample aerial images to 2cm resolution?")
                    gr.Markdown("""
                        *Resampling will take longer, but it should also improve
                        detection results by ensuring your aerial images match our
                        pre-trained models' expected resolution (RECOMMENDED).*
                        """)
                    in_resampling = gr.Checkbox(
                            label=f"Automatically resample aerial images to \
                                {int(api_configs.TARGET_GSD_CM)}cm resolution?",
                    )
                    in_flight_agl = gr.Slider(
                        label="Flight AGL (meters)? \
                            We need to know the height at which the aerial photos \
                            were taken for auto-resampling.",
                        minimum=3,
                        maximum=122,
                        value=76,
                        step=1,
                        visible=False,
                    )
                    in_sensor_platform = gr.Dropdown(
                        label="Sensor Platform? \
                            We need to know the parameters of the camera that took the \
                            aerial photos for auto-resampling.",
                        choices=list(supported_sensors.keys()),
                        value=list(supported_sensors.keys())[0],
                        visible=False,
                    )
                    in_resampling.change(
                        fn=toggle_resampling,
                        inputs=in_resampling,
                        outputs=[in_flight_agl, in_sensor_platform],
                    )
                with gr.Column():
                    gr.Markdown("### Modify Confidence Threshold?")
                    gr.Markdown("""
                        *Our detectors assign each detection a
                        'confidence score'. This setting filters all detections whose
                        confidence score is below the threshold. Lowering the threshold
                        allows in more detections, biasing the results toward a higher
                        rate of false positive detections. Conversely, increasing the
                        threshold filters the most uncertain detections, biasing the
                        results towards a higher rate of false negative detections.
                        (RECOMMENDED VALUE: 30%)*""")
                    confidence_threshold = gr.Slider(
                        label="Confidence Threshold (%)",
                        minimum=0,
                        maximum=100,
                        value=api_configs.CONFIDENCE_THRESHOLD,
                        step=5,
                    )

                submit_button = gr.Button(value="Upload Imagery")

            with gr.Column(visible=False) as upload_results:
                gr.Markdown("## Upload Results")
                out_payload = gr.Text(label="Task ID")
                out_message = gr.Text(label="Message")

            submit_button.click(
                async_object_detection,
                inputs=[
                    in_aerial_images,
                    in_resampling,
                    in_flight_agl,
                    in_sensor_platform,
                    confidence_threshold,
                ],
                # outputs=[out_task_id],
                outputs=[upload_results, out_payload, out_message],
            )

    with gr.Tab("Retrieve Task Status"):
        gr.Markdown("## Enter Task ID")
        with gr.Column():
            in_task_id = gr.Text(label="Task ID")
            status_button = gr.Button(value="Get Job Status")
            out_status = gr.JSON(label="Status")
        status_button.click(
            get_task_status,
            inputs=[in_task_id],
            outputs=[out_status],
        )

# gr.close_all()

# conc_count: "Number of worker threads that will be processing requests concurrently."
# demo.queue(concurrency_count=2)
demo.launch(server_name="0.0.0.0", server_port=8080, debug=True)
